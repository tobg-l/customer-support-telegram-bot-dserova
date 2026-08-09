import os
from dotenv import load_dotenv

load_dotenv()


def _require(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required .env variable: {name}")
    return value


GMAIL_ADDRESS = _require("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = _require("GMAIL_APP_PASSWORD")
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(_require("TELEGRAM_CHAT_ID"))

# Optional - suggestion engine runs in "disabled" mode without this.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

BODY_TRUNCATE_CHARS = 1000
