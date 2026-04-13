# Template Telegram Bot

Minimal aiogram 3.x bot template.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export BOT_TOKEN=your_token
python bot/main.py
```

## Notes
- Configure env in `.env` based on `.env.example`.
- Incoming messages are routed through `swarmctl run` with `ZeroClaw` runtime defaults.
- For native binary mode set `ZEROCLAW_USE_NATIVE_BIN=true` and point `ZEROCLAW_BIN` to the installed binary.
- Set `TG_ALLOWED_CHAT_IDS` to restrict the bot to your own chat or admin chats.
- `/health` reports runtime profile and queue counters.
- Long replies are chunked automatically and simple per-chat rate limiting is enabled.
- `/queue` (alias `/jobs`), `/drain`, `/pause_background <minutes>`, `/resume_background`, `/mode` are admin-oriented commands.
- Approval and governance commands: `/approvals`, `/approve <ticket_id>`, `/deny <ticket_id>`, `/stop [minutes]`, `/resume`, `/goals`, `/budget`, `/incident`.
- Set `TG_ADMIN_CHAT_IDS` explicitly before enabling admin commands.
- For webhook mode set `TG_BOT_MODE=webhook` and fill `TG_WEBHOOK_URL`.
- For webhook validation use:
  - `python repos/packages/agent-os/scripts/swarmctl.py telegram-readiness --mode webhook`
