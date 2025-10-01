# app/auth.py
import hmac, hashlib, urllib.parse
from typing import Optional
from fastapi import Header, HTTPException, Request
from .config import settings  # BOT_TOKEN

def _parse_init_data(raw: str) -> dict:
    # initData — это query-string; percent-decode делаем через parse_qsl
    pairs = urllib.parse.parse_qsl(raw, keep_blank_values=True, strict_parsing=False)
    return {k: v for k, v in pairs}

def _calc_hash(data: dict, bot_token: str) -> str:
    lines = [f"{k}={data[k]}" for k in sorted(data) if k != "hash"]
    check_string = "\n".join(lines).encode()
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, check_string, hashlib.sha256).hexdigest()

def validate_init_data(raw: str, bot_token: str) -> bool:
    if not raw or "hash=" not in raw:
        return False
    data = _parse_init_data(raw)
    recv = data.get("hash", "")
    calc = _calc_hash(data, bot_token)
    return hmac.compare_digest(calc.lower(), recv.lower())

async def require_telegram(
    request: Request,
    x1: Optional[str] = Header(None, alias="X-Telegram-InitData"),
    x2: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),  # на всякий случай
):
    raw = x1 or x2
    if not raw:
        # fallback на тело, если фронт положил initData только туда
        try:
            body = await request.json()
            if isinstance(body, dict):
                raw = body.get("telegram_init_data", "")
        except Exception:
            raw = ""
    if settings.BOT_TOKEN and not validate_init_data(raw, settings.BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
