"""
actions/conversation_memory.py — Action tool for recent conversation recall.

Enables JARVIS to answer questions such as:
"JARVIS, what was my last conversation?"
"What did I ask ChatGPT earlier?"
"What was the last topic we discussed?"
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from memory.conversation_context import ConversationContextManager

logger = logging.getLogger("ConversationMemoryAction")


def conversation_context(parameters: Optional[Dict[str, Any]] = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "get_last").lower().strip()
    limit = int(params.get("limit", 5))

    if action in ("get_last", "last", "recall"):
        info = ConversationContextManager.recall_last_conversation()
        summary = info.get("speech_summary", "No recent conversations found.")
        if player:
            try:
                player.write_log(f"[context] {summary[:80]}")
            except Exception:
                pass
        return summary

    elif action in ("list_recent", "history", "recent"):
        turns = ConversationContextManager.get_recent_turns(limit=limit)
        if not turns:
            return "No recent conversations found in history."
        lines = []
        for t in turns:
            time_str = t.get("time_display", "")
            user_msg = t.get("user_message", "")
            asst_msg = t.get("assistant_response", "")
            lines.append(f"• [{time_str}] You: {user_msg}\n  JARVIS: {asst_msg[:100]}...")
        return "Recent conversations:\n" + "\n".join(lines)

    elif action == "record":
        user_msg = params.get("user_message", "")
        asst_msg = params.get("assistant_response", "")
        source = params.get("source", "jarvis")
        if user_msg and asst_msg:
            ConversationContextManager.record_turn(user_msg, asst_msg, source=source)
            return "Conversation turn recorded."
        return "Missing user_message or assistant_response to record."

    return f"Unknown conversation action: '{action}'"


TOOL = {
    "name": "conversation_context",
    "description": "Recalls recent conversations, chats, or queries. Use when the user asks 'what was my last conversation?', 'what did we just talk about?', or asks about their recent ChatGPT session.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "get_last (recall the most recent conversation) | list_recent (list last few turns) | record",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Number of recent turns to retrieve (default: 5)",
            },
            "user_message": {
                "type": "STRING",
                "description": "User message if recording a turn manually",
            },
            "assistant_response": {
                "type": "STRING",
                "description": "Assistant response if recording a turn manually",
            },
        },
        "required": ["action"],
    },
    "handler": conversation_context,
}
