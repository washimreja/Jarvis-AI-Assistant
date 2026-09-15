"""
Live verification for Phase 3: Window & Fullscreen Control.
Tests:
1. Navigate to a test page
2. Maximize window via WindowManager / browser_control
3. Toggle fullscreen ON via browser_control
4. Toggle fullscreen OFF via browser_control
"""
import sys
sys.path.insert(0, r"F:\WASHIM-PROJECT\Hey-ira-jarvis")

from actions.browser_control import browser_control

def main():
    print("=== Phase 3: Window & Fullscreen Control Verification ===")

    print("\n--- Test 1: Navigate to example.com ---")
    res1 = browser_control({"action": "navigate", "url": "https://example.com"})
    print("Navigate:", res1)

    print("\n--- Test 2: Maximize Window ---")
    res2 = browser_control({"action": "maximize"})
    print("Maximize:", res2)

    print("\n--- Test 3: Fullscreen ON ---")
    res3 = browser_control({"action": "fullscreen", "enable": True})
    print("Fullscreen ON:", res3)

    print("\n--- Test 4: Fullscreen OFF ---")
    res4 = browser_control({"action": "fullscreen", "enable": False})
    print("Fullscreen OFF:", res4)

    print("\n=== Phase 3 Verification Complete ===")

if __name__ == "__main__":
    main()
