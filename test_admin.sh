#!/bin/bash

BASE_URL="https://plugd-wxjr.onrender.com"
ADMIN_EMAIL="admin@plugd.com"
ADMIN_PASSWORD="AdminPass123!"

echo "======================================"
echo " STEP 1: Register first admin"
echo " (Skipped if an admin already exists)"
echo "======================================"
curl -s -X POST "$BASE_URL/api/users/auth/admin/register/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$ADMIN_EMAIL\",
    \"first_name\": \"Admin\",
    \"last_name\": \"User\",
    \"password\": \"$ADMIN_PASSWORD\",
    \"password2\": \"$ADMIN_PASSWORD\"
  }" | python3 -m json.tool

echo ""
echo "======================================"
echo " STEP 2: Admin login"
echo "======================================"
sleep 1

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/auth/admin/login/" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$ADMIN_EMAIL\",
    \"password\": \"$ADMIN_PASSWORD\"
  }")

if [ -z "$LOGIN_RESPONSE" ]; then
  echo "ERROR: Empty response. Server may still be waking up. Re-run the script."
  exit 1
fi

echo "$LOGIN_RESPONSE" | python3 -m json.tool

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo ""
  echo "======================================"
  echo " LOGIN FAILED - Use Render Shell to"
  echo " create a fresh admin account:"
  echo "======================================"
  echo ""
  echo "python manage.py shell -c \""
  printf "from users.models import User, UserRole, VerificationStatus\n"
  printf "User.objects.filter(role='admin').delete()\n"
  printf "u = User(email='admin@plugd.com', username='admin@plugd.com', first_name='Admin', last_name='User', role=UserRole.ADMIN, is_staff=True, verification_status=VerificationStatus.VERIFIED)\n"
  printf "u.set_password('AdminPass123!')\n"
  printf "u.save()\n"
  printf "print('Admin created:', u.email)\n"
  echo "\""
  exit 1
fi

echo ""
echo "Token: ${TOKEN:0:50}..."

echo ""
echo "======================================"
echo " STEP 3: Admin user list (expect 200)"
echo "======================================"
curl -s -X GET "$BASE_URL/api/users/admin/users/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "======================================"
echo " STEP 4: Register a regular customer"
echo "======================================"
curl -s -X POST "$BASE_URL/api/users/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@test.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer",
    "password": "TestPass123!",
    "password2": "TestPass123!"
  }' | python3 -m json.tool

echo ""
echo "======================================"
echo " STEP 5: Non-admin login (expect 403)"
echo "======================================"
curl -s -X POST "$BASE_URL/api/users/auth/admin/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@test.com",
    "password": "TestPass123!"
  }' | python3 -m json.tool

echo ""
echo "======================================"
echo " STEP 6: Verification queue (expect 200)"
echo "======================================"
curl -s -X GET "$BASE_URL/api/users/admin/verification/queue/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "======================================"
echo " ALL TESTS DONE"
echo "======================================"
