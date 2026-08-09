# Your Support Bot — User Guide

This is a quick guide to running your Telegram support bot day-to-day. No coding needed for
anything below — everything is managed through a Google Sheet and a few Telegram commands.

## What the bot does

Your bot answers customer questions automatically, 24/7, using the knowledge base you control.
If it can't confidently answer something, it tells the customer honestly and connects them with
you instead of guessing.

## Updating what the bot knows

Everything the bot can answer comes from your Google Sheet. To add, change, or remove an answer:

1. Open your FAQ sheet.
2. Each row is one question/answer pair with four columns:
   - **Question** — the question in plain language
   - **Answer** — what the bot should say
   - **Keywords** — optional, for your own reference when scanning the sheet
   - **Active** — `TRUE` to make it live, `FALSE` to turn it off without deleting it
3. Save the sheet — that's it, no one needs to touch any code.

Changes are picked up automatically within about 10 minutes. If you want a change to apply
immediately, send `/reload` to the bot in Telegram (see commands below).

Tip: prefer setting a row to `Active = FALSE` over deleting it if you might reuse it later.

## Order lookups (if enabled for your bot)

If your bot is also connected to an order/shipment sheet, customers can ask about their order in
plain language — e.g. "where's my order 1042" or "what's the status of ORD-1042" — and the bot
will look it up and answer using that order's details (status, tracking number, carrier, fee,
estimated delivery). It only ever shares the one order being asked about, never the full sheet,
so other customers' information is never exposed.

If a customer references an order without repeating the number (e.g. a one-word follow-up like
"and the fee?"), the bot remembers which order you were just discussing and keeps answering
about that one — including if the customer uses Telegram's reply feature to reply directly to
an earlier order message.

## When the bot hands off to you

The bot escalates to you instead of answering when:
- The customer asks to speak to a person, mentions a complaint, a refund, or wants a manager
- The bot isn't confident it has the right answer
- The customer asks the same unresolved question more than once

When that happens, the customer sees a message letting them know your team will follow up, and
you get a Telegram alert with their username and their message — so you can message them
directly to take it from there.

## Commands you can use

These only work when sent from your own Telegram account — anyone else sending them is silently
ignored.

| Command | What it does |
|---|---|
| `/status` | Bot uptime, messages handled today, escalations today |
| `/pause` | Temporarily takes the bot offline — customers are told you're back soon |
| `/resume` | Brings the bot back online |
| `/reload` | Forces an immediate refresh of your FAQ (and order sheet, if enabled) instead of waiting ~10 minutes |
| `/escalations` | Lists today's unresolved handoffs |

## A few tips

- Keep answers short and specific — the bot is instructed to keep replies concise, and shorter
  source answers make for more consistent replies.
- Write answers the way you'd want a customer to read them — the bot uses your wording closely
  rather than heavily rephrasing.
- If you notice the bot escalating something it should be able to answer, check whether that
  question is actually covered in the sheet yet.

## Questions or issues

If something isn't behaving as expected, reach out to us directly and we'll take a look.
