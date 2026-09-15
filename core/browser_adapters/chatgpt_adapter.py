"""
ChatGPT Browser Adapter for JARVIS.

Provides reliable detection, input insertion, submission, and response
extraction for ChatGPT (chatgpt.com / chat.openai.com).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger("ChatGPTAdapter")


def is_chatgpt_url(url: str) -> bool:
    """Check if the given URL points to ChatGPT."""
    lowered = (url or "").lower()
    return "chatgpt.com" in lowered or "chat.openai.com" in lowered


class ChatGPTAdapter:
    """Site adapter for interacting with ChatGPT in Playwright."""

    INPUT_SELECTORS = [
        "#prompt-textarea",
        "div#prompt-textarea",
        "div[contenteditable='true']",
        "textarea[placeholder*='Message']",
        "textarea[placeholder*='Ask']",
        "div[data-placeholder*='Message']",
        "div[data-placeholder*='Ask']",
        "[data-testid='prompt-textarea']",
        "textarea",
    ]

    SEND_SELECTORS = [
        "button[data-testid='send-button']",
        "button[data-testid='fruitjuice-send-button']",
        "button[aria-label='Send prompt']",
        "button[aria-label*='Send']",
        "button[aria-label*='Submit']",
    ]

    STOP_SELECTORS = [
        "button[data-testid='stop-button']",
        "button[aria-label*='Stop']",
        "button[aria-label*='stop']",
        "[data-testid*='stop']",
    ]

    RESPONSE_SELECTORS = [
        "div[data-message-author-role='assistant']",
        "article[data-testid*='conversation-turn'] div[data-message-author-role='assistant']",
        ".markdown.prose",
        "div.agent-turn",
    ]

    @classmethod
    async def find_prompt_input(cls, page: Page, timeout_ms: int = 8000) -> Optional[Locator]:
        """Locate the chat prompt composer element with multiple fallbacks."""
        for sel in cls.INPUT_SELECTORS:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=1000):
                    return loc
            except Exception:
                continue

        # Broader wait if initial passes failed
        for sel in cls.INPUT_SELECTORS[:3]:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=timeout_ms // 3)
                return loc
            except Exception:
                continue

        return None

    @classmethod
    async def send_prompt(
        cls,
        page: Page,
        prompt: str,
        wait_for_response: bool = True,
        max_response_wait_sec: int = 60,
    ) -> Dict[str, Any]:
        """
        Types the given prompt into ChatGPT, submits it, and optionally waits
        for the assistant's response to complete.
        """
        current_url = page.url or ""
        if not is_chatgpt_url(current_url):
            logger.info("Current page is not ChatGPT; navigating to https://chatgpt.com")
            try:
                await page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to navigate to ChatGPT: {e}",
                    "current_url": page.url,
                }

        # Check for Cloudflare / Login block
        page_title = await page.title()
        if "just a moment" in page_title.lower() or "cloudflare" in page_title.lower():
            return {
                "success": False,
                "error": "ChatGPT is blocked by Cloudflare verification. Please complete the verification in the browser window.",
                "url": page.url,
            }

        input_loc = await cls.find_prompt_input(page)
        if not input_loc:
            return {
                "success": False,
                "error": "Could not locate ChatGPT prompt composer. You may need to log in or wait for page load.",
                "url": page.url,
                "title": page_title,
            }

        # Focus and insert prompt
        try:
            await input_loc.click()
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"Click on prompt input failed: {e}")

        # Try multiple typing mechanisms for contenteditable / textarea
        inserted = False
        try:
            await input_loc.fill(prompt)
            inserted = True
        except Exception:
            try:
                await page.keyboard.type(prompt, delay=10)
                inserted = True
            except Exception:
                try:
                    await input_loc.evaluate(
                        """(el, text) => {
                            if (el.tagName.toLowerCase() === 'textarea') {
                                el.value = text;
                            } else {
                                el.textContent = text;
                            }
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        prompt,
                    )
                    inserted = True
                except Exception as e:
                    return {"success": False, "error": f"Failed to insert text into ChatGPT: {e}"}

        # Verify insertion in DOM
        verify_text = await input_loc.evaluate(
            "el => el.value || el.textContent || el.innerText || ''"
        )
        if not verify_text and not inserted:
            return {"success": False, "error": "Prompt insertion verification failed (input remains empty)."}

        await asyncio.sleep(0.5)

        # Click send or press Enter
        submitted = False
        for send_sel in cls.SEND_SELECTORS:
            try:
                btn = page.locator(send_sel).first
                if await btn.count() > 0 and await btn.is_visible(timeout=800):
                    # Check if disabled
                    is_disabled = await btn.get_attribute("disabled")
                    aria_disabled = await btn.get_attribute("aria-disabled")
                    if not is_disabled and aria_disabled != "true":
                        await btn.click()
                        submitted = True
                        break
            except Exception:
                continue

        if not submitted:
            # Fallback to pressing Enter
            try:
                await input_loc.press("Enter")
                submitted = True
            except Exception:
                await page.keyboard.press("Enter")
                submitted = True

        logger.info(f"ChatGPT prompt submitted: '{prompt[:50]}...'")

        if not wait_for_response:
            return {
                "success": True,
                "message": f"Prompt submitted to ChatGPT: '{prompt[:60]}...'",
                "prompt": prompt,
                "waiting_for_response": False,
            }

        # Wait for generation to start and complete
        response_info = await cls.wait_for_response_completion(
            page, timeout_sec=max_response_wait_sec
        )

        return {
            "success": True,
            "message": f"ChatGPT responded: {response_info.get('snippet', '')[:120]}...",
            "prompt": prompt,
            "response": response_info.get("full_text", ""),
            "snippet": response_info.get("snippet", ""),
        }

    @classmethod
    async def wait_for_response_completion(
        cls, page: Page, timeout_sec: int = 60
    ) -> Dict[str, str]:
        """
        Waits for ChatGPT to finish generating its response.
        Detects streaming stop button and stabilizes the assistant's message.
        """
        # Brief pause for streaming to begin
        await asyncio.sleep(1.5)

        # 1. Wait for stop button to appear (indicating generation started) or finish directly
        stop_seen = False
        start_wait = asyncio.get_event_loop().time()

        for _ in range(10):
            for stop_sel in cls.STOP_SELECTORS:
                try:
                    btn = page.locator(stop_sel).first
                    if await btn.count() > 0 and await btn.is_visible(timeout=500):
                        stop_seen = True
                        break
                except Exception:
                    pass
            if stop_seen:
                break
            await asyncio.sleep(0.5)

        # 2. Wait for stop button to disappear (indicating generation finished)
        if stop_seen:
            elapsed = asyncio.get_event_loop().time() - start_wait
            remaining = max(10, timeout_sec - int(elapsed))
            for stop_sel in cls.STOP_SELECTORS:
                try:
                    btn = page.locator(stop_sel).first
                    if await btn.count() > 0:
                        await btn.wait_for(state="hidden", timeout=remaining * 1000)
                        break
                except Exception:
                    pass

        # Stabilize
        await asyncio.sleep(1.0)

        # 3. Extract latest assistant message
        return await cls.get_latest_response(page)

    @classmethod
    async def get_latest_response(cls, page: Page) -> Dict[str, str]:
        """Extract the last response from ChatGPT."""
        for sel in cls.RESPONSE_SELECTORS:
            try:
                msgs = page.locator(sel)
                cnt = await msgs.count()
                if cnt > 0:
                    last_msg = msgs.nth(cnt - 1)
                    text = await last_msg.inner_text()
                    text = (text or "").strip()
                    if text:
                        snippet = text[:250].replace("\n", " ")
                        return {"full_text": text, "snippet": snippet}
            except Exception:
                continue

        # Generic fallback: get latest turn text
        try:
            turns = page.locator("article")
            cnt = await turns.count()
            if cnt > 0:
                last_turn = turns.nth(cnt - 1)
                text = (await last_turn.inner_text() or "").strip()
                return {"full_text": text, "snippet": text[:250].replace("\n", " ")}
        except Exception:
            pass

        return {
            "full_text": "Response generated in ChatGPT window.",
            "snippet": "Response generated in ChatGPT window.",
        }

    @classmethod
    async def get_conversation_history(cls, page: Page, limit: int = 6) -> List[Dict[str, str]]:
        """Extract recent turns from the active ChatGPT conversation."""
        turns: List[Dict[str, str]] = []
        try:
            # Look for conversation turns
            user_msgs = page.locator("div[data-message-author-role='user']")
            asst_msgs = page.locator("div[data-message-author-role='assistant']")

            u_count = await user_msgs.count()
            a_count = await asst_msgs.count()

            max_items = max(u_count, a_count)
            start_idx = max(0, max_items - limit)

            for i in range(start_idx, max_items):
                if i < u_count:
                    u_text = (await user_msgs.nth(i).inner_text() or "").strip()
                    if u_text:
                        turns.append({"role": "user", "text": u_text})
                if i < a_count:
                    a_text = (await asst_msgs.nth(i).inner_text() or "").strip()
                    if a_text:
                        turns.append({"role": "assistant", "text": a_text})
        except Exception as e:
            logger.warning(f"Could not extract conversation history: {e}")

        return turns
