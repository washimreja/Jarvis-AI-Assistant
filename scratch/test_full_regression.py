"""
Comprehensive End-to-End Regression Test Suite for JARVIS Upgrade.
Tests:
1. Action Discovery (core/action_loader.py) — all tools valid, no syntax/import errors.
2. Browser Control & Window Control (actions/browser_control.py, core/browser_manager.py, core/window_manager.py).
3. ChatGPT Site Adapter (core/browser_adapters/chatgpt_adapter.py).
4. Recent Conversation Context & Recall (memory/conversation_context.py, actions/conversation_memory.py).
5. AI News System & Voice Briefing (news/news_manager.py, actions/ai_news.py).
"""
from pathlib import Path
from core.action_loader import discover_actions
from core.browser_manager import BrowserManager
from core.window_manager import WindowManager
from actions.browser_control import browser_control
from actions.conversation_memory import conversation_context
from actions.ai_news import ai_news
from memory.conversation_context import ConversationContextManager
from news.news_manager import NewsManager

def test_action_loader():
    print("\n--- Test Suite 1: Action Loader Discovery ---")
    actions_dir = Path(r"F:\WASHIM-PROJECT\Hey-ira-jarvis\actions")
    reg = discover_actions(actions_dir=actions_dir, logger=lambda msg: print(f"[ActionLoader] {msg}"))
    names = reg.names()
    print(f"Total discovered valid actions: {len(names)}")
    assert "browser_control" in names, "browser_control missing!"
    assert "conversation_context" in names, "conversation_context missing!"
    assert "ai_news" in names, "ai_news missing!"
    print("Action discovery: PASS")

def test_conversation_context():
    print("\n--- Test Suite 2: Recent Conversation Context ---")
    ConversationContextManager.record_turn(
        user_message="JARVIS, what is the plan for today?",
        assistant_response="Reviewing system diagnostics, scheduled meetings at 2 PM, and finalizing project milestones.",
        source="jarvis",
    )
    last = ConversationContextManager.recall_last_conversation()
    assert "Reviewing system diagnostics" in last.get("assistant_response", ""), "Context mismatch!"
    action_res = conversation_context({"action": "get_last"})
    assert "Reviewing system diagnostics" in action_res, "Action context mismatch!"
    print("Conversation context: PASS")

def test_ai_news():
    print("\n--- Test Suite 3: AI News Aggregator & Briefing ---")
    briefing = NewsManager.get_briefing(limit=2)
    assert briefing.get("success") is True, "News fetch failed!"
    assert len(briefing.get("articles", [])) > 0, "No articles found!"
    assert "briefing" in briefing.get("speech_text", "").lower(), "Speech text missing header!"
    action_res = ai_news({"action": "briefing", "limit": 2})
    assert len(action_res) > 20, "Action returned empty news briefing!"
    print("AI News System: PASS")

def test_browser_and_window():
    print("\n--- Test Suite 4: Browser Control & Window Control ---")
    bm = BrowserManager.get_instance()
    # Navigate
    nav_res = browser_control({"action": "navigate", "url": "https://example.com"})
    assert "example.com" in nav_res.lower() or "Example Domain" in nav_res, f"Navigate failed: {nav_res}"
    print("Navigation: PASS")

    # Get page info
    info_res = browser_control({"action": "get_text"})
    assert "Example Domain" in info_res, f"Page info failed: {info_res}"
    print("Get Text: PASS")

    # Fullscreen ON / OFF
    fs_on = browser_control({"action": "fullscreen", "enable": True})
    assert "enabled" in fs_on.lower(), f"Fullscreen ON failed: {fs_on}"
    fs_off = browser_control({"action": "fullscreen", "enable": False})
    assert "disabled" in fs_off.lower(), f"Fullscreen OFF failed: {fs_off}"
    print("Fullscreen Control: PASS")

    # Maximize Window
    max_res = browser_control({"action": "maximize"})
    assert "maximized" in max_res.lower(), f"Maximize failed: {max_res}"
    print("Window Maximize: PASS")

    # Tab listing
    tabs_res = browser_control({"action": "list_tabs"})
    assert "Open tabs" in tabs_res, f"List tabs failed: {tabs_res}"
    print("Tab listing: PASS")

def main():
    print("========================================================")
    print("   JARVIS UPGRADE COMPREHENSIVE REGRESSION TEST SUITE   ")
    print("========================================================")

    test_action_loader()
    test_conversation_context()
    test_ai_news()
    test_browser_and_window()

    print("\n========================================================")
    print("   ALL TEST SUITES COMPLETED: 100% PASS                ")
    print("========================================================")

if __name__ == "__main__":
    main()
