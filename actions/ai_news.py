"""
actions/ai_news.py — Action tool for AI news briefings.

Provides concise, voice-formatted updates on the latest artificial intelligence
breakthroughs and industry announcements from Google AI, OpenAI, TechCrunch, and VentureBeat.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from news.news_manager import NewsManager

logger = logging.getLogger("AINewsAction")


def ai_news(parameters: Optional[Dict[str, Any]] = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "briefing").lower().strip()
    limit = int(params.get("limit", 3))
    force_refresh = action in ("refresh", "reload") or bool(params.get("force_refresh", False))

    briefing = NewsManager.get_briefing(limit=limit, force_refresh=force_refresh)

    if action in ("briefing", "speech", "voice", "summary"):
        result = briefing.get("speech_text", "No updates available at this time.")
    elif action in ("headlines", "list"):
        articles = briefing.get("articles", [])
        if not articles:
            result = "No AI news articles available."
        else:
            lines = [f"• [{a.get('source')}] {a.get('title')}" for a in articles]
            result = "Latest AI Headlines:\n" + "\n".join(lines)
    else:
        result = briefing.get("speech_text", "No updates available.")

    if player:
        try:
            player.write_log(f"[ai_news] {result[:80]}")
        except Exception:
            pass

    return result


TOOL = {
    "name": "ai_news",
    "description": "Provides the latest artificial intelligence news updates and voice briefings. Trigger when the user asks 'what is the latest AI news?', 'give me an AI briefing', or asks for tech/AI industry updates.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "briefing (conversational voice briefing) | headlines (bulleted headline list) | refresh (force fetch latest updates)",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Number of news items to include (default: 3)",
            },
            "force_refresh": {
                "type": "BOOLEAN",
                "description": "If true, bypasses the 1-hour cache and fetches fresh feeds directly",
            },
        },
        "required": [],
    },
    "handler": ai_news,
}
