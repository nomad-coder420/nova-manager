#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/metrics"
HDR_CT='Content-Type: application/json'

echo "== Track Event =="
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATA=$(cat <<JSON
{
  "user_id": "$EXTERNAL_USER_ID",
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "timestamp": "$NOW",
  "event_name": "$EVENT_NAME",
  "event_data": {"amount": 19.99, "currency": "USD"}
}
JSON
)

echo "$DATA" > tmp_event.json
curl -sS -X POST "$API/track-event/" -H "$HDR_CT" -d @tmp_event.json | jq .
rm -f tmp_event.json 