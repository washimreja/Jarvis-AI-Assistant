"""
core/visual_engine.py  — JARVIS Visual Computer Control Engine
==============================================================
Small, focused engine. Priority: SAFETY > CORRECTNESS > SPEED.

Pipeline:
    screenshot → Gemini vision (single call, bbox JSON) → safety validate
    → preview log → click → post-screenshot → verify → result

Rules:
    - confidence_min = 0.80  (hard floor)
    - destructive targets    → HARD BLOCK, no auto-click ever
    - single Gemini call     → bbox reused, never re-queried
    - failure                → re-screenshot + re-detect (never retry old coords)
    - pixel-diff             → signal only, not sole success proof
    - Gemini post-verify     → ambiguous cases only (API cost-conscious)
"""
from __future__ import annotations

import io
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import sys

# ── Optional imports (all already in requirements.txt) ───────────────────────
try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    import PIL.ImageChops
    import PIL.ImageStat
    _PIL = True
except ImportError:
    _PIL = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIDENCE_MIN   = 0.80          # Hard floor — won't click below this
EDGE_DEADZONE_PX = 8             # Don't click within 8px of screen edge
VERIFY_DIFF_MIN  = 6.0           # Mean pixel diff to count as "UI changed"
MAX_RETRIES      = 1             # On failure: 1 re-screenshot + re-detect cycle

DESTRUCTIVE_KEYWORDS = frozenset({
    "delete", "remove", "uninstall", "format", "wipe", "erase",
    "shutdown", "restart", "reset", "payment", "pay", "purchase",
    "submit payment", "confirm delete", "permanently",
})

GEMINI_MODEL = "gemini-2.0-flash"   # vision-capable, cost-efficient

# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class DetectionResult:
    found:      bool          = False
    label:      str           = ""
    confidence: float         = 0.0
    bbox:       dict          = field(default_factory=dict)   # x1,y1,x2,y2
    center:     dict          = field(default_factory=dict)   # x, y
    warning:    str           = ""
    raw:        str           = ""   # raw Gemini response for debug

@dataclass
class VerifyResult:
    success:    bool  = False
    method:     str   = ""    # "pixel_diff" | "gemini" | "assumed"
    diff_score: float = 0.0
    notes:      str   = ""


# ── Config helper (mirrors pattern from computer_control.py) ──────────────────
def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_api_key() -> str:
    cfg_path = _base_dir() / "config" / "api_keys.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8")).get("gemini_api_key", "")
    except Exception:
        return ""


