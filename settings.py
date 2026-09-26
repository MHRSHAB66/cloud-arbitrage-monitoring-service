# settings.py — PAIRS support + backward compatibility
import os
import logging
from dotenv import load_dotenv

load_dotenv()

def _norm_symbol(s: str) -> str:
    if not s:
        return "BTCUSDT"
    return s.strip().upper()

# --- Backward compat: if PAIRS unset, fall back to single SYMBOL
SYMBOL = _norm_symbol(os.getenv("SYMBOL", "BTCUSDT"))

def _parse_pairs(val: str | None) -> list[str]:
    if not val:
        return [SYMBOL]
    parts = [p.strip().upper() for p in val.split(",") if p.strip()]
    return parts or [SYMBOL]

PAIRS: list[str] = _parse_pairs(os.getenv("PAIRS"))

# --- Threshold (%)
try:
    THRESHOLD_PCT = float(os.getenv("THRESHOLD_PCT", "0.5"))
except Exception:
    THRESHOLD_PCT = 0.5
if THRESHOLD_PCT < 0:
    raise ValueError("THRESHOLD_PCT must be >= 0")

# --- Polling (sec)
try:
    POLL_SEC = int(os.getenv("POLL_SEC", "5"))
except Exception:
    POLL_SEC = 5
if POLL_SEC < 1:
    POLL_SEC = 1

# --- Optional API keys
WALLEX_KEY = os.getenv("WALLEX_KEY", "") or ""
NOBITEX_KEY = os.getenv("NOBITEX_KEY", "") or ""

# --- Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# --- Notifier
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Nobitex fallback
NOBITEX_FALLBACK_ENABLED = os.getenv("NOBITEX_FALLBACK_ENABLED", "false").lower() == "true"
NOBITEX_IP = os.getenv("NOBITEX_IP", "185.143.233.35")

# --- HTTP
HTTP_TIMEOUT_SEC = float(os.getenv("HTTP_TIMEOUT_SEC", "10"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))

# --- Worker
ENABLE_WORKER = os.getenv("ENABLE_WORKER", "true").lower() == "true"

# --- Base URLs
WALLEX_BASE_URL = os.getenv("WALLEX_BASE_URL", "https://api.wallex.ir")
NOBITEX_BASE_URL = os.getenv("NOBITEX_BASE_URL", "https://apiv2.nobitex.ir")

__all__ = [
    "SYMBOL", "PAIRS", "THRESHOLD_PCT", "POLL_SEC",
    "WALLEX_KEY", "NOBITEX_KEY", "LOG_LEVEL",
    "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID",
    "NOBITEX_FALLBACK_ENABLED", "NOBITEX_IP",
    "HTTP_TIMEOUT_SEC", "HTTP_RETRIES",
    "ENABLE_WORKER",
    "WALLEX_BASE_URL", "NOBITEX_BASE_URL",
]
