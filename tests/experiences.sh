#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/experiences"
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== List Experiences =="
EXPS=$(curl -sS "$API/" "${AUTH_HDR[@]}")
echo "$EXPS" | jq .
EXP_ID=$(echo "$EXPS" | jq -r '.[0].pid // empty')

if [ -n "$EXP_ID" ]; then
  echo "== Get Experience =="
  curl -sS "$API/$EXP_ID/" "${AUTH_HDR[@]}" | jq .
  echo "== Get Experience Features =="
  curl -sS "$API/$EXP_ID/features/" "${AUTH_HDR[@]}" | jq .
fi 