#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/users"
HDR_CT='Content-Type: application/json'

echo "== Create User =="
BODY1=$(cat <<JSON
{
  "user_id": "$EXTERNAL_USER_ID",
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "user_profile": {"country": "US", "ltv": 1200}
}
JSON
)
echo "$BODY1" > tmp_user1.json
curl -sS -X POST "$API/create-user/" -H "$HDR_CT" -d @tmp_user1.json | jq .

echo "== Update User Profile =="
BODY2=$(cat <<JSON
{
  "user_id": "$EXTERNAL_USER_ID",
  "organisation_id": "$ORG_ID",
  "app_id": "$APP_ID",
  "user_profile": {"country": "US", "ltv": 1300}
}
JSON
)
echo "$BODY2" > tmp_user2.json
curl -sS -X POST "$API/update-user-profile/" -H "$HDR_CT" -d @tmp_user2.json | jq .

rm -f tmp_user1.json tmp_user2.json 