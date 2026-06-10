"""
Telegram notification sender.
Sends alerts when pricing changes are detected.

Setup: create a bot via @BotFather, get your chat ID via @userinfobot
then add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your .env file.
"""

import os
import logging
import httpx
from models import Change

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


def _build_message(change: Change) -> str:
    """
    Format a Telegram alert message for a detected change.
    Keeps it under Telegram's 4096-char limit.
    """
    # Truncate summary for the message
    summary = (change.summary or "")[:800]

    # Find URL from common tool names
    url_map = {
        "OpenAI": "https://openai.com/pricing",
        "Claude": "https://www.anthropic.com/pricing",
        "Gemini": "https://gemini.google/subscriptions/",
        "Perplexity": "https://www.perplexity.ai/pro",
        "Cursor": "https://www.cursor.com/pricing",
    }
    source_url = url_map.get(change.tool_name, "https://example.com")

    message = (
        f"🚨 *AI Pricing Change Detected*\n\n"
        f"*Tool:* {change.tool_name}\n"
        f"*Detected at:* {change.detected_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"*Summary:*\n{summary}\n\n"
        f"*Source:* {source_url}"
    )
    return message[:4096]  # Telegram hard limit


async def send_alert(change: Change) -> bool:
    """
    Send a Telegram message for a detected change.
    Returns True on success, False on failure (non-fatal).
    
    Uses httpx async client so it plays nicely with FastAPI's event loop.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.warning("[Notifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping alert")
        return False

    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": _build_message(change),
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"[Notifier] Alert sent for {change.tool_name}")
            return True

    except httpx.HTTPStatusError as e:
        logger.error(f"[Notifier] Telegram API error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[Notifier] Failed to send alert: {e}")
        return False


async def send_startup_message() -> bool:
    """
    Send a test/startup message to confirm Telegram is configured correctly.
    Call this on app startup to verify credentials.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        return False

    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "✅ *AI Deals Tracker started* — monitoring AI pricing pages.",
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("[Notifier] Startup message sent")
            return True
    except Exception as e:
        logger.warning(f"[Notifier] Startup message failed: {e}")
        return False
