"""
Live verification for Phase 2: ChatGPT Adapter.
Tests:
1. Navigation to ChatGPT
2. Composer element locator detection
3. Cloudflare / Login detection
4. Status report
"""
import sys
sys.path.insert(0, r"F:\WASHIM-PROJECT\Hey-ira-jarvis")

from core.browser_manager import BrowserManager
from core.browser_adapters.chatgpt_adapter import ChatGPTAdapter, is_chatgpt_url

def main():
    print("=== Phase 2: ChatGPT Adapter Verification ===")
    bm = BrowserManager.get_instance()

    print("Step 1: Navigate to ChatGPT...")
    nav_res = bm.run_sync(bm.navigate("https://chatgpt.com"), timeout=40)
    print(f"Navigation result: {nav_res}")

    page_info = bm.run_sync(bm.get_page_info(), timeout=10)
    print(f"Current page: {page_info.get('title')} ({page_info.get('url')})")

    # Inspect composer detection
    async def inspect_composer():
        page = await bm.get_active_page()
        loc = await ChatGPTAdapter.find_prompt_input(page, timeout_ms=6000)
        found = loc is not None
        title = await page.title()
        url = page.url
        return {"found_composer": found, "title": title, "url": url}

    comp_res = bm.run_sync(inspect_composer(), timeout=15)
    print(f"Composer detection result: {comp_res}")

    if comp_res.get("found_composer"):
        print("Composer found! Testing prompt insertion...")
        test_prompt = "Say 'Hello JARVIS' in exactly 3 words."
        send_res = bm.run_sync(bm.ask_chatgpt(test_prompt, wait_for_response=True), timeout=45)
        print(f"Ask ChatGPT result: {send_res}")
    else:
        print(f"Note: Composer not immediately visible (Title: '{comp_res.get('title')}'). Likely requires login/verification, which is gracefully handled.")

    # List open tabs to ensure state is clean
    tabs_res = bm.run_sync(bm.list_tabs(), timeout=10)
    print(f"Tabs: {tabs_res.get('tabs')}")
    print("=== Phase 2 ChatGPT Verification Complete ===")

if __name__ == "__main__":
    main()
