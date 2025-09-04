#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/feature-flags"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Sync Nova Objects =="
cat > tmp_nova_objects.json <<JSON
{
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "objects": {
    "Button": {
      "type": "ui",
      "keys": {
        "text": { "type": "string", "description": "Button text", "default": "Buy" },
        "color": { "type": "string", "description": "CSS color", "default": "#000" }
      }
    }
  },
  "experiences": {
    "Homepage": { "description": "Home screen", "objects": { "Button": true } }
  }
}
JSON
curl -sS -X POST "$API/sync-nova-objects/" -H "$HDR_CT" -d @tmp_nova_objects.json | jq .

echo "== List Feature Flags =="
FLAGS=$(curl -sS "$API/" "${AUTH_HDR[@]}")
echo "$FLAGS" | jq .
FLAG_ID=$(echo "$FLAGS" | jq -r '.[0].pid // empty')

echo "== List Available Flags =="
curl -sS "$API/available/" "${AUTH_HDR[@]}" | jq .

if [ -n "$FLAG_ID" ]; then
  echo "== Get Feature Flag by ID =="
  curl -sS "$API/$FLAG_ID/" "${AUTH_HDR[@]}" | jq .
fi
rm -f tmp_nova_objects.json 