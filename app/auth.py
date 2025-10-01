# app/auth.py
import hmac, hashlib, urllib.parse
from typing import Optional
from fastapi import Header, HTTPException, Request
from .config import settings  # settings.BOT_TOKEN

def _parse_init_data(raw: str) -> dict:
    # initData приходит как query-string; parse_qsl сам сделает percent-decode
    pairs = urllib.parse.parse_qsl(raw, keep_blank_values=True, strict_parsing=False)
    return {k: v for k, v in pairs}

def _calc_hash(data: dict, bot_token: str) -> str:
    # data_check_string: key=value\n (отсортированные ключи, кроме "hash")
    lines = [f"{k}={data[k]}" for k in sorted(data) if k != "hash"]
    check = "\n".join(lines).encode()
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, check, hashlib.sha256).hexdigest()

def validate_init_data(raw: str, bot_token: str) -> bool:
    if not raw or "hash=" not in raw:
        return False
    data = _parse_init_data(raw)
    rec = data.get("hash", "")
    calc = _calc_hash(data, bot_token)
    return hmac.compare_digest(calc.lower(), rec.lower())

async def require_telegram(
    request: Request,
    x1: Optional[str] = Header(None, alias="X-Telegram-InitData"),
    x2: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),  # на всякий случай
):
    # если BOT_TOKEN пустой — пропускаем (удобно для теста из браузера)
    if not settings.BOT_TOKEN:
        return True

    raw = x1 or x2
    if not raw:
        # fallback: возьмём из тела, если фронт положил туда
        try:
            body = await request.json()
            if isinstance(body, dict):
                raw = body.get("telegram_init_data", "")
        except Exception:
            raw = ""

    if not validate_init_data(raw, settings.BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
