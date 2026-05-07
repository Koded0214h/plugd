#!/bin/bash

set -u

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_API_URL="${BASE_URL}/api/users"

TEST_EMAIL="${TEST_EMAIL:-${EMAIL_HOST_USER:-}}"
TEST_FIRST_NAME="${TEST_FIRST_NAME:-OAuth}"
TEST_LAST_NAME="${TEST_LAST_NAME:-Mailer}"
TEST_PASSWORD="${TEST_PASSWORD:-TestPass123!}"
TEST_ROLE="${TEST_ROLE:-customer}"

GOOGLE_ID_TOKEN="${GOOGLE_ID_TOKEN:-}"
GOOGLE_ROLE="${GOOGLE_ROLE:-customer}"

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok() { echo -e "${GREEN}PASS${NC}: $1"; ((PASS++)); }
fail() { echo -e "${RED}FAIL${NC}: $1"; [ -n "${2:-}" ] && echo "  $2"; ((FAIL++)); }
section() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

http() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  local token="${4:-}"

  local args=(-s -w "\n__STATUS__%{http_code}" -X "$method" "$url" -H "Content-Type: application/json" -H "Accept: application/json")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  [ -n "$data" ] && args+=(-d "$data")

  curl "${args[@]}"
}

parse_response() {
  RAW_BODY="$1"
  BODY="$(echo "$RAW_BODY" | sed '$d')"
  STATUS="$(echo "$RAW_BODY" | tail -n1 | sed 's/__STATUS__//')"
}

json_get() {
  local key="$1"
  echo "$BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$key', ''))" 2>/dev/null
}

section "1. Registration flow"
if [ -z "$TEST_EMAIL" ]; then
  echo -e "${RED}FAIL${NC}: TEST_EMAIL is required. Set TEST_EMAIL to a real inbox, or export EMAIL_HOST_USER in your shell first."
  exit 1
fi

REGISTER_PAYLOAD=$(python3 - <<PY
import json
print(json.dumps({
    "email": "${TEST_EMAIL}",
    "first_name": "${TEST_FIRST_NAME}",
    "last_name": "${TEST_LAST_NAME}",
    "role": "${TEST_ROLE}",
    "password": "${TEST_PASSWORD}",
    "password2": "${TEST_PASSWORD}",
}))
PY
)

parse_response "$(http POST "${USER_API_URL}/auth/register/" "$REGISTER_PAYLOAD")"
if [ "$STATUS" = "201" ]; then
  ok "Registration returned HTTP 201"
  ACCESS_TOKEN="$(json_get access)"
  REFRESH_TOKEN="$(json_get refresh)"
  [ -n "$ACCESS_TOKEN" ] && ok "Registration returned access token" || fail "Registration did not return access token" "$BODY"
  [ -n "$REFRESH_TOKEN" ] && ok "Registration returned refresh token" || fail "Registration did not return refresh token" "$BODY"
  echo "  This request also exercises the onboarding email hook."
else
  fail "Registration failed" "$BODY"
fi

section "2. Login after registration"
LOGIN_PAYLOAD=$(python3 - <<PY
import json
print(json.dumps({
    "email": "${TEST_EMAIL}",
    "password": "${TEST_PASSWORD}",
}))
PY
)

parse_response "$(http POST "${USER_API_URL}/auth/login/" "$LOGIN_PAYLOAD")"
if [ "$STATUS" = "200" ]; then
  ok "Login returned HTTP 200"
  LOGIN_ACCESS_TOKEN="$(json_get access)"
  [ -n "$LOGIN_ACCESS_TOKEN" ] && ok "Login returned access token" || fail "Login did not return access token" "$BODY"
else
  fail "Login failed" "$BODY"
fi

section "3. Authenticated profile check"
if [ -n "${LOGIN_ACCESS_TOKEN:-}" ]; then
  parse_response "$(http GET "${USER_API_URL}/profile/" "" "$LOGIN_ACCESS_TOKEN")"
  if [ "$STATUS" = "200" ]; then
    ok "Profile endpoint accepted JWT"
  else
    fail "Profile endpoint rejected JWT" "$BODY"
  fi
else
  fail "Skipping profile check because login token is missing"
fi

section "4. Google OAuth flow"
if [ -z "$GOOGLE_ID_TOKEN" ]; then
  fail "GOOGLE_ID_TOKEN is required to test /auth/google/" "Set GOOGLE_ID_TOKEN to a valid Google ID token from the frontend sign-in flow."
else
  GOOGLE_PAYLOAD=$(python3 - <<PY
import json
print(json.dumps({
    "id_token": "${GOOGLE_ID_TOKEN}",
    "role": "${GOOGLE_ROLE}",
}))
PY
)

  parse_response "$(http POST "${USER_API_URL}/auth/google/" "$GOOGLE_PAYLOAD")"
  if [ "$STATUS" = "200" ]; then
    ok "Google OAuth returned HTTP 200"
    GOOGLE_ACCESS_TOKEN="$(json_get access)"
    GOOGLE_REFRESH_TOKEN="$(json_get refresh)"
    [ -n "$GOOGLE_ACCESS_TOKEN" ] && ok "Google OAuth returned access token" || fail "Google OAuth did not return access token" "$BODY"
    [ -n "$GOOGLE_REFRESH_TOKEN" ] && ok "Google OAuth returned refresh token" || fail "Google OAuth did not return refresh token" "$BODY"
    echo "  This request also exercises the Google sign-up onboarding email hook for new users."
  else
    fail "Google OAuth failed" "$BODY"
  fi
fi

section "5. Summary"
echo "Passed: $PASS"
echo "Failed: $FAIL"

if [ "$FAIL" -eq 0 ]; then
  echo "All OAuth and onboarding-mail checks passed."
  exit 0
else
  exit 1
fi
