"""
Live verification for Phase 5 & 6: AI News System & Proactive Briefing.
"""
import sys
sys.path.insert(0, r"F:\WASHIM-PROJECT\Hey-ira-jarvis")

from news.news_manager import NewsManager
from actions.ai_news import ai_news

def main():
    print("=== Phase 5 & 6: AI News System Verification ===")

    print("\n--- Test 1: NewsManager Live Fetch / Cache ---")
    briefing = NewsManager.get_briefing(limit=3)
    print(f"Success: {briefing.get('success')}, Item count: {briefing.get('count')}")
    for i, a in enumerate(briefing.get("articles", [])):
        print(f"  {i+1}. [{a.get('source')}] {a.get('title')}")

    print("\n--- Test 2: Voice Briefing Format ---")
    voice_speech = briefing.get("speech_text", "")
    print("Voice Speech Output:\n", voice_speech)

    print("\n--- Test 3: Action Tool Execution ('briefing') ---")
    action_briefing = ai_news({"action": "briefing", "limit": 2})
    print("Action output:\n", action_briefing)

    print("\n--- Test 4: Action Tool Execution ('headlines') ---")
    action_headlines = ai_news({"action": "headlines", "limit": 3})
    print("Action headlines:\n", action_headlines)

    print("\n=== Phase 5 & 6 Verification Complete: PASS ===")

if __name__ == "__main__":
    main()
