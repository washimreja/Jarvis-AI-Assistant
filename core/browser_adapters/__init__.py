"""Browser adapters package for site-specific automation."""
from core.browser_adapters.chatgpt_adapter import ChatGPTAdapter, is_chatgpt_url

__all__ = ["ChatGPTAdapter", "is_chatgpt_url"]
