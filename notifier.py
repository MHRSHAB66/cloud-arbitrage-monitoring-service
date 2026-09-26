import os
import httpx
import asyncio

# Telegram
TG_BASE = os.getenv("TELEGRAM_BASE_URL", "https://api.telegram.org")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID", "")

# Bale
BALE_BASE = os.getenv("BALE_BASE_URL", "https://tapi.bale.ai")
BALE_TOKEN = os.getenv("BALE_TOKEN", "")
BALE_CHAT  = os.getenv("BALE_CHAT_ID", "")

# اختیاری: یک پراکسی واحد برای خروجی (اگر خالی باشد استفاده نمی‌شود)
HTTP_PROXY = os.getenv("NOTIFIER_PROXY", "")  # مثل: http://user:pass@host:port

def _api(base, token, path):
    return f"{base.rstrip('/')}/bot{token}/{path.lstrip('/')}"

async def _send(base, token, chat_id, html: str, platform: str):
    if not (token and chat_id):
        print(f"⚠️ Skipping {platform}: token or chat_id missing.")
        return False
    try:
        # httpx 0.28+: به جای proxies= از proxy= استفاده کن
        async with httpx.AsyncClient(
            timeout=10,
            http2=True,
            proxy=(HTTP_PROXY or None),   # ← این خط مشکل را حل می‌کند
            trust_env=False               # اگر نمی‌خواهی env سیستم را بخواند
        ) as cx:
            r = await cx.post(
                _api(base, token, "sendMessage"),
                data={
                    "chat_id": chat_id,
                    "text": html,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            r.raise_for_status()
            print(f"✅ Sent to {platform}")
            return True
    except Exception as e:
        print(f"❌ Error sending to {platform}: {e}")
        return False

async def send_telegram(html: str): return await _send(TG_BASE, TG_TOKEN, TG_CHAT, html, "Telegram")
async def send_bale(html: str):     return await _send(BALE_BASE, BALE_TOKEN, BALE_CHAT, html, "Bale")

async def notify(html: str):
    results = await asyncio.gather(send_telegram(html), send_bale(html), return_exceptions=True)
    return {"telegram": results[0], "bale": results[1]}
