# VPS_DEPLOYMENT.md — Linux VPS Deployment

## 1. System requirements
- Linux (Ubuntu 22.04+ recommended)
- Python 3.9+ (3.10/3.11 also fine)
- `ffmpeg` (video encode/decode)
- `pip`, `virtualenv`/`venv`
- (Optional) `blender` if 3D required
- Outbound HTTPS for research fetches; inbound to Telegram polling port not required (uses long polling)

## 2. Install dependencies
```sh
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip ffmpeg git
# optional
# sudo snap install blender --classic  # or build from source
```

## 3. Deploy
```sh
mkdir -p ~/apps
cd ~/apps
git clone <your-repo-url> agent-lawfirm  # or copy files
cd agent-lawfirm
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install python-telegram-bot==21.6 Pillow requests
```

## 4. Configure
```sh
cp .env.example .env
chmod 600 .env  # restrict permissions
nano .env  # set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_IDS (two numeric IDs)
# optionally set FAST_RENDER, AGENT_NO_RENDER, MAX_UPLOAD_MB, LOG_LEVEL
```

Verify:
```sh
source .venv/bin/activate
python3 -m agent_system health
python3 -m agent_system styles
```

## 5. Run as a systemd service (recommended)
Create `/etc/systemd/system/lawfirm-agent.service`:
```ini
[Unit]
Description=Law Firm Research & Video Script Agent Telegram Bot
After=network.target

[Service]
User=<your-user>
WorkingDirectory=/home/<your-user>/apps/agent-lawfirm
Environment=PATH=/home/<your-user>/apps/agent-lawfirm/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/<your-user>/apps/agent-lawfirm/.venv/bin/python -m agent_system serve
Restart=always
RestartSec=5
StandardOutput=append:/home/<your-user>/apps/agent-lawfirm/output/logs/bot.log
StandardError=append:/home/<your-user>/apps/agent-lawfirm/output/logs/bot.log

[Install]
WantedBy=multi-user.target
```

Enable & start:
```sh
sudo systemctl daemon-reload
sudo systemctl enable --now lawfirm-agent
sudo systemctl status lawfirm-agent
journalctl -u lawfirm-agent -f  # follow logs
```

Stop/restart:
```sh
sudo systemctl stop lawfirm-agent
sudo systemctl restart lawfirm-agent
```

## 6. Operation & safety
- **Authorisation:** only the two numeric IDs in `TELEGRAM_ALLOWED_USER_IDS` can control the bot. Unauthorised users are rejected before job creation.
- **Secrets:** keep `.env` mode `600`. Never commit tokens. Register with @BotFather revoke if compromised.
- **Redaction:** all logs pass through `security.redact`. The bot token is masked in messages/logs.
- **Limits:** `MAX_UPLOAD_MB=49` → oversize files not uploaded via API; local path delivered. `MAX_CONCURRENT_JOBS=1` (safe). `APPROVAL_TIMEOUT_SEC=900`.
- **No-render:** set `AGENT_NO_RENDER=1` in `.env` or use `--no-render` for research-only runs.
- **Fast render:** `FAST_RENDER=true` for smoke tests.
- **Uzbek TTS:** Linux typically has no Uzbek voice; record human narration for final UZ cut.
- **Blender:** if not installed, 3D style is UNAVAILABLE (honest).
- **Backups:** back up `output/` and `output/jobs.sqlite3*` regularly (contains job state and deliverables). Jobs are versioned by job_id; avoid deleting in-progress work.
- **Firewall:** no open inbound ports needed for long-polling Telegram bot. If you later switch to webhooks, open only HTTPS.
- **Updates:** pull repo, `pip install -U` deps if needed, `systemctl restart lawfirm-agent`. Test with `python3 -m agent_system styles && python3 -m agent_system health` after update.