#!/bin/bash
set -e
cd "$(dirname "$0")/.."
curl -s http://localhost:8000/health
echo ""
docker compose exec -T agenda-agent python -c "from src.scheduler import execute_daily_briefing; print('SENT=', execute_daily_briefing())"
