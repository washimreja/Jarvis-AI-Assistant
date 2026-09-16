"""
core/user_profile.py — Persistent User Profile for JARVIS.

Stores durable identity information about the user in:
    %APPDATA%\\JARVIS\\profile\\user_profile.json

This is the CANONICAL source for:
  - name / preferred name
  - education & university
  - technical interests, technology stack
  - creative preferences, favourite colours
  - content creation interests
  - important project context

It is SEPARATE from long-term memory (memory/long_term.json).

  PROFILE  = "Who Washim is"        (stable identity, edited explicitly)
  MEMORY   = "What JARVIS learned"  (grows during conversation)

No side effects at import time.  Call load_profile() or
format_profile_for_prompt() explicitly — never from module-level code.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock

from core.user_data import get_profile_path, ensure_profile_dir

_lock = Lock()

# ---------------------------------------------------------------------------
# Initial profile seed — used ONLY when user_profile.json does not exist yet.
# Never overwrite an existing profile automatically.
# ---------------------------------------------------------------------------

_INITIAL_PROFILE: dict = {
    "_meta": {
        "created": "",          # filled in at first-run creation
        "schema_version": 1,
    },
    "name": "Washim Reja",
    "preferred_name": "Washim",
    "education": {
        "program": "B.Tech",
        "field": "Computer Science & Engineering",
        "university": "Sister Nivedita University (SNU), Kolkata",
        "current_semester": 5,
        "status": "Active student",
    },
    "technical_interests": [
        "Artificial Intelligence",
        "AI engineering",
        "AI assistants",
        "AI agents",
        "Generative AI",
        "LLMs",
        "Computer Vision",
        "Machine Learning",
        "Web development",
        "Software engineering",
        "SaaS",
        "Automation",
        "Desktop applications",
    ],
    "technology_stack": [
        "Python", "Java", "C", "C++", "JavaScript", "TypeScript",
        "HTML", "CSS", "SQL", "Kotlin",
        "Next.js", "React", "PostgreSQL", "Prisma", "Supabase",
        "Vercel", "GitHub",
    ],
    "creative_preferences": [
        "cinematic", "futuristic", "clean", "premium", "modern",
        "minimal", "professional", "polished UI/UX",
        "cinematic video editing", "velocity edits", "slow-motion edits",
        "evening/night grading", "premium typography",
    ],
    "favorite_colors": ["White", "Blue", "Black"],
    "music_preference": ["Arijit Singh"],
    "content_creation_interests": [
        "YouTube", "Instagram", "short-form video",
        "cinematic content", "motivational content",
        "video editing", "graphic design", "thumbnails", "social media branding",
    ],
    "projects": [
        "JARVIS — AI Assistant",
        "Washim Labs",
        "PromptVerse / PromptVision",
        "Nexon Flow / Nexon Lab",
        "Quantum Creator Washim portfolio",
    ],
    "social": {
        "github":    "https://github.com/washimreja",
        "youtube":   "https://www.youtube.com/@washimrejaa9",
        "instagram": "https://www.instagram.com/cinematic_vibes_by_washim",
        "linkedin":  "https://www.linkedin.com/in/washim-reja-376832339",
        "x":         "https://x.com/Washim_9",
        "tiktok":    "https://www.tiktok.com/@washim_9",
        "pinterest": "https://www.pinterest.com/cinematic_vibes_by_washim",
    },
}


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def load_profile() -> dict:
    """Load user profile from disk.

    First run: if the file does not exist, creates it with the initial seed.
    Subsequent runs: loads and returns the existing profile unchanged.
    Thread-safe.
    """
    path = get_profile_path()
    with _lock:
        if not path.exists():
            return _create_initial_profile()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            # Corrupted file — recreate
            print("[Profile] [WARN] Corrupted profile file -- recreating.")
            return _create_initial_profile()
        except Exception as exc:
            print(f"[Profile] [WARN] Load error: {exc}")
            return {}


def save_profile(profile: dict) -> None:
    """Persist profile to disk.  Thread-safe.

    Merges the provided dict into the existing profile (read-modify-write).
    Existing keys that are not in `profile` are preserved.
    Call with the full updated profile to perform a complete replace.
    """
    if not isinstance(profile, dict):
        return
    path = get_profile_path()
    with _lock:
        existing: dict = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        _deep_merge(existing, profile)
        ensure_profile_dir()
        path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def update_profile_field(keys: list[str], value) -> None:
    """Update a single nested field in the profile.

    Example:
        update_profile_field(["education", "current_semester"], 6)
    """
    profile = load_profile()
    node = profile
    for key in keys[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    node[keys[-1]] = value
    save_profile(profile)


def format_profile_for_prompt(profile: dict | None) -> str:
    """Format the user profile as a concise system-prompt block.

    Returns an empty string if the profile is empty or None.
    Designed to be injected into the Gemini system instruction alongside
    the long-term memory block — they remain separate data sources.
    """
    if not profile:
        return ""

    lines: list[str] = [
        "[USER PROFILE — stable identity, always use naturally]",
    ]

    name = profile.get("preferred_name") or profile.get("name", "")
    if name:
        lines.append(f"Name: {name}")

    edu = profile.get("education")
    if isinstance(edu, dict):
        prog  = edu.get("program", "")
        field = edu.get("field", "")
        uni   = edu.get("university", "")
        sem   = edu.get("current_semester", "")
        parts = []
        if prog and field:
            parts.append(f"{prog} — {field}")
        if uni:
            parts.append(uni)
        if sem:
            parts.append(f"Semester {sem}")
        if parts:
            lines.append("Education: " + ", ".join(parts))

    tech = profile.get("technical_interests", [])
    if isinstance(tech, list) and tech:
        lines.append("Technical interests: " + ", ".join(tech[:8]))

    stack = profile.get("technology_stack", [])
    if isinstance(stack, list) and stack:
        lines.append("Technology: " + ", ".join(stack[:10]))

    creative = profile.get("creative_preferences", [])
    if isinstance(creative, list) and creative:
        lines.append("Creative style: " + ", ".join(creative[:6]))

    projects = profile.get("projects", [])
    if isinstance(projects, list) and projects:
        lines.append("Key projects: " + "; ".join(projects[:5]))

    if len(lines) <= 1:
        return ""

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_initial_profile() -> dict:
    """Write the initial seed file and return it.  Caller holds _lock."""
    profile = dict(_INITIAL_PROFILE)
    profile["_meta"] = {
        "created": datetime.now().strftime("%Y-%m-%d"),
        "schema_version": 1,
    }
    ensure_profile_dir()
    path = get_profile_path()
    path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[Profile] [+] Created initial profile -> {path}")
    return profile


def _deep_merge(target: dict, source: dict) -> None:
    """Recursively merge `source` into `target` in-place."""
    for key, value in source.items():
        if (
            key in target
            and isinstance(target[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(target[key], value)
        else:
            target[key] = value
