#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/segments"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Create Segment =="
CREATE=$(curl -sS -X POST "$API/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d '{
  "name": "High Value Users",
  "description": "Users with LTV > 1000",
  "rule_config": {"operator":"AND","conditions":[{"field":"ltv","operator":">","value":1000}]}
}')
echo "$CREATE" | jq .
SEG_ID=$(echo "$CREATE" | jq -r '.pid // empty')

echo "== List Segments =="
SEGS=$(curl -sS "$API/" "${AUTH_HDR[@]}")
echo "$SEGS" | jq .
[ -z "$SEG_ID" ] && SEG_ID=$(echo "$SEGS" | jq -r '.[0].pid // empty')

if [ -n "$SEG_ID" ]; then
  echo "== Get Segment =="
  curl -sS "$API/$SEG_ID/" "${AUTH_HDR[@]}" | jq .
  echo "== Update Segment =="
  curl -sS -X PUT "$API/$SEG_ID/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d '{"description":"Updated"}' | jq .
fi 