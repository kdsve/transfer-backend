import hashlib, hmac, urllib.parse
from .config import settings

def verify_telegram_init_data(init_data: str) -> bool:
    """Validate Telegram WebApp initData signature.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not settings.BOT_TOKEN:
        # dev mode: allow empty or fake init_data; set BOT_TOKEN in prod
        return True
    try:
        parts = [p for p in init_data.split("&") if p]
        data = {}
        hash_recv = ""
        for p in parts:
            k, v = p.split("=", 1)
            if k == "hash":
                hash_recv = v
            else:
                data[k] = urllib.parse.unquote_plus(v)
        data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
        secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()
        calc = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(calc, hash_recv)
    except Exception:
        return False
