#!/bin/bash
cd /opt/thorondor
source venv/bin/activate
nohup python3 telegram_bot.py > /var/log/thorondor/bot.log 2>&1 &
echo "Bot started. Logs: /var/log/thorondor/bot.log"