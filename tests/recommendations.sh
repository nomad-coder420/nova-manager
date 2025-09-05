#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/recommendations"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Get AI Recommendations =="
BODY=$(cat <<JSON
{ "user_prompt": "$RECO_PROMPT" }
JSON
)
echo "$BODY" > tmp_reco.json
curl -sS -X POST "$API/get-ai-recommendations/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d @tmp_reco.json | jq . || true

echo "== List Recommendations =="
curl -sS "$API/" "${AUTH_HDR[@]}" | jq .

rm -f tmp_reco.json 