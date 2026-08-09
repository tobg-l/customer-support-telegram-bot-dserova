from html import escape


def build_notification_text(from_name, from_email, subject, body, has_suggestion):
    lines = [
        "📩 <b>New Fiverr message</b>",
        f"From: {escape(from_name)} &lt;{escape(from_email)}&gt;",
        f"Subject: {escape(subject)}",
        "",
        escape(body),
        "",
        "<i>Reply to this message to send your response on the thread.</i>",
    ]
    if has_suggestion:
        lines += ["", "💡 <b>Suggested reply below:</b>"]

    text = "\n".join(lines)
    # Telegram hard cap is 4096 chars; trim the body first if we're over.
    if len(text) > 4096:
        overflow = len(text) - 4096 + 20
        body_trimmed = body[: max(0, len(body) - overflow)] + "... [trimmed]"
        return build_notification_text(from_name, from_email, subject, body_trimmed, has_suggestion)
    return text


def _trim_to_limit(text):
    if len(text) > 4096:
        return text[: 4096 - 20] + "... [trimmed]"
    return text


async def send_notification(bot, chat_id, from_name, from_email, subject, body, suggestion):
    """Sends the customer message as one Telegram message, and (if a suggestion
    was generated) the suggested reply as a second, separate message right
    below it - kept as plain unformatted text so it's easy to copy/forward as-is.

    Returns a list of the sent message_id(s): [notification_id] or
    [notification_id, suggestion_id]. Replying to *either* message is treated
    as a valid trigger for sending a Gmail reply (see state.find_by_telegram_message_id).
    """
    text = build_notification_text(from_name, from_email, subject, body, bool(suggestion))
    notification = await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    message_ids = [notification.message_id]

    if suggestion:
        suggestion_message = await bot.send_message(
            chat_id=chat_id, text=_trim_to_limit(suggestion)
        )
        message_ids.append(suggestion_message.message_id)

    return message_ids
