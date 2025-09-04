#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/metrics"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Compute Metric =="
curl -sS -X POST "$API/compute/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d '{
  "type": "count",
  "config": {"event":"login","time_range":{"start":"2024-01-01","end":"2024-01-31"}}
}' | jq .

echo "== List Events Schema =="
curl -sS "$API/events-schema/" "${AUTH_HDR[@]}" | jq .

echo "== List User Profile Keys =="
curl -sS "$API/user-profile-keys/" "${AUTH_HDR[@]}" | jq .

echo "== Create Metric =="
CREATE=$(curl -sS -X POST "$API/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d '{
  "name":"Weekly Active Users","description":"WAU","type":"count","config":{"event":"login"}
}')
echo "$CREATE" | jq .
METRIC_ID=$(echo "$CREATE" | jq -r '.pid // empty')

echo "== List Metrics =="
LIST=$(curl -sS "$API/" "${AUTH_HDR[@]}")
echo "$LIST" | jq .
[ -z "$METRIC_ID" ] && METRIC_ID=$(echo "$LIST" | jq -r '.[0].pid // empty')

if [ -n "$METRIC_ID" ]; then
  echo "== Get Metric =="
  curl -sS "$API/$METRIC_ID/" "${AUTH_HDR[@]}" | jq .
  echo "== Update Metric =="
  curl -sS -X PUT "$API/$METRIC_ID/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d '{
    "name":"WAU","description":"Weekly AU","type":"count","config":{"event":"login"}
  }' | jq .
fi 