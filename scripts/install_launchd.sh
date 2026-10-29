#!/bin/zsh
# Install the bot as a macOS launchd agent: starts at login, restarts on crash.
#   scripts/install_launchd.sh          install + start
#   scripts/install_launchd.sh remove   stop + uninstall
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="uz.gsp.lawfirm-bot"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$(command -v python3)"

if [[ "$1" == "remove" ]]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed $LABEL"
  exit 0
fi

mkdir -p "$ROOT/output/logs" "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$PY</string><string>-m</string><string>agent_system</string><string>serve</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>StandardOutPath</key><string>$ROOT/output/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/output/logs/launchd.err.log</string>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "installed and started $LABEL (logs: $ROOT/output/logs)"
