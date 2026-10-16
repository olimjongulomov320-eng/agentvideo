# TELEGRAM_SETUP.md — Telegram Bot Setup

This document covers creating the bot, finding numeric user IDs, and restricting access to exactly the two intended users.

## 1. Create a bot with @BotFather

1. Open Telegram and message `@BotFather`.
2. Send `/start`, then `/newbot`.
3. Choose a display name (e.g. `Law Firm Agent`).
4. Choose a unique username ending in `bot` (e.g. `gsplaw_agent_bot`).
5. Copy the **API token** shown (format `1234567890:ABCDEF...`). This is `TELEGRAM_BOT_TOKEN`.

Keep the token secret. Never commit `.env` or paste the token in issues/docs.

## 2. Get your numeric user ID

The bot authorises **numeric** user IDs only (never usernames).

Options:
- Message `@userinfobot` — replies with your numeric `id` (e.g. `123456789`).
- Message `@getidsbot` — shows your user id.
- Alternatively, run the bot in debug mode and message it while logged in as that user (health/auth logs show the numeric id).

You need **exactly two** authorised users: typically **you** and **your father** (as requested).

## 3. Configure `.env`

Copy the template and fill values:
```sh
cd "/Users/olimjongulomov/Desktop/Projects/AI-Bots/AI AGENT FOR MY FATHER(new)"
cp .env.example .env
```

Edit `.env` (never commit it):
```env
# Required
TELEGRAM_BOT_TOKEN=000000000:REPLACE_WITH_YOUR_REAL_TOKEN

# Restrict access to EXACTLY two configured users (you and your father)
# Use numeric IDs, comma-separated. Do not add extra spaces.
TELEGRAM_ALLOWED_USER_IDS=111111111,222222222

# Optional (defaults are safe)
OUTPUT_DIR=./output
MAX_CONCURRENT_JOBS=1
MAX_UPLOAD_MB=49
APPROVAL_TIMEOUT_SEC=900
LOG_LEVEL=INFO
FAST_RENDER=false
AGENT_NO_RENDER=0
OPENCODE_ENABLED=false
```

Notes:
- `TELEGRAM_ALLOWED_USER_IDS` is a comma-separated list of integers. The bot checks `cfg.is_authorized(uid)` for every interaction (commands, text, document, callback). Unauthorised users receive `⛔ Not authorised. This bot serves a fixed list of users only.` and no job is created.
- `FAST_RENDER=true` lowers resolution to 960×540 @24fps (useful for smoke tests); leave `false` for deliverables.
- `AGENT_NO_RENDER=1` disables rendering entirely (research/script/storyboard only) — equivalent to `--no-render` in the CLI.
- The bot registers the token as a secret at startup and `security.redact` masks it in logs/messages.

## 4. Test authorisation locally

1. Set `.env` with your two numeric IDs.
2. Run the health check:
```sh
python3 -m agent_system health
```
It should report `token_set: true` and `allowed_user_count: 2`.

3. Start the bot (will poll Telegram; stop with Ctrl+C):
```sh
python3 -m agent_system serve
```
In a separate Telegram chat with the bot:
- Send `/start` as an authorised user → should see "✅ Authorised..." and help text.
- Send `/start` from an unauthorised account → rejected (no job created). The server logs will also show `rejected unauthorized interaction`.

## 5. Restrictions & hardening

- The allow-list is the **only** access control. Do not rely on usernames, chats, or groups.
- To change the allowed set, edit `.env` and restart `serve`.
- Keep `.env` out of version control (`.gitignore` should exclude it). Use a secrets manager on VPS (not plain text if shared).
- Never send the token to anyone. If exposed, revoke and regenerate via @BotFather (`/revoke`/new token).
- Large files: if a video exceeds `MAX_UPLOAD_MB`, delivery falls back to the local filesystem path (not re-uploaded). That’s intentional to avoid API limits.
- The bot never bypasses Telegram's own access controls and never makes outbound requests beyond Telegram Bot API + normal HTTP fetches for research (when fetcher is used).