#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

EXPS_API="$BASE_URL/api/v1/experiences"
PERS_API="$BASE_URL/api/v1/personalisations"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Discover Experience and Features =="
EXPS=$(curl -sS "$EXPS_API/" "${AUTH_HDR[@]}")
echo "$EXPS" | jq .
EXP_ID=$(echo "$EXPS" | jq -r '.[0].pid // empty')

if [ -z "$EXP_ID" ]; then
  echo "No experiences available; listing personalisations only." >&2
else
  # Fetch experience to find a feature id
  EXP=$(curl -sS "$EXPS_API/$EXP_ID/" "${AUTH_HDR[@]}")
  echo "$EXP" | jq .
  EXP_FEATURE_ID=$(echo "$EXP" | jq -r '.features[0].pid // empty')

  echo "== Create Personalisation (may fail if validation fails) =="
  PAYLOAD=$(cat <<JSON
{
  "name": "Promo 10%",
  "description": "Offer 10% discount",
  "experience_id": "$EXP_ID",
  "priority": 1,
  "rule_config": {"conditions":[{"field":"country","operator":"==","value":"US"}],"operator":"AND"},
  "rollout_percentage": 100,
  "selected_metrics": [],
  "experience_variants": [
    { "target_percentage": 100, "experience_variant": {"name":"Variant A","description":"Primary","is_default": false, "feature_variants": [ {"experience_feature_id": "$EXP_FEATURE_ID", "name":"Blue Button","config":{"color":"#00F"}} ] } }
  ]
}
JSON
)
  echo "$PAYLOAD" > tmp_personalisation.json
  curl -sS -X POST "$PERS_API/create-personalisation/" -H "$HDR_CT" "${AUTH_HDR[@]}" -d @tmp_personalisation.json | jq . || true
  rm -f tmp_personalisation.json
fi

echo "== List Personalisations =="
curl -sS "$PERS_API/" "${AUTH_HDR[@]}" | jq .

if [ -n "${EXP_ID:-}" ]; then
  echo "== List Personalised Experiences for Experience =="
  curl -sS "$PERS_API/personalised-experiences/$EXP_ID/" "${AUTH_HDR[@]}" | jq .
fi 