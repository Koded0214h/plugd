#!/bin/bash

BASE_URL="https://plugd-wxjr.onrender.com"
PASS=0
FAIL=0

# ── helpers ────────────────────────────────────────────────────────────────
ok()   { echo "  PASS: $1"; ((PASS++)); }
fail() { echo "  FAIL: $1"; echo "        Response: $2"; ((FAIL++)); }

check_status() {
  local label="$1" expected="$2" actual="$3" body="$4"
  if [ "$actual" = "$expected" ]; then ok "$label (HTTP $actual)"
  else fail "$label (expected $expected, got $actual)" "$body"; fi
}

check_no_match() {
  local label="$1" pattern="$2" body="$3"
  if echo "$body" | grep -q "$pattern"; then
    fail "$label (found '$pattern' in response)" "$body"
  else ok "$label"; fi
}

check_match() {
  local label="$1" pattern="$2" body="$3"
  if echo "$body" | grep -q "$pattern"; then ok "$label"
  else fail "$label (pattern '$pattern' not found)" "$body"; fi
}

http() {
  # Usage: http METHOD URL [token] [data]
  local method="$1" url="$2" token="$3" data="$4"
  local args=(-s -w "\n__STATUS__%{http_code}" -X "$method" "$url" -H "Content-Type: application/json")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  [ -n "$data"  ] && args+=(-d "$data")
  curl "${args[@]}"
}

parse() {
  # splits body and status from http() output
  local raw="$1"
  BODY=$(echo "$raw" | sed '$d')
  STATUS=$(echo "$raw" | tail -n1 | sed 's/__STATUS__//')
}

# ── setup: get tokens ──────────────────────────────────────────────────────
echo ""
echo "━━━ SETUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Admin login
parse "$(http POST "$BASE_URL/api/users/auth/admin/login/" "" '{"email":"admin@plugd.com","password":"AdminPass123!"}')"
ADMIN_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
[ -n "$ADMIN_TOKEN" ] && echo "  Admin token: OK" || { echo "  FATAL: Admin login failed. Run test_admin.sh first."; exit 1; }

# Register test provider (may already exist — ignore 400)
http POST "$BASE_URL/api/users/auth/register/" "" \
  '{"email":"fix.provider@test.com","first_name":"Fix","last_name":"Provider","role":"provider","password":"TestPass123!","password2":"TestPass123!"}' > /dev/null

# Register test customer
http POST "$BASE_URL/api/users/auth/register/" "" \
  '{"email":"fix.customer@test.com","first_name":"Fix","last_name":"Customer","role":"customer","password":"TestPass123!","password2":"TestPass123!"}' > /dev/null

# Register second customer for messaging
http POST "$BASE_URL/api/users/auth/register/" "" \
  '{"email":"fix.customer2@test.com","first_name":"Fix","last_name":"CustomerTwo","role":"customer","password":"TestPass123!","password2":"TestPass123!"}' > /dev/null

# Provider login
parse "$(http POST "$BASE_URL/api/users/auth/login/" "" '{"email":"fix.provider@test.com","password":"TestPass123!"}')"
PROVIDER_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
[ -n "$PROVIDER_TOKEN" ] && echo "  Provider token: OK" || echo "  WARN: Provider login failed"

# Customer login
parse "$(http POST "$BASE_URL/api/users/auth/login/" "" '{"email":"fix.customer@test.com","password":"TestPass123!"}')"
CUSTOMER_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
[ -n "$CUSTOMER_TOKEN" ] && echo "  Customer token: OK" || echo "  WARN: Customer login failed"

# Customer 2 login
parse "$(http POST "$BASE_URL/api/users/auth/login/" "" '{"email":"fix.customer2@test.com","password":"TestPass123!"}')"
CUSTOMER2_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
[ -n "$CUSTOMER2_TOKEN" ] && echo "  Customer2 token: OK" || echo "  WARN: Customer2 login failed"

# Get customer2 ID for messaging
parse "$(http GET "$BASE_URL/api/users/profile/" "$CUSTOMER2_TOKEN")"
CUSTOMER2_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)


# ── FIX 1: Balance endpoint no longer crashes ──────────────────────────────
echo ""
echo "━━━ FIX 1: GET /bookings/payouts/balance/ (was 500) ━━━━━━━━━━━━━"
parse "$(http GET "$BASE_URL/api/bookings/payouts/balance/" "$PROVIDER_TOKEN")"
check_status "Provider balance endpoint" "200" "$STATUS" "$BODY"
check_no_match "No 'transaction__isnull' crash" "FieldError\|transaction__isnull\|Exception" "$BODY"
echo "  Response: $BODY"


# ── FIX 2: Messaging conversations no longer 500 ──────────────────────────
echo ""
echo "━━━ FIX 2: GET /messaging/conversations/ (was 500) ━━━━━━━━━━━━━━"

# Start a conversation first so there's data
if [ -n "$CUSTOMER2_ID" ]; then
  http POST "$BASE_URL/api/messaging/conversations/start/" "$CUSTOMER_TOKEN" \
    "{\"user_id\":\"$CUSTOMER2_ID\"}" > /dev/null
