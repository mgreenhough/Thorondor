#!/bin/bash
# Start Thorondor Telegram bot (lightweight command-only mode)
# Usage: ./start_bot.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "Warning: venv not found at $SCRIPT_DIR/venv, using system python3"
fi

mkdir -p /var/log/thorondor 2>/dev/null || true

nohup python3 telegram_bot.py > /var/log/thorondor/bot.log 2>&1 &
echo "Bot started. PID: $!"
echo "Logs: /var/log/thorondor/bot.log"