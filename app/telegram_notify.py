# app/telegram_notify.py
from __future__ import annotations

import json
import urllib.parse
import httpx


def _extract_user_id_from_init_data(init_data: str) -> int | None:
    """
    init_data — это query-string от Telegram WebApp.
    В нём ключ 'user' содержит JSON-объект пользователя. Берём user.id.
    """
    if not init_data:
        return None
    try:
        pairs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        user_json = pairs.get("user")
        if not user_json:
            return None
        user = json.loads(user_json)
        uid = user.get("id")
        return int(uid) if uid is not None else None
    except Exception:
        return None


async def send_user_confirmation(bot_token: str, init_data: str, text: str) -> None:
    """
    Отправляет сообщение пользователю (chat_id = user.id из initData)
    через того же бота, чей токен передан.
    """
    user_id = _extract_user_id_from_init_data(init_data)
    if not user_id or not bot_token:
        return  # нечего отправлять

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)
    except Exception:
        # без падения — подтверждение не критично для основного потока
        pass