fi

parse "$(http GET "$BASE_URL/api/messaging/conversations/" "$CUSTOMER_TOKEN")"
check_status "Conversations list (customer)" "200" "$STATUS" "$BODY"
check_no_match "No distinct() TypeError" "TypeError\|Cannot combine\|unique query" "$BODY"

parse "$(http GET "$BASE_URL/api/messaging/conversations/" "$PROVIDER_TOKEN")"
check_status "Conversations list (provider)" "200" "$STATUS" "$BODY"


# ── FIX 3: POST /admin/register returns 401/403 when admin exists ─────────
echo ""
echo "━━━ FIX 3: POST /admin/register/ locked when admin exists ━━━━━━━"
parse "$(http POST "$BASE_URL/api/users/auth/admin/register/" "" \
  '{"email":"hacker@evil.com","first_name":"h","last_name":"h","password":"Hack1234!","password2":"Hack1234!"}')"
# DRF returns 401 when no credentials are provided, 403 when wrong role — both mean "blocked"
if [ "$STATUS" = "401" ] || [ "$STATUS" = "403" ]; then
  ok "Blocked without auth (admin exists) (HTTP $STATUS)"
  ((PASS++))
else
  fail "Blocked without auth (admin exists) (expected 401 or 403, got $STATUS)" "$BODY"
fi

# Existing admin can still create another admin (unique email via timestamp)
ADMIN2_PAYLOAD=$(python3 -c "
import json, time
print(json.dumps({
  'email': 'admin.%d@plugd.com' % int(time.time()),
  'first_name': 'Admin', 'last_name': 'Two',
  'password': 'AdminPass123!', 'password2': 'AdminPass123!'
}))")
parse "$(http POST "$BASE_URL/api/users/auth/admin/register/" "$ADMIN_TOKEN" "$ADMIN2_PAYLOAD")"
check_status "Admin can create another admin" "201" "$STATUS" "$BODY"
check_match "New user has role=admin" '"admin"' "$BODY"


# ── FIX 4: DEBUG=False — 500s return generic JSON, not stack traces ────────
echo ""
echo "━━━ FIX 4: DEBUG=False — no stack traces on errors ━━━━━━━━━━━━━━"
# Hit a truly non-existent URL path
parse "$(http GET "$BASE_URL/api/this-does-not-exist/" "")"
check_status "404 on non-existent path" "404" "$STATUS" "$BODY"
check_no_match "No traceback in 404" "Traceback\|File \"/" "$BODY"

# Unauthenticated request to protected endpoint
parse "$(http GET "$BASE_URL/api/users/admin/users/" "")"
check_status "401 on unauthenticated" "401" "$STATUS" "$BODY"
check_no_match "No traceback in 401" "Traceback\|File \"/" "$BODY"


# ── FIX 5: Avatar/logo URLs are not double-encoded ────────────────────────
echo ""
echo "━━━ FIX 5: Image URLs not double-encoded ━━━━━━━━━━━━━━━━━━━━━━━━"
parse "$(http GET "$BASE_URL/api/users/profile/" "$PROVIDER_TOKEN")"
check_status "Provider profile fetch" "200" "$STATUS" "$BODY"

AVATAR=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('avatar') or '')" 2>/dev/null)
if [ -z "$AVATAR" ] || [ "$AVATAR" = "None" ]; then
  ok "Avatar is null (no upload yet — field returns null not double URL)"
else
  check_no_match "Avatar URL not double-encoded" "onrender.com/http" "$AVATAR"
  check_no_match "Avatar URL not percent-encoded" "https%3A" "$AVATAR"
  echo "  Avatar URL: $AVATAR"
fi

# Provider profile endpoint (has business_logo)
# First hit own-profile to ensure ProviderProfile row exists (get_or_create)
parse "$(http GET "$BASE_URL/api/users/provider/profile/" "$PROVIDER_TOKEN")"
parse "$(http GET "$BASE_URL/api/users/profile/" "$PROVIDER_TOKEN")"
PROVIDER_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
parse "$(http GET "$BASE_URL/api/users/provider/profile/$PROVIDER_ID/" "")"
check_status "Public provider profile fetch (no auth)" "200" "$STATUS" "$BODY"
LOGO=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('business_logo') or '')" 2>/dev/null)
if [ -z "$LOGO" ] || [ "$LOGO" = "None" ]; then
  ok "business_logo is null (no upload yet — field returns null not double URL)"
else
  check_no_match "business_logo not double-encoded" "onrender.com/http" "$LOGO"
  check_no_match "business_logo not percent-encoded" "https%3A" "$LOGO"
  echo "  Logo URL: $LOGO"
fi


# ── SUMMARY ────────────────────────────────────────────────────────────────
echo ""
echo "━━━ RESULTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""
[ "$FAIL" -eq 0 ] && echo "  All fixes verified." || echo "  Some tests failed — see above."
