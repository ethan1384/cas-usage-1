#!/usr/bin/env bash
# Lance la démo : Slack réel si .env le configure, HubSpot remplacé par un simulateur visible
# dans le navigateur. Les données de démonstration précédentes sont effacées.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8765}"
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export MOCK_HUBSPOT=1 HUBSPOT_TOKEN=demo HUBSPOT_BASE_URL="http://127.0.0.1:$PORT/mock/hubspot"
rm -f data/decisions.csv data/outbox.jsonl
echo "Contacts HubSpot simulés : http://127.0.0.1:$PORT/mock/hubspot"
echo "Documentation du webhook : http://127.0.0.1:$PORT/docs"
exec uv run uvicorn lumio.main:app --port "$PORT"
