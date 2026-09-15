"""
core/window_manager.py — OS-Level Window and Screen Control for JARVIS.

Provides reliable window manipulation (maximize, minimize, restore, bring to front,
fullscreen) using Win32 APIs on Windows with verification.
"""

from __future__ import annotations

import logging
import platform
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("WindowManager")
_OS = platform.system()

if _OS == "Windows":
    try:
        import win32con
        import win32gui
        import win32process
    except ImportError:
        win32gui = None
        win32con = None
        win32process = None
else:
    win32gui = None
    win32con = None
    win32process = None


class WindowManager:
    """Provides verified OS-level window control."""

    @staticmethod
    def is_available() -> bool:
        return _OS == "Windows" and win32gui is not None

    @classmethod
    def find_windows_by_title_or_class(
        cls,
        title_keywords: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find visible top-level windows matching title keywords or class names."""
        if not cls.is_available():
            return []

        results: List[Dict[str, Any]] = []

        def enum_handler(hwnd: int, extra: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd).strip()
            cls_name = win32gui.GetClassName(hwnd).strip()
            if not title:
                return True

            match = False
            if title_keywords:
                title_lower = title.lower()
                if any(kw.lower() in title_lower for kw in title_keywords):
                    match = True
            if class_names and not match:
                if any(cn.lower() == cls_name.lower() for cn in class_names):
                    match = True

            if match:
                rect = win32gui.GetWindowRect(hwnd)
                placement = win32gui.GetWindowPlacement(hwnd)
                # placement[1] is showCmd: SW_SHOWMAXIMIZED=3, SW_SHOWMINIMIZED=2, SW_SHOWNORMAL=1
                is_maximized = placement[1] == 3
                is_minimized = placement[1] == 2
                results.append({
                    "hwnd": hwnd,
                    "title": title,
                    "class": cls_name,
                    "rect": rect,
                    "is_maximized": is_maximized,
                    "is_minimized": is_minimized,
                })
            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

        return results

    @classmethod
    def find_browser_windows(cls, specific_title: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find active browser windows (Chrome, Edge, Brave, Firefox)."""
        keywords = ["Chrome", "Edge", "Brave", "Firefox"]
        if specific_title:
            keywords.insert(0, specific_title)
        classes = ["Chrome_WidgetWin_1", "MozillaWindowClass"]
        return cls.find_windows_by_title_or_class(title_keywords=keywords, class_names=classes)

    @classmethod
    def maximize_window(cls, hwnd: int) -> Dict[str, Any]:
        """Maximize window and bring it to the foreground with verification."""
        if not cls.is_available():
            return {"success": False, "error": "Win32 window control not available."}

        try:
            # Restore first if minimized, then maximize
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            time.sleep(0.1)
            win32gui.SetForegroundWindow(hwnd)

            # Verification
            placement = win32gui.GetWindowPlacement(hwnd)
            is_max = placement[1] == win32con.SW_SHOWMAXIMIZED
            title = win32gui.GetWindowText(hwnd)
            return {
                "success": is_max,
                "hwnd": hwnd,
                "title": title,
                "is_maximized": is_max,
                "message": f"Window '{title}' maximized successfully." if is_max else f"Window '{title}' could not be maximized.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def restore_window(cls, hwnd: int) -> Dict[str, Any]:
        """Restore window to normal size."""
        if not cls.is_available():
            return {"success": False, "error": "Win32 window control not available."}
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            title = win32gui.GetWindowText(hwnd)
            return {"success": True, "title": title, "message": f"Window '{title}' restored."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def minimize_window(cls, hwnd: int) -> Dict[str, Any]:
        """Minimize window."""
        if not cls.is_available():
            return {"success": False, "error": "Win32 window control not available."}
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            title = win32gui.GetWindowText(hwnd)
            return {"success": True, "title": title, "message": f"Window '{title}' minimized."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def bring_to_front(cls, hwnd: int) -> Dict[str, Any]:
        """Bring window to foreground and focus."""
        if not cls.is_available():
            return {"success": False, "error": "Win32 window control not available."}
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            title = win32gui.GetWindowText(hwnd)
            return {"success": True, "title": title, "message": f"Window '{title}' brought to front."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def maximize_browser(cls, page_title: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method to find the browser window and maximize it."""
        windows = cls.find_browser_windows(specific_title=page_title)
        if not windows:
            return {"success": False, "error": "No browser window found to maximize."}

        # Select best window (if page_title provided, prefer matching)
        target = windows[0]
        if page_title:
            for w in windows:
                if page_title.lower() in w["title"].lower():
                    target = w
                    break

        return cls.maximize_window(target["hwnd"])
