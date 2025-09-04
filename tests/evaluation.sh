#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/user-experience"
HDR_CT='Content-Type: application/json'

echo "== Get Experience (single) =="
BODY1=$(cat <<JSON
{
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "user_id": "$EXTERNAL_USER_ID",
  "experience_name": "$EVAL_EXPERIENCE_NAME",
  "payload": {"country":"US"}
}
JSON
)
echo "$BODY1" > tmp_eval1.json
curl -sS -X POST "$API/get-experience/" -H "$HDR_CT" -d @tmp_eval1.json | jq . || true

echo "== Get Experiences (selected) =="
BODY2=$(cat <<JSON
{
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "user_id": "$EXTERNAL_USER_ID",
  "experience_names": ["$EVAL_EXPERIENCE_NAME"],
  "payload": {"country":"US"}
}
JSON
)
echo "$BODY2" > tmp_eval2.json
curl -sS -X POST "$API/get-experiences/" -H "$HDR_CT" -d @tmp_eval2.json | jq . || true

echo "== Get All Experiences =="
BODY3=$(cat <<JSON
{
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "user_id": "$EXTERNAL_USER_ID",
  "payload": {"country":"US"}
}
JSON
)
echo "$BODY3" > tmp_eval3.json
curl -sS -X POST "$API/get-all-experiences/" -H "$HDR_CT" -d @tmp_eval3.json | jq . || true

rm -f tmp_eval1.json tmp_eval2.json tmp_eval3.json 