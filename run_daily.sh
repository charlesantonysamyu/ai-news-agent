#!/bin/bash
# Wrapper for cron. Points at the project folder + venv, logs each run.
#
# Example crontab entry (runs daily at 8:00am server time):
#   0 8 * * * /path/to/ai_news_agent/run_daily.sh >> /path/to/ai_news_agent/run.log 2>&1

set -e
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=== Run started: $(date) ==="
python agent.py
echo "=== Run finished: $(date) ==="
