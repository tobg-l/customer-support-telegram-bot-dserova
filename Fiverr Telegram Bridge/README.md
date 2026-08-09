# Fiverr → Telegram Bridge

Polls Gmail every 60s for unread Fiverr notification emails, forwards each one to
your personal Telegram chat (sender, subject, body, and an optional AI-suggested
reply), and turns any Telegram reply-to-message into a threaded Gmail reply so it
lands back in the original Fiverr conversation.

## 1. Get a Gmail App Password

Regular Gmail passwords don't work with IMAP/SMTP if 2-Step Verification is on
(and Google requires 2-Step Verification to even generate an App Password).

1. Turn on 2-Step Verification: https://myaccount.google.com/security → "2-Step Verification"
2. Go to https://myaccount.google.com/apppasswords
3. Create an app password (name it e.g. "fiverr-bridge"), copy the 16-character code
4. Put it in `.env` as `GMAIL_APP_PASSWORD` (spaces in the code are fine)

## 2. Create the Telegram bot

1. Open Telegram, message **@BotFather**
2. Send `/newbot`, follow the prompts, copy the token it gives you → `TELEGRAM_BOT_TOKEN`
3. Send your new bot at least one message (anything) so it can message you back
4. Get your chat ID: message **@userinfobot** (or **@RawDataBot**) and it will reply
   with your numeric chat id → `TELEGRAM_CHAT_ID`

## 3. Configure

```bash
cp .env.example .env
```

Fill in `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

`OPENAI_API_KEY` is optional — leave it blank to get plain notifications with no
suggested reply, or set it to enable the "💡 Suggested reply" section (uses your
7 reply templates baked into `app/suggestions.py` as reference examples).

## 4. Run locally (test first)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Send yourself a test email that contains "Fiverr" in the subject/sender and
confirm it shows up in Telegram. Reply to that Telegram message and confirm you
get "✅ Sent back to Fiverr via email."

## 5. Deploy to a VPS (always-on)

```bash
# on the VPS
mkdir -p /opt/fiverr-bridge
# copy the project there (scp/rsync/git clone), then:
cd /opt/fiverr-bridge
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill it in
```

Install as a systemd service:

```bash
cp fiverr-bridge.service /etc/systemd/system/fiverr-bridge.service
systemctl daemon-reload
systemctl enable --now fiverr-bridge
systemctl status fiverr-bridge
```

Logs: `tail -f /opt/fiverr-bridge/bridge.log`

To update after code changes: `systemctl restart fiverr-bridge`

## How it works

- **Dedup**: each forwarded email's `Message-ID` is recorded in `state.json` so
  restarts never re-forward the same email.
- **Threading**: replies are sent with `In-Reply-To`/`References` headers pointing
  at the original email, and to whatever address the original's `Reply-To` (or
  `From`) header specified — the same mechanism Fiverr's own email notifications
  rely on to route a reply back into the platform conversation.
- **Reply detection**: you must reply-to (long-press → Reply, or swipe-to-reply)
  the bot's Telegram message, not send a new message — that's how the bridge
  finds which email thread to reply to.
- **Errors**: any failure in a poll cycle (Gmail down, Telegram down, OpenAI down)
  is logged and the loop continues on the next 60s cycle rather than crashing.

## Known limitations

- Only matches emails where the sender or subject contains "fiverr" (case-insensitive).
- Assumes plain Gmail IMAP/SMTP access (App Password), not OAuth.
- The AI suggestion is only as good as the reference templates in
  `app/suggestions.py` — edit `REPLY_TEMPLATES` there if your standard replies change.
