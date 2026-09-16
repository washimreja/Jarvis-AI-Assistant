r"""
core/user_data.py — Persistent User-Data Path Manager for JARVIS.

All runtime user data (credentials, memory, profile, conversations, sessions)
lives under %APPDATA%\JARVIS\ so it survives EXE updates, git pulls, and
PyInstaller rebuilds.

Application code (actions, plugins, ...) should never build these paths by
hand — import the helpers here instead.

Usage:
    from core.user_data import get_appdata_dir, get_settings_dir, ...

No side effects at import time.  Directories are created on first write, not
on import, so importing this module is always fast and safe.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

def get_appdata_dir() -> Path:
    """Return the root user-data directory: %APPDATA%\\JARVIS\\

    Uses APPDATA env var on Windows.  Falls back to the home directory on
    other platforms (Linux / macOS — primarily useful for dev/CI).
    Never hardcodes a username.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "JARVIS"
    # Fallback for non-Windows (dev machines, CI)
    return Path.home() / ".jarvis"


# ---------------------------------------------------------------------------
# Sub-directories
# ---------------------------------------------------------------------------

def get_settings_dir() -> Path:
    """%APPDATA%\\JARVIS\\settings\\ — API keys and all user preferences."""
    return get_appdata_dir() / "settings"


def get_memory_dir() -> Path:
    """%APPDATA%\\JARVIS\\memory\\ — long-term learned memory."""
    return get_appdata_dir() / "memory"


def get_conversations_dir() -> Path:
    """%APPDATA%\\JARVIS\\conversations\\ — conversation turn history."""
    return get_appdata_dir() / "conversations"


def get_profile_dir() -> Path:
    """%APPDATA%\\JARVIS\\profile\\ — persistent user profile."""
    return get_appdata_dir() / "profile"


def get_sessions_dir() -> Path:
    """%APPDATA%\\JARVIS\\sessions\\ — durable session summary archive."""
    return get_appdata_dir() / "sessions"


def get_logs_dir() -> Path:
    """%APPDATA%\\JARVIS\\logs\\ — reserved for future logging."""
    return get_appdata_dir() / "logs"


# ---------------------------------------------------------------------------
# Specific file paths
# ---------------------------------------------------------------------------

def get_settings_path() -> Path:
    """Full path to api_keys.json (config + credentials)."""
    return get_settings_dir() / "api_keys.json"


def get_memory_path() -> Path:
    """Full path to long_term.json (long-term memory)."""
    return get_memory_dir() / "long_term.json"


def get_conversations_path() -> Path:
    """Full path to conversation_history.json."""
    return get_conversations_dir() / "conversation_history.json"


def get_profile_path() -> Path:
    """Full path to user_profile.json."""
    return get_profile_dir() / "user_profile.json"


# ---------------------------------------------------------------------------
# Directory creation helpers (called by writers, not by importers)
# ---------------------------------------------------------------------------

def ensure_settings_dir() -> None:
    get_settings_dir().mkdir(parents=True, exist_ok=True)


def ensure_memory_dir() -> None:
    get_memory_dir().mkdir(parents=True, exist_ok=True)


def ensure_conversations_dir() -> None:
    get_conversations_dir().mkdir(parents=True, exist_ok=True)


def ensure_profile_dir() -> None:
    get_profile_dir().mkdir(parents=True, exist_ok=True)


def ensure_sessions_dir() -> None:
    get_sessions_dir().mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Migration helper — safe, idempotent copy of a single legacy file
# ---------------------------------------------------------------------------

def migrate_file(old_path: Path, new_path: Path, label: str = "") -> bool:
    """Copy `old_path` → `new_path` if the new path does not already exist.

    Rules:
      - If new_path exists          → do nothing (already migrated or fresh install).
      - If old_path does not exist  → do nothing (nothing to migrate).
      - Original file is NEVER deleted.
      - Returns True if a copy was made, False otherwise.
    """
    if new_path.exists():
        return False          # already in place — nothing to do
    if not old_path.exists():
        return False          # no legacy data — nothing to migrate

    try:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(str(old_path), str(new_path))
        tag = f"[{label}] " if label else ""
        print(f"{tag}[MIGRATION] Migrated {old_path.name} -> {new_path}")
        return True
    except Exception as exc:
        tag = f"[{label}] " if label else ""
        print(f"{tag}[MIGRATION WARN] Migration failed ({old_path.name}): {exc}")
        return False
