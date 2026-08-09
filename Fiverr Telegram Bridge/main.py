"""Fiverr -> Telegram bridge.

Polls Gmail for unread Fiverr notification emails, forwards each one to a
personal Telegram chat (with an optional AI-suggested reply), and sends any
Telegram reply-to-message back to Gmail as a threaded reply so it lands back
in the original Fiverr conversation.

Run: python main.py  (requires a configured .env - see README.md)
"""
import asyncio
import datetime
import logging

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from app import config, gmail_client, state, suggestions, telegram_client

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("fiverr-bridge")


async def poll_gmail_job(context: ContextTypes.DEFAULT_TYPE):
    """Runs every POLL_INTERVAL_SECONDS. Blocking IMAP/SMTP/OpenAI calls are
    offloaded to a worker thread via asyncio.to_thread so the bot keeps
    handling Telegram updates (i.e. your replies) without stalling."""
    try:
        st = state.load()
        imap = await asyncio.to_thread(gmail_client.connect_imap)
        try:
            emails = await asyncio.to_thread(gmail_client.fetch_unread_fiverr_emails, imap)

            for email_data in emails:
                message_id = email_data["message_id"] or f"uid:{email_data['uid']}"
                if state.already_forwarded(st, message_id):
                    continue

                suggestion = await asyncio.to_thread(
                    suggestions.get_suggestion, email_data["subject"], email_data["body"]
                )

                telegram_message_ids = await telegram_client.send_notification(
                    context.bot,
                    config.TELEGRAM_CHAT_ID,
                    email_data["from_name"],
                    email_data["from_email"],
                    email_data["subject"],
                    email_data["body"],
                    suggestion,
                )

                state.record_forwarded(
                    st,
                    message_id,
                    {
                        "telegram_message_ids": telegram_message_ids,
                        "subject": email_data["subject"],
                        "from_email": email_data["from_email"],
                        "from_name": email_data["from_name"],
                        "reply_to_email": email_data["reply_to_email"],
                        "message_id": email_data["message_id"],
                        "references": email_data["references"],
                        "forwarded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    },
                )

                await asyncio.to_thread(gmail_client.mark_as_read, imap, email_data["uid"])
                log.info("Forwarded Fiverr email '%s' to Telegram", email_data["subject"])
        finally:
            await asyncio.to_thread(_safe_logout, imap)
    except Exception:
        log.exception("Gmail poll failed - will retry on next cycle")


def _safe_logout(imap):
    try:
        imap.logout()
    except Exception:
        pass


async def handle_telegram_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.reply_to_message:
        return
    if update.effective_chat.id != config.TELEGRAM_CHAT_ID:
        return

    replied_to_id = message.reply_to_message.message_id
    st = state.load()
    email_message_id, record = state.find_by_telegram_message_id(st, replied_to_id)

    if record is None:
        await message.reply_text("Couldn't find the original email for this message.")
        return

    try:
        await asyncio.to_thread(gmail_client.send_reply, record, message.text or "")
    except Exception:
        log.exception("Failed to send Gmail reply")
        await message.reply_text("⚠️ Failed to send this as a Gmail reply - check the logs.")
        return

    await message.reply_text("✅ Sent back to Fiverr via email.")
    log.info("Sent Telegram reply back to Gmail thread for '%s'", record.get("subject"))


def main():
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(
        MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, handle_telegram_reply)
    )
    application.job_queue.run_repeating(
        poll_gmail_job, interval=config.POLL_INTERVAL_SECONDS, first=5
    )

    log.info("Fiverr <-> Telegram bridge starting (polling every %ss)", config.POLL_INTERVAL_SECONDS)
    application.run_polling()


if __name__ == "__main__":
    main()
