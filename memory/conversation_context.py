"""
memory/conversation_context.py — Recent Conversation Context Tracking & Recall for JARVIS.

Tracks recent conversation turns (from JARVIS voice sessions, command runs,
and live browser ChatGPT sessions) and provides instant recall answering:
"JARVIS, what was my last conversation?"
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ConversationContext")

_LOCK = threading.Lock()
_BASE_DIR = Path(__file__).resolve().parent.parent
_HISTORY_FILE = _BASE_DIR / "memory" / "conversation_history.json"
_MAX_STORED_TURNS = 100


class ConversationContextManager:
    """Manages recording and structured recall of recent conversations."""

    @classmethod
    def _load_history(cls) -> List[Dict[str, Any]]:
        if not _HISTORY_FILE.exists():
            return []
        try:
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
            return []

    @classmethod
    def _save_history(cls, history: List[Dict[str, Any]]) -> None:
        try:
            _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history[-_MAX_STORED_TURNS:], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")

    @classmethod
    def record_turn(
        cls,
        user_message: str,
        assistant_response: str,
        source: str = "jarvis",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a single user-assistant conversational turn."""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "time_display": datetime.now().strftime("%I:%M %p, %b %d"),
            "source": source,
            "user_message": (user_message or "").strip(),
            "assistant_response": (assistant_response or "").strip(),
            "metadata": metadata or {},
        }
        with _LOCK:
            history = cls._load_history()
            history.append(turn)
            cls._save_history(history)
        return turn

    @classmethod
    def get_last_turn(cls) -> Optional[Dict[str, Any]]:
        """Retrieve the single most recent conversation turn from local history."""
        with _LOCK:
            history = cls._load_history()
            return history[-1] if history else None

    @classmethod
    def get_recent_turns(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent conversation turns from local history."""
        with _LOCK:
            history = cls._load_history()
            return history[-limit:] if history else []

    @classmethod
    def get_browser_chatgpt_context(cls) -> Optional[Dict[str, Any]]:
        """
        Check if an active ChatGPT session exists in the browser and fetch
        its recent conversation history.
        """
        try:
            from core.browser_manager import BrowserManager
            from core.browser_adapters.chatgpt_adapter import is_chatgpt_url

            bm = BrowserManager.get_instance()
            page_info = bm.run_sync(bm.get_page_info(), timeout=4)
            if page_info.get("success") and is_chatgpt_url(page_info.get("url", "")):
                history = bm.run_sync(bm.get_chatgpt_history(limit=4), timeout=5)
                if history:
                    last_user = next((t["text"] for t in reversed(history) if t["role"] == "user"), "")
                    last_asst = next((t["text"] for t in reversed(history) if t["role"] == "assistant"), "")
                    return {
                        "source": "chatgpt_browser",
                        "url": page_info.get("url"),
                        "turns": history,
                        "last_user": last_user,
                        "last_asst": last_asst,
                    }
        except Exception as e:
            logger.debug(f"Could not inspect browser ChatGPT context: {e}")
        return None

    @classmethod
    def recall_last_conversation(cls) -> Dict[str, Any]:
        """
        Synthesize the last conversation from either active browser ChatGPT
        or local JARVIS history, formatting a voice-ready response.
        """
        # 1. Check browser ChatGPT if active
        bg_chatgpt = cls.get_browser_chatgpt_context()
        if bg_chatgpt and (bg_chatgpt.get("last_user") or bg_chatgpt.get("last_asst")):
            u = bg_chatgpt.get("last_user", "")
            a = bg_chatgpt.get("last_asst", "")
            snippet = a[:180] + "..." if len(a) > 180 else a
            speech = f"In your active ChatGPT session, you asked: '{u}'. ChatGPT answered: '{snippet}'."
            return {
                "source": "chatgpt_browser",
                "user_message": u,
                "assistant_response": a,
                "speech_summary": speech,
            }

        # 2. Check local history
        last_turn = cls.get_last_turn()
        if last_turn:
            u = last_turn.get("user_message", "")
            a = last_turn.get("assistant_response", "")
            t = last_turn.get("time_display", "recently")
            snippet = a[:180] + "..." if len(a) > 180 else a
            speech = f"At {t}, you asked: '{u}'. I responded: '{snippet}'."
            return {
                "source": last_turn.get("source", "jarvis"),
                "timestamp": last_turn.get("timestamp"),
                "user_message": u,
                "assistant_response": a,
                "speech_summary": speech,
            }

        return {
            "source": "none",
            "speech_summary": "I don't have any recent conversations recorded in this session yet.",
        }
