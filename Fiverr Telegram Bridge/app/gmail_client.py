"""IMAP polling + SMTP reply-sending for the Gmail account being bridged to Telegram."""
import email
import imaplib
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr

from . import config


IMAP_TIMEOUT_SECONDS = 30
SMTP_TIMEOUT_SECONDS = 30
MAX_EMAILS_PER_CYCLE = 50


def connect_imap():
    # A timeout is essential here: without one, a flaky Gmail connection can
    # hang a blocking IMAP call forever, which would freeze the whole poll
    # loop (every future cycle silently skipped, no error ever raised).
    imap = imaplib.IMAP4_SSL(config.IMAP_HOST, timeout=IMAP_TIMEOUT_SECONDS)
    imap.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
    imap.select("INBOX")
    return imap


def _decode(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _looks_like_fiverr(from_header, subject):
    haystack = f"{from_header} {subject}".lower()
    return "fiverr" in haystack


def _extract_body(msg):
    if msg.is_multipart():
        # Prefer text/plain; fall back to stripping tags from text/html.
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition:
                return part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/html" and "attachment" not in disposition:
                import re

                html = part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
                return re.sub("<[^<]+?>", " ", html)
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload is None:
            return msg.get_payload()
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def fetch_unread_fiverr_emails(imap):
    """Returns a list of dicts for unread emails that look like Fiverr notifications.

    Filters server-side (UNSEEN AND (FROM or SUBJECT contains "fiverr")) instead
    of fetching every unread message's full body - on a mailbox with a large
    unread backlog, fetching thousands of full RFC822 bodies per 60s cycle is
    slow enough to trip Gmail's IMAP rate limiting ("System Error" on FETCH).
    """
    status, data = imap.search(None, "UNSEEN", "OR", "FROM", "fiverr", "SUBJECT", "fiverr")
    if status != "OK" or not data or not data[0]:
        return []

    uids = data[0].split()
    if len(uids) > MAX_EMAILS_PER_CYCLE:
        print(
            f"[gmail] {len(uids)} matching unread emails found, processing "
            f"first {MAX_EMAILS_PER_CYCLE} this cycle, rest will follow on later cycles"
        )
        uids = uids[:MAX_EMAILS_PER_CYCLE]

    results = []
    for uid in uids:
        status, msg_data = imap.fetch(uid, "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        from_header = _decode(msg.get("From", ""))
        subject = _decode(msg.get("Subject", ""))

        if not _looks_like_fiverr(from_header, subject):
            continue

        from_name, from_email = parseaddr(from_header)
        reply_to_header = msg.get("Reply-To")
        reply_to_email = parseaddr(reply_to_header)[1] if reply_to_header else from_email

        body = _extract_body(msg).strip()
        truncated = body[: config.BODY_TRUNCATE_CHARS]
        if len(body) > config.BODY_TRUNCATE_CHARS:
            truncated += "... [truncated]"

        results.append(
            {
                "uid": uid,
                "message_id": msg.get("Message-ID", "").strip(),
                "references": msg.get("References", "").strip(),
                "from_name": from_name or from_email,
                "from_email": from_email,
                "reply_to_email": reply_to_email,
                "subject": subject,
                "body": truncated,
            }
        )
    return results


def mark_as_read(imap, uid):
    imap.store(uid, "+FLAGS", "\\Seen")


def send_reply(original, reply_text):
    """Sends reply_text as an SMTP reply threaded onto the original email."""
    msg = EmailMessage()
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = original["reply_to_email"]

    subject = original["subject"] or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    msg["Subject"] = subject

    if original.get("message_id"):
        msg["In-Reply-To"] = original["message_id"]
        references = (original.get("references") or "").strip()
        references = f"{references} {original['message_id']}".strip()
        msg["References"] = references

    msg.set_content(reply_text)

    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)
