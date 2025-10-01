import httpx
from .config import settings

API_BASE = "https://api.telegram.org"

async def forward_transfer_message(text: str) -> None:
    """Send a message with the transfer summary to the second bot/chat."""
    if not settings.FORWARD_BOT_TOKEN or not settings.FORWARD_CHAT_ID:
        return
    url = f"{API_BASE}/bot{settings.FORWARD_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.FORWARD_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)
