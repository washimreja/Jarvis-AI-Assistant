import sys
import time
from core.browser_manager import BrowserManager

def test_phase1():
    print("[TEST] Getting BrowserManager instance...")
    bm = BrowserManager.get_instance()
    
    print("[TEST] 1. Testing Navigation to https://duckduckgo.com...")
    res_nav = bm.run_sync(bm.navigate("https://duckduckgo.com"), timeout=30)
    print("  Navigation result:", res_nav)
    assert res_nav.get("success"), f"Navigation failed: {res_nav}"
    assert "duckduckgo" in res_nav.get("url", "").lower(), f"Unexpected URL: {res_nav.get('url')}"
    print("  [PASS] Navigation verified!")

    print("[TEST] 2. Testing Typing 'JARVIS AI Assistant' into search box...")
    res_type = bm.run_sync(bm.type_text("JARVIS AI Assistant", selector="input[name='q']", clear_first=True, press_enter=True), timeout=30)
    print("  Typing result:", res_type)
    assert res_type.get("success"), f"Typing failed: {res_type}"
    print("  [PASS] Typing and Enter submission verified!")

    time.sleep(2)

    print("[TEST] 3. Testing Reading Page Info...")
    res_info = bm.run_sync(bm.get_page_info(), timeout=15)
    print("  Page title:", res_info.get("title"))
    print("  Page URL:", res_info.get("url"))
    print("  Snippet sample:", res_info.get("text_snippet", "")[:100], "...")
    assert "jarvis" in res_info.get("url", "").lower() or "jarvis" in res_info.get("title", "").lower() or len(res_info.get("text_snippet", "")) > 50
    print("  [PASS] Page info verified!")

    print("[TEST] 4. Testing Scrolling...")
    res_scroll = bm.run_sync(bm.scroll("down", 400), timeout=10)
    print("  Scroll result:", res_scroll)
    assert res_scroll.get("success")
    print("  [PASS] Scroll verified!")

    print("[TEST] 5. Testing Tab Management...")
    res_tabs = bm.run_sync(bm.list_tabs(), timeout=10)
    print("  Tab list count:", res_tabs.get("count"))
    assert res_tabs.get("count", 0) >= 1
    print("  [PASS] Tab listing verified!")

    print("\n==========================================")
    print("ALL PHASE 1 BROWSER TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    try:
        test_phase1()
    except Exception as e:
        print("[FAIL] Exception during test:", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
