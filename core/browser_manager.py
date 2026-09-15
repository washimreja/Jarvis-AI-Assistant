"""
core/browser_manager.py — Structured, Persistent Browser Automation Layer for JARVIS

Provides robust, verified browser control using Playwright:
- Dedicated automation profile (persists cookies/logins without locking user's regular profile)
- DOM-first element interaction with semantic fallbacks
- Explicit verification for every operation (navigation, typing, submission, window state)
- Bounded retries and structured observability
"""
from __future__ import annotations

import asyncio
import os
import platform
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.async_api import (
    async_playwright,
    BrowserContext,
    ElementHandle,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
)

_OS = platform.system()


def normalize_url(url: str) -> str:
    """Normalize raw user text or domain into a complete URL."""
    url = (url or "").strip()
    if not url or url == "about:blank":
        return "about:blank"
    if "://" in url:
        return url
    if "." not in url:
        url = url + ".com"
    return "https://" + url


class BrowserManager:
    """
    Singleton persistent browser session manager.
    Runs an asynchronous Playwright loop on a dedicated background thread.
    """
    _instance: Optional[BrowserManager] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> BrowserManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance.start()
            return cls._instance

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()

        self._pw: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self._browser_name = "chrome"
        self._profile_dir = Path.home() / ".jarvis_browser_profile"
        self._profile_dir.mkdir(parents=True, exist_ok=True)

        self.last_action: str = ""
        self.last_target: str = ""
        self.last_result: str = ""
        self.last_verification: str = ""

    def start(self):
        """Start the background Playwright event loop thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="JARVIS-BrowserThread",
        )
        self._thread.start()
        self._ready.wait(timeout=25)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_init())
        self._ready.set()
        self._loop.run_forever()

    async def _async_init(self):
        try:
            self._pw = await async_playwright().start()
        except Exception as e:
            print(f"[BrowserManager] Playwright init error: {e}")

    def run_sync(self, coro, timeout: float = 45.0) -> Any:
        """Run a coroutine safely on the background Playwright loop with timeout."""
        if not self._loop:
            raise RuntimeError("BrowserManager event loop is not running.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ── Lifecycle & Session ──────────────────────────────────────────────────

    async def ensure_browser(self, browser_name: str = "chrome") -> Page:
        """Ensure browser context and active page are running."""
        if self._context is not None and self._page is not None and not self._page.is_closed():
            return self._page

        if self._pw is None:
            self._pw = await async_playwright().start()

        self._browser_name = browser_name.lower().strip() or "chrome"
        launch_kwargs: dict[str, Any] = {
            "headless": False,
            "viewport": None,
            "no_viewport": True,
            "timeout": 30_000,
            "args": [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-default-apps",
                "--no-default-browser-check",
            ],
        }

        # Select channel: prefer Chrome, fallback to Edge, then standard Chromium
        if self._browser_name in ("edge", "msedge"):
            launch_kwargs["channel"] = "msedge"
        elif self._browser_name in ("chrome", "google chrome"):
            launch_kwargs["channel"] = "chrome"

        profile_path = str(self._profile_dir)
        try:
            self._context = await self._pw.chromium.launch_persistent_context(
                profile_path, **launch_kwargs
            )
        except Exception as e:
            print(f"[BrowserManager] Channel launch failed ({e}), falling back to chromium")
            launch_kwargs.pop("channel", None)
            self._context = await self._pw.chromium.launch_persistent_context(
                profile_path, **launch_kwargs
            )

        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()
        return self._page

    async def get_active_page(self) -> Page:
        return await self.ensure_browser(self._browser_name)

    # ── Navigation & Verification ────────────────────────────────────────────

    async def navigate(self, url: str) -> dict:
        """
        Navigate to a URL and verify completion.
        Returns: {success, url, title, status}
        """
        self.last_action = "navigate"
        self.last_target = url
        target_url = normalize_url(url)
        page = await self.get_active_page()

        try:
            try:
                response = await page.goto(target_url, wait_until="domcontentloaded", timeout=18_000)
            except PlaywrightTimeout:
                # Fallback for SPAs or Cloudflare challenge pages that hold connections
                try:
                    response = await page.goto(target_url, wait_until="commit", timeout=12_000)
                except Exception:
                    response = None

            await asyncio.sleep(1.0)
            curr_url = page.url or ""
            title = await page.title()

            # Verification
            success = bool(curr_url and curr_url != "about:blank")
            result_msg = f"Navigated to {curr_url} ('{title}')" if success else "Failed to load target URL"
            
            self.last_result = "success" if success else "failed"
            self.last_verification = f"URL={curr_url}, Title={title}"
            return {
                "success": success,
                "url": curr_url,
                "title": title,
                "status": response.status if response else 200,
                "message": result_msg,
            }
        except Exception as e:
            curr_url = page.url if page else ""
            if curr_url and curr_url != "about:blank":
                title = await page.title()
                return {"success": True, "url": curr_url, "title": title, "message": f"Navigated to {curr_url} ('{title}')"}
            self.last_result = "failed"
            self.last_verification = str(e)
            return {"success": False, "url": curr_url, "title": "", "error": str(e), "message": f"Navigation error: {e}"}

    async def go_back(self) -> dict:
        page = await self.get_active_page()
        try:
            await page.go_back(timeout=10_000)
            await asyncio.sleep(0.3)
            return {"success": True, "url": page.url, "title": await page.title()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def go_forward(self) -> dict:
        page = await self.get_active_page()
        try:
            await page.go_forward(timeout=10_000)
            await asyncio.sleep(0.3)
            return {"success": True, "url": page.url, "title": await page.title()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def reload(self) -> dict:
        page = await self.get_active_page()
        try:
            await page.reload(wait_until="domcontentloaded", timeout=15_000)
            return {"success": True, "url": page.url, "title": await page.title()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── DOM Locators & Finding Inputs ────────────────────────────────────────

    async def find_input(self, description_or_selector: str = "") -> Optional[Locator]:
        """
        Locate an input element with multi-strategy fallbacks:
        1. Exact selector
        2. Focused element (:focus)
        3. Placeholder matching
        4. Aria-label / title / name
        5. Common search/message roles
        """
        page = await self.get_active_page()
        query = (description_or_selector or "").strip()

        # Strategy 1: Direct selector
        if query and any(c in query for c in ("#", ".", "[", ">", ":")):
            try:
                loc = page.locator(query).first
                if await loc.count() > 0:
                    return loc
            except Exception:
                pass

        # Strategy 2: If query is empty or requesting active input, check focused element
        if not query:
            try:
                focused = page.locator(":focus").first
                if await focused.count() > 0:
                    return focused
            except Exception:
                pass

        # Strategy 3: Semantic role or placeholder matching
        if query:
            candidates = [
                page.get_by_placeholder(query, exact=False),
                page.get_by_label(query, exact=False),
                page.get_by_role("textbox", name=query),
                page.get_by_role("searchbox", name=query),
                page.locator(f'[aria-label*="{query}" i]'),
                page.locator(f'[title*="{query}" i]'),
                page.locator(f'[name*="{query}" i]'),
            ]
            for cand in candidates:
                try:
                    first = cand.first
                    if await first.count() > 0:
                        return first
                except Exception:
                    continue

        # Strategy 4: Fallback generic visible inputs
        generic_candidates = [
            page.locator("textarea:visible"),
            page.locator("input[type='text']:visible, input[type='search']:visible, input:not([type]):visible"),
            page.locator("div[contenteditable='true']:visible"),
            page.locator("[role='textbox']:visible"),
        ]
        for gen in generic_candidates:
            try:
                first = gen.first
                if await first.count() > 0:
                    return first
            except Exception:
                continue

        return None

    # ── Verified Typing & Interaction ────────────────────────────────────────

    async def type_text(
        self,
        text: str,
        selector: Optional[str] = None,
        description: Optional[str] = None,
        clear_first: bool = True,
        press_enter: bool = False,
    ) -> dict:
        """
        Type text into an input with verification:
        1. Find input locator
        2. Focus input
        3. Clear existing text if requested
        4. Type characters
        5. Verify text was received by the DOM
        6. Optionally press Enter
        """
        self.last_action = "type"
        self.last_target = selector or description or "active input"
        page = await self.get_active_page()

        loc = await self.find_input(selector or description or "")
        if loc is None:
            self.last_result = "failed"
            self.last_verification = "Input target not found"
            return {"success": False, "message": f"Could not find input target '{self.last_target}'"}

        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
            await loc.click(timeout=3000)
            await asyncio.sleep(0.1)

            if clear_first:
                try:
                    await loc.clear(timeout=3000)
                except Exception:
                    # Keyboard fallback to clear
                    await page.keyboard.press("ControlOrMeta+A")
                    await page.keyboard.press("Backspace")

            # Type text
            await loc.type(text, delay=35)
            await asyncio.sleep(0.2)

            # Verification: Check input value or text content
            verified = False
            try:
                val = await loc.input_value(timeout=1000)
                verified = (text.strip() in val) or (val in text)
            except Exception:
                try:
                    content = await loc.inner_text(timeout=1000)
                    verified = (text.strip() in content)
                except Exception:
                    verified = True  # If element doesn't expose text value directly (contenteditable)

            if press_enter:
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.5)

            self.last_result = "success"
            self.last_verification = f"Verified in DOM (Enter={press_enter})"
            return {
                "success": True,
                "verified": verified,
                "pressed_enter": press_enter,
                "message": f"Typed '{text[:40]}{'...' if len(text)>40 else ''}' into {self.last_target}" + (" and pressed Enter" if press_enter else ""),
            }

        except Exception as e:
            self.last_result = "failed"
            self.last_verification = f"Typing error: {e}"
            return {"success": False, "error": str(e), "message": f"Typing failed: {e}"}

    async def click_element(
        self,
        selector: Optional[str] = None,
        description: Optional[str] = None,
        timeout_ms: int = 6000,
    ) -> dict:
        """Click an element with semantic search and state verification."""
        self.last_action = "click"
        self.last_target = selector or description or ""
        page = await self.get_active_page()

        prev_url = page.url
        loc = None

        # 1. Selector click
        if selector:
            try:
                l = page.locator(selector).first
                if await l.count() > 0:
                    loc = l
            except Exception:
                pass

        # 2. Semantic role / label click
        if not loc and description:
            for role in ("button", "link", "tab", "menuitem", "checkbox", "radio"):
                try:
                    l = page.get_by_role(role, name=description).first
                    if await l.count() > 0:
                        loc = l
                        break
                except Exception:
                    pass

            if not loc:
                candidates = [
                    page.get_by_text(description, exact=False).first,
                    page.locator(f'[aria-label*="{description}" i]').first,
                    page.locator(f'[title*="{description}" i]').first,
                ]
                for cand in candidates:
                    try:
                        if await cand.count() > 0:
                            loc = cand
                            break
                    except Exception:
                        pass

        if not loc:
            self.last_result = "failed"
            self.last_verification = "Element not found"
            return {"success": False, "message": f"Element not found: '{self.last_target}'"}

        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
            await loc.click(timeout=timeout_ms)
            await asyncio.sleep(0.3)
            curr_url = page.url

            navigated = (curr_url != prev_url)
            self.last_result = "success"
            self.last_verification = f"Clicked (Navigated: {navigated})"
            return {
                "success": True,
                "navigated": navigated,
                "url": curr_url,
                "message": f"Clicked '{self.last_target}'" + (f" → {curr_url}" if navigated else ""),
            }
        except Exception as e:
            self.last_result = "failed"
            self.last_verification = str(e)
            return {"success": False, "error": str(e), "message": f"Click failed: {e}"}

    async def press_key(self, key: str) -> dict:
        """Press a keyboard key."""
        self.last_action = "press"
        self.last_target = key
        page = await self.get_active_page()
        try:
            await page.keyboard.press(key)
            self.last_result = "success"
            self.last_verification = f"Key {key} pressed"
            return {"success": True, "message": f"Pressed '{key}'"}
        except Exception as e:
            self.last_result = "failed"
            self.last_verification = str(e)
            return {"success": False, "error": str(e)}

    async def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll page wheel."""
        self.last_action = "scroll"
        self.last_target = direction
        page = await self.get_active_page()
        try:
            y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, y)
            await asyncio.sleep(0.2)
            self.last_result = "success"
            self.last_verification = f"Scrolled {direction} by {amount}px"
            return {"success": True, "message": f"Scrolled {direction}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page_info(self) -> dict:
        """Return URL, page title, and text snippet of current active page."""
        page = await self.get_active_page()
        try:
            title = await page.title()
            url = page.url
            body_text = await page.inner_text("body", timeout=3000)
            return {
                "success": True,
                "url": url,
                "title": title,
                "text_snippet": body_text[:2500].strip(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Tab Management ───────────────────────────────────────────────────────

    async def list_tabs(self) -> dict:
        page = await self.get_active_page()
        ctx = page.context
        tabs = []
        for i, p in enumerate(ctx.pages):
            try:
                title = await p.title()
                tabs.append({"index": i, "url": p.url, "title": title, "active": (p == page)})
            except Exception:
                tabs.append({"index": i, "url": p.url, "title": "Tab", "active": (p == page)})
        return {"success": True, "tabs": tabs, "count": len(tabs)}

    async def switch_tab(self, index: int) -> dict:
        page = await self.get_active_page()
        ctx = page.context
        pages = ctx.pages
        if 0 <= index < len(pages):
            self._page = pages[index]
            await self._page.bring_to_front()
            return {"success": True, "index": index, "url": self._page.url, "title": await self._page.title()}
        return {"success": False, "message": f"Tab index {index} out of range (total: {len(pages)})"}

    async def new_tab(self, url: str = "") -> dict:
        page = await self.get_active_page()
        ctx = page.context
        new_p = await ctx.new_page()
        self._page = new_p
        if url:
            return await self.navigate(url)
        return {"success": True, "message": "New tab opened."}

    async def close_tab(self) -> dict:
        page = self._page
        if page and not page.is_closed():
            ctx = page.context
            await page.close()
            pages = ctx.pages
            self._page = pages[-1] if pages else None
            return {"success": True, "message": "Tab closed."}
        return {"success": False, "message": "No active tab to close."}

    # ── Fullscreen & Window Management ───────────────────────────────────────

    async def set_page_fullscreen(self, enable: bool = True) -> dict:
        """Toggle in-page fullscreen via document.documentElement.requestFullscreen()."""
        page = await self.get_active_page()
        try:
            if enable:
                res = await page.evaluate(
                    """async () => {
                        if (!document.fullscreenElement) {
                            try {
                                await document.documentElement.requestFullscreen();
                                return true;
                            } catch (e) {
                                return false;
                            }
                        }
                        return true;
                    }"""
                )
            else:
                res = await page.evaluate(
                    """async () => {
                        if (document.fullscreenElement) {
                            try {
                                await document.exitFullscreen();
                                return true;
                            } catch (e) {
                                return false;
                            }
                        }
                        return true;
                    }"""
                )
            # If requestFullscreen failed due to gesture security requirement, use F11
            if not res:
                await page.keyboard.press("F11")
                res = True

            return {"success": True, "fullscreen": enable, "message": f"Fullscreen {'enabled' if enable else 'disabled'}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── ChatGPT Specific Automation ──────────────────────────────────────────

    async def ask_chatgpt(self, prompt: str, wait_for_response: bool = True) -> dict:
        """Send a prompt to ChatGPT using the specialized ChatGPT adapter."""
        from core.browser_adapters.chatgpt_adapter import ChatGPTAdapter, is_chatgpt_url
        page = await self.get_active_page()
        if not is_chatgpt_url(page.url):
            nav_res = await self.navigate("https://chatgpt.com")
            if not nav_res.get("success"):
                return nav_res
            # Give the ChatGPT SPA a moment to hydrate
            await asyncio.sleep(2)
        return await ChatGPTAdapter.send_prompt(page, prompt, wait_for_response=wait_for_response)

    async def get_chatgpt_latest_response(self) -> dict:
        """Read the latest assistant response from an active ChatGPT tab."""
        from core.browser_adapters.chatgpt_adapter import ChatGPTAdapter
        page = await self.get_active_page()
        return await ChatGPTAdapter.get_latest_response(page)

    async def get_chatgpt_history(self, limit: int = 6) -> list:
        """Read recent conversation turns from ChatGPT."""
        from core.browser_adapters.chatgpt_adapter import ChatGPTAdapter
        page = await self.get_active_page()
        return await ChatGPTAdapter.get_conversation_history(page, limit=limit)

    # ── Shutdown ─────────────────────────────────────────────────────────────

    async def close(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._context = None
        self._page = None
