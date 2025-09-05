#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && source .env; set +a

API="$BASE_URL/api/v1/invitations"
HDR_CT='Content-Type: application/json'
AUTH_HDR=( -H "Authorization: Bearer $ACCESS_TOKEN" )

echo "== Send Invitation =="
INVITE=$(curl -sS -X POST "$API/invite" -H "$HDR_CT" "${AUTH_HDR[@]}" -d "{\"email\":\"$INVITEE_EMAIL\",\"role\":\"ADMIN\"}")
echo "$INVITE" | jq .
INV_ID=$(echo "$INVITE" | jq -r '.id // empty')

echo "== List Invitations =="
LIST=$(curl -sS "$API/invitations" "${AUTH_HDR[@]}")
echo "$LIST" | jq .
[ -z "$INV_ID" ] && INV_ID=$(echo "$LIST" | jq -r '.[0].id // empty')

if [ -n "$INV_ID" ]; then
  echo "== Cancel Invitation =="
  curl -sS -X DELETE "$API/invitations/$INV_ID" "${AUTH_HDR[@]}" | jq .
fi

echo "== Validate Invitation Token (if known) =="
# Requires a token value; leaving as example
# curl -sS "$API/validate-invite/<token>" | jq . || true 