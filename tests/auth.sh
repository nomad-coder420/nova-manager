#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/auth"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Register =="
curl -sS -X POST "$API/register" -H "$HDR_CT" \
  -d "{\"email\":\"$REGISTER_EMAIL\",\"password\":\"$REGISTER_PASSWORD\",\"name\":\"$REGISTER_NAME\",\"invite_token\":null,\"company\":\"Test Co\"}" | jq . || true

echo "== Login =="
LOGIN_RESP=$(curl -sS -X POST "$API/login" -H "$HDR_CT" \
  -d "{\"email\":\"$REGISTER_EMAIL\",\"password\":\"$REGISTER_PASSWORD\"}")
echo "$LOGIN_RESP" | jq .
NEW_ACCESS=$(echo "$LOGIN_RESP" | jq -r .access_token)
NEW_REFRESH=$(echo "$LOGIN_RESP" | jq -r .refresh_token)

echo "== Refresh =="
curl -sS -X POST "$API/refresh" -H "$HDR_CT" \
  -d "{\"refresh_token\":\"$NEW_REFRESH\"}" | jq .

echo "== Me =="
curl -sS "$API/me" -H "Authorization: Bearer $NEW_ACCESS" | jq .

echo "== Create App =="
CREATE_APP=$(curl -sS -X POST "$API/apps" -H "$HDR_CT" -H "Authorization: Bearer $NEW_ACCESS" \
  -d "{\"name\":\"Test App\",\"description\":\"Demo app\"}")
echo "$CREATE_APP" | jq .
NEW_APP_ID=$(echo "$CREATE_APP" | jq -r .app.id)

echo "== List Apps =="
curl -sS "$API/apps" -H "Authorization: Bearer $NEW_ACCESS" | jq .

if [ "$NEW_APP_ID" != "null" ] && [ -n "$NEW_APP_ID" ]; then
  echo "== Switch App =="
  curl -sS -X POST "$API/switch-app" -H "$HDR_CT" -H "Authorization: Bearer $NEW_ACCESS" \
    -d "{\"app_id\":\"$NEW_APP_ID\"}" | jq .
fi 