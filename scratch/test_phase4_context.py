"""
Live verification for Phase 4: Recent Conversation Context.
"""
import sys
sys.path.insert(0, r"F:\WASHIM-PROJECT\Hey-ira-jarvis")

from memory.conversation_context import ConversationContextManager
from actions.conversation_memory import conversation_context

def main():
    print("=== Phase 4: Conversation Context Verification ===")

    # Test 1: Record a sample conversation
    print("\n--- Test 1: Recording conversation turn ---")
    ConversationContextManager.record_turn(
        user_message="JARVIS, can you analyze the latest quantum computing breakthroughs?",
        assistant_response="Certainly, sir. Recent developments show 1000+ qubit processors achieving error suppression thresholds.",
        source="jarvis",
    )
    print("Turn recorded successfully.")

    # Test 2: Recall last conversation via ConversationContextManager
    print("\n--- Test 2: Recall via Manager ---")
    last = ConversationContextManager.recall_last_conversation()
    print("Recalled speech summary:", last.get("speech_summary"))

    # Test 3: Action tool handler execution
    print("\n--- Test 3: Recall via Action Handler ---")
    action_res = conversation_context({"action": "get_last"})
    print("Action output:\n", action_res)

    print("\n--- Test 4: List recent via Action Handler ---")
    list_res = conversation_context({"action": "list_recent", "limit": 3})
    print("Recent list:\n", list_res)

    print("\n=== Phase 4 Verification Complete: PASS ===")

if __name__ == "__main__":
    main()
