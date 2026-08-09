"""Local JSON-backed state: which emails we've already forwarded, and how to
map a Telegram message back to the original email thread when the user replies."""
import json
import os
import threading

from . import config

_lock = threading.Lock()


def _empty():
    return {"forwarded": {}}


def _migrate(state):
    """Upgrades records from the older single "telegram_message_id" field to
    the current "telegram_message_ids" list, so replies to messages forwarded
    before that change still resolve instead of silently failing lookup."""
    changed = False
    for record in state.get("forwarded", {}).values():
        if "telegram_message_ids" not in record and "telegram_message_id" in record:
            record["telegram_message_ids"] = [record.pop("telegram_message_id")]
            changed = True
    if changed:
        save(state)
    return state


def load():
    if not os.path.exists(config.STATE_FILE):
        return _empty()
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            return _empty()
    return _migrate(state)


def save(state):
    tmp_path = config.STATE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, config.STATE_FILE)


def already_forwarded(state, message_id):
    return message_id in state["forwarded"]


def record_forwarded(state, message_id, record):
    """record: dict with telegram_message_ids (list - notification, and
    optionally the separate suggested-reply message), subject, from_email,
    from_name, reply_to_email, orig_message_id, references (str), forwarded_at (iso str)."""
    with _lock:
        state["forwarded"][message_id] = record
        save(state)


def find_by_telegram_message_id(state, telegram_message_id):
    """Replying to EITHER the original notification or its suggested-reply
    message (if one was sent) should trigger the Gmail reply."""
    for email_message_id, record in state["forwarded"].items():
        if telegram_message_id in record.get("telegram_message_ids", []):
            return email_message_id, record
    return None, None