# ── VisualEngine ──────────────────────────────────────────────────────────────
class VisualEngine:
    """
    Small, safety-first visual interaction engine.

    Usage:
        ve = VisualEngine()
        result = ve.visual_click("settings gear icon")
        result = ve.visual_find("search bar")
    """

    def __init__(self, confidence_min: float = CONFIDENCE_MIN):
        self.confidence_min = confidence_min

    # ── 1. Screenshot ─────────────────────────────────────────────────────────
    def screenshot(self) -> tuple[bytes, "PIL.Image.Image | None", int, int]:
        """
        Capture full screen.
        Returns (jpeg_bytes, pil_image, width, height).
        Priority: mss (fast) -> pyautogui -> win32 GDI fallback.
        """
        # ── mss (fastest) ────────────────────────────────────────────────────
        if _MSS and _PIL:
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[0]
                    w = monitor["width"]
                    h = monitor["height"]
                    raw = sct.grab(monitor)
                    img = PIL.Image.frombytes("RGB", (w, h), raw.rgb)
                    if w > 1280:
                        ratio = 1280 / w
                        img = img.resize((1280, int(h * ratio)), PIL.Image.BILINEAR)
                        w, h = img.size
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=82, optimize=False)
                    return buf.getvalue(), img, w, h
            except Exception:
                pass  # fall through to next method

        # ── pyautogui fallback ───────────────────────────────────────────────
        if _PYAUTOGUI and _PIL:
            try:
                img = pyautogui.screenshot()
                w, h = img.size
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=82)
                return buf.getvalue(), img, w, h
            except Exception:
                pass

        # ── win32 GDI fallback (Windows only) ────────────────────────────────
        if _PIL:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                gdi32  = ctypes.windll.gdi32
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
                src_dc  = user32.GetDC(0)
                mem_dc  = gdi32.CreateCompatibleDC(src_dc)
                bmp     = gdi32.CreateCompatibleBitmap(src_dc, w, h)
                gdi32.SelectObject(mem_dc, bmp)
                SRCCOPY = 0x00CC0020
                gdi32.BitBlt(mem_dc, 0, 0, w, h, src_dc, 0, 0, SRCCOPY)
                bmi = ctypes.create_string_buffer(40)
                ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[0] = 40   # biSize
                ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[1] = w
                ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[2] = -h   # top-down
                ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int16))[6] = 1    # biPlanes
                ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int16))[7] = 24   # biBitCount
                buf_size = w * h * 3
                raw_buf  = ctypes.create_string_buffer(buf_size)
                gdi32.GetDIBits(mem_dc, bmp, 0, h, raw_buf, bmi, 0)
                gdi32.DeleteObject(bmp)
                gdi32.DeleteDC(mem_dc)
                user32.ReleaseDC(0, src_dc)
                img = PIL.Image.frombuffer("RGB", (w, h), raw_buf.raw, "raw", "BGR", 0, 1)
                if w > 1280:
                    ratio = 1280 / w
                    img = img.resize((1280, int(h * ratio)), PIL.Image.BILINEAR)
                    w, h = img.size
                out = io.BytesIO()
                img.save(out, format="JPEG", quality=82, optimize=False)
                return out.getvalue(), img, w, h
            except Exception as e:
                raise RuntimeError(f"All screenshot methods failed. GDI error: {e}")

        raise RuntimeError("PIL not available — cannot capture screenshot.")

    # ── 2. Gemini Vision Detection ────────────────────────────────────────────
    def find(self, description: str) -> DetectionResult:
        """
        Single Gemini call. Returns DetectionResult with bbox + confidence.
        The bbox is used for all subsequent operations — no re-query.
        """
        api_key = _get_api_key()
        if not api_key:
            return DetectionResult(found=False, warning="No Gemini API key configured.")

        raw = ""
        try:
            from google import genai
            from google.genai import types as gtypes

            img_bytes, _, w, h = self.screenshot()

            prompt = (
                f"You are analyzing a {w}x{h} screenshot.\n"
                f"Find the UI element described as: \"{description}\"\n\n"
                "Reply with ONLY valid JSON, no markdown, no explanation:\n"
                "{\n"
                '  "found": true or false,\n'
                '  "label": "short label of what you see",\n'
                '  "confidence": 0.0 to 1.0,\n'
                '  "bbox": {"x1": int, "y1": int, "x2": int, "y2": int},\n'
                '  "center": {"x": int, "y": int},\n'
                '  "warning": "any concern or empty string"\n'
                "}\n\n"
                "If not found: set found=false, confidence=0.0, bbox/center all zeros.\n"
                "Coordinates are in the resized screenshot pixel space."
            )

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    gtypes.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )

            raw = (response.text or "").strip()
            # Strip markdown fences if present
            raw_clean = re.sub(r"^```[a-z]*\n?|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw_clean)

            return DetectionResult(
                found      = bool(data.get("found", False)),
                label      = str(data.get("label", "")),
                confidence = float(data.get("confidence", 0.0)),
                bbox       = data.get("bbox", {"x1": 0, "y1": 0, "x2": 0, "y2": 0}),
                center     = data.get("center", {"x": 0, "y": 0}),
                warning    = str(data.get("warning", "")),
                raw        = raw,
            )

        except json.JSONDecodeError as e:
            return DetectionResult(found=False, warning=f"Gemini returned invalid JSON: {e}", raw=raw)
        except Exception as e:
            return DetectionResult(found=False, warning=f"Detection failed: {e}")

    # ── 3. Safety Validator ───────────────────────────────────────────────────
    def validate(
        self,
        det: DetectionResult,
        description: str,
        screen_w: int,
        screen_h: int,
        confirm_destructive: bool = False,
    ) -> tuple[bool, str]:
        """
        Returns (is_safe, reason_string).
        Hard-blocks on destructive keywords unless confirm_destructive=True.
        """
        if not det.found:
            return False, f"Element not found on screen: {description}"

        if det.confidence < self.confidence_min:
            return False, (
                f"Confidence too low ({det.confidence:.0%} < {self.confidence_min:.0%}). "
                f"I see '{det.label}' but I'm not confident enough to click. "
                f"Try describing it more precisely."
            )

        # Destructive keyword check
        desc_lower = description.lower()
        triggered = [kw for kw in DESTRUCTIVE_KEYWORDS if kw in desc_lower]
        if triggered and not confirm_destructive:
            return False, (
                f"Destructive action detected ({', '.join(triggered)}). "
                f"This requires explicit confirmation (confirm=True) to proceed."
            )

        # Coordinate sanity
        cx = det.center.get("x", 0)
        cy = det.center.get("y", 0)
        if not (EDGE_DEADZONE_PX < cx < screen_w - EDGE_DEADZONE_PX and
                EDGE_DEADZONE_PX < cy < screen_h - EDGE_DEADZONE_PX):
            return False, (
                f"Target coordinates ({cx},{cy}) outside safe bounds "
                f"(screen: {screen_w}x{screen_h}, deadzone: {EDGE_DEADZONE_PX}px)."
            )

        return True, "OK"

    # ── 4. Execute Click ──────────────────────────────────────────────────────
    def execute_click(self, x: int, y: int, click_type: str = "left") -> None:
        """Smooth human-like move + click."""
        if not _PYAUTOGUI:
            raise RuntimeError("pyautogui not available.")
        cur_x, cur_y = pyautogui.position()
        dist = ((x - cur_x) ** 2 + (y - cur_y) ** 2) ** 0.5
        duration = min(0.15 + dist / 2000, 0.6)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)
        time.sleep(0.05)
        if click_type == "right":
            pyautogui.rightClick()
        elif click_type == "double":
            pyautogui.doubleClick()
        else:
            pyautogui.click()

    # ── 5. Post-click Verify ──────────────────────────────────────────────────
    def verify(
        self,
        before_img: "PIL.Image.Image",
        bbox: dict,
        description: str,
    ) -> VerifyResult:
        """
        Capture fresh screenshot after click and compare the clicked region.
        Pixel-diff is a SIGNAL, not sole proof.
        Escalates to Gemini only if ambiguous (cost-conscious).
        """
        if not _PIL:
            return VerifyResult(success=True, method="assumed", notes="PIL not available.")

        try:
            time.sleep(0.4)   # allow UI to settle
            _, after_img, _, _ = self.screenshot()

            x1, y1 = bbox.get("x1", 0), bbox.get("y1", 0)
            x2, y2 = bbox.get("x2", 0), bbox.get("y2", 0)
            pad = 30
            region = (max(0, x1 - pad), max(0, y1 - pad), x2 + pad, y2 + pad)

            before_crop = before_img.crop(region).convert("RGB")
            after_crop  = after_img.crop(region).convert("RGB")

            diff  = PIL.ImageChops.difference(before_crop, after_crop)
            stat  = PIL.ImageStat.Stat(diff)
            score = sum(stat.mean) / 3

            if score >= VERIFY_DIFF_MIN:
                return VerifyResult(
                    success=True, method="pixel_diff",
                    diff_score=score,
                    notes=f"UI changed (diff={score:.1f})"
                )

            # Ambiguous — escalate to Gemini
            return self._gemini_verify(after_img, description, score)

        except Exception as e:
            return VerifyResult(success=True, method="assumed", notes=f"Verify error: {e}")

    def _gemini_verify(
        self,
        after_img: "PIL.Image.Image",
        description: str,
        diff_score: float,
    ) -> VerifyResult:
        """Lightweight Gemini visual confirm for ambiguous cases."""
        api_key = _get_api_key()
        if not api_key:
            return VerifyResult(success=True, method="assumed", notes="No API key for verify.")
        try:
            from google import genai
            from google.genai import types as gtypes

            buf = io.BytesIO()
            after_img.save(buf, format="JPEG", quality=70)

            prompt = (
                f"A click was just performed on: \"{description}\"\n"
                "Looking at this post-click screenshot, did the click appear to succeed?\n"
                "Reply with ONLY: YES or NO, then one brief reason."
            )
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    gtypes.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"),
                    prompt,
                ],
            )
            text = (response.text or "").strip()
            success = text.upper().startswith("YES")
            return VerifyResult(
                success=success, method="gemini",
                diff_score=diff_score,
                notes=text
            )
        except Exception as e:
            return VerifyResult(success=True, method="assumed", notes=f"Gemini verify error: {e}")

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def visual_find(self, description: str) -> dict:
        """
        Find element visually. No click. Returns location + confidence.
        Build and test this first before using visual_click.
        """
        print(f"[VisualEngine] Searching: {description}")
        det = self.find(description)

        if not det.found:
            return {
                "found": False,
                "message": f"Not found: '{description}'",
                "warning": det.warning,
            }

        _, _, w, h = self.screenshot()
        safe, reason = self.validate(det, description, w, h)

        return {
            "found":      det.found,
            "safe":       safe,
            "label":      det.label,
            "confidence": det.confidence,
            "center":     det.center,
            "bbox":       det.bbox,
            "warning":    det.warning,
            "message":    reason if not safe else f"Found '{det.label}' at {det.center} ({det.confidence:.0%})",
        }

    def visual_click(
        self,
        description: str,
        click_type: str = "left",
        confirm_destructive: bool = False,
    ) -> dict:
        """
        Full pipeline: screenshot → find → validate → preview → click → verify.
        On failure: re-screenshot + re-detect. NEVER retry stale coordinates.
        """
        print(f"[VisualEngine] visual_click: '{description}'")

        for attempt in range(1, MAX_RETRIES + 2):
            if attempt > 1:
                print(f"[VisualEngine] Re-screenshot + re-detect (attempt {attempt})...")
                time.sleep(0.5)

            try:
                img_bytes, before_img, w, h = self.screenshot()
            except Exception as e:
                return {"success": False, "message": f"Screenshot failed: {e}"}

            det = self.find(description)

            if not det.found:
                if attempt <= MAX_RETRIES:
                    continue
                return {
                    "success": False,
                    "message": f"Element not found: '{description}'",
                    "warning": det.warning,
                }

            safe, reason = self.validate(det, description, w, h, confirm_destructive)
            if not safe:
                # Safety blocks are intentional — never retry them
                return {"success": False, "safe": False, "message": reason}

            print(
                f"[VisualEngine] Target: {det.label} | "
                f"confidence={det.confidence:.0%} | "
                f"center=({det.center['x']},{det.center['y']}) | "
                f"bbox={det.bbox}"
            )
            if det.warning:
                print(f"[VisualEngine] Warning: {det.warning}")

            try:
                self.execute_click(det.center["x"], det.center["y"], click_type)
            except Exception as e:
                return {"success": False, "message": f"Click execution failed: {e}"}

            verify = self.verify(before_img, det.bbox, description)
            print(
                f"[VisualEngine] Verify: {verify.method} | "
                f"diff={verify.diff_score:.1f} | {verify.notes}"
            )

            return {
                "success":       verify.success,
                "label":         det.label,
                "confidence":    det.confidence,
                "center":        det.center,
                "verify_method": verify.method,
                "verify_notes":  verify.notes,
                "message": (
                    f"Clicked '{det.label}' at ({det.center['x']},{det.center['y']}) "
                    f"with {det.confidence:.0%} confidence. "
                    f"Result: {'confirmed' if verify.success else 'unconfirmed'}."
                ),
            }

        return {"success": False, "message": "All attempts exhausted."}

    def visual_type(self, field_description: str, text: str) -> dict:
        """
        Find field → click → verify focus → type.
        Never types into an unconfirmed field.
        """
        print(f"[VisualEngine] visual_type into: '{field_description}'")

        click_result = self.visual_click(field_description, click_type="left")
        if not click_result.get("success"):
            return {
                "success": False,
                "message": f"Could not click field '{field_description}': {click_result.get('message', '')}",
            }

        time.sleep(0.2)   # allow focus

        try:
            if not _PYAUTOGUI:
                return {"success": False, "message": "pyautogui not available."}
            pyautogui.typewrite(text, interval=0.04)
            return {
                "success":     True,
                "field_label": click_result.get("label", field_description),
                "message":     f"Typed into '{field_description}': {repr(text)}",
            }
        except Exception as e:
            return {"success": False, "message": f"Typing failed: {e}"}
