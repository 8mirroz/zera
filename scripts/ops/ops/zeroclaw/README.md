# ZeroClaw Edge Runtime

This directory contains the minimum deployment assets for the `ZeroClaw + Zera` edge runtime.

## Files
- `.env.example`: runtime and Telegram defaults
- `docker-compose.yaml`: bot + background daemon
- `zera-telegram-bot.service`: systemd unit for the Telegram ingress
- `zeroclaw-zera.service`: systemd unit for the background daemon
- `Caddyfile`: HTTPS reverse proxy template
- `nginx.conf`: HTTP reverse proxy template

## Docker Compose
```bash
cd ops/zeroclaw
cp .env.example .env
docker compose up -d
```

## systemd
```bash
cp ops/zeroclaw/.env.example ops/zeroclaw/.env
sudo cp ops/zeroclaw/zera-telegram-bot.service /etc/systemd/system/
sudo cp ops/zeroclaw/zeroclaw-zera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zera-telegram-bot.service
sudo systemctl enable --now zeroclaw-zera.service
```

## Native ZeroClaw mode
Set:
```bash
ZEROCLAW_USE_NATIVE_BIN=true
ZEROCLAW_BIN=zeroclaw
```

Profiles in [zeroclaw_profiles.json](/Users/user/zera/configs/tooling/zeroclaw_profiles.json) already expose `native_command` templates. If the installed ZeroClaw CLI differs, edit those command arrays to match the target host.

## Recommended hardening
- Rotate any bot token that was pasted into chat, logs, or shell history.
- Set `TG_ALLOWED_CHAT_IDS` before first production start.
- Set `TG_ADMIN_CHAT_IDS` separately from the general allowlist.
- Keep `ZEROCLAW_USE_NATIVE_BIN=false` until the target host's CLI contract is verified.
- Run the background daemon as a separate service even for single-user mode.
- Prefer `TG_BOT_MODE=webhook` for production ingress once a stable HTTPS endpoint exists.

## Readiness check
```bash
python repos/packages/agent-os/scripts/swarmctl.py telegram-readiness --mode polling
python repos/packages/agent-os/scripts/swarmctl.py telegram-readiness --mode webhook
python repos/packages/agent-os/scripts/swarmctl.py budget-status
python repos/packages/agent-os/scripts/swarmctl.py approval-list
```

The check reports only `set|empty|missing` for secrets, never raw values.

## Governance commands
```bash
python repos/packages/agent-os/scripts/swarmctl.py stop-signal --scope global --minutes 30
python repos/packages/agent-os/scripts/swarmctl.py stop-clear --scope global
python repos/packages/agent-os/scripts/swarmctl.py incident-report
```

These commands provide bounded-autonomy emergency controls and operator-visible audit signals.
