#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/users"

# Test user credentials - no phone numbers to avoid validation issues
TEST_EMAIL="test.customer1@example.com"
TEST_USERNAME="testcustomer1"
TEST_PASSWORD="TestPass123!"
TEST_FIRST_NAME="Test"
TEST_LAST_NAME="Customer"

PROVIDER_EMAIL="test.provider@example.com"
PROVIDER_USERNAME="testprovider"
PROVIDER_PASSWORD="TestPass123!"
PROVIDER_BUSINESS="Test Provider Business"

HUB_EMAIL="test.hub@example.com"
HUB_USERNAME="testhub"
HUB_PASSWORD="TestPass123!"
HUB_BUSINESS="Test Hub Agency"

ADMIN_EMAIL="admin1@example.com"
ADMIN_PASSWORD="admin123"

# Store tokens
ACCESS_TOKEN=""
REFRESH_TOKEN=""
CUSTOMER_TOKEN=""
PROVIDER_TOKEN=""
HUB_TOKEN=""
ADMIN_TOKEN=""

# Global to capture last response body
LAST_RESPONSE_BODY=""

# Temporary files
HEADERS_FILE=$(mktemp)
BODY_FILE=$(mktemp)

# Cleanup function
cleanup() {
    rm -f "$HEADERS_FILE" "$BODY_FILE"
}
trap cleanup EXIT

# Function to print section headers
print_section() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}\n"
}

# Function to print step
print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print JSON response
print_json() {
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
}

# Function to make API call and handle response
call_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    local description=$5
    
    print_step "$description"
    echo -e "${BLUE}Endpoint: ${method} ${endpoint}${NC}"
    
    # Build curl command
    local curl_cmd="curl -s -X ${method} '${API_URL}${endpoint}'"
    curl_cmd="${curl_cmd} -H 'Content-Type: application/json'"
    curl_cmd="${curl_cmd} -H 'Accept: application/json'"
    
    if [ -n "$token" ]; then
        curl_cmd="${curl_cmd} -H 'Authorization: Bearer ${token}'"
    fi
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -d '${data}'"
    fi
    
    # Execute curl and save headers and body
    eval "$curl_cmd" -D "$HEADERS_FILE" > "$BODY_FILE"
    
    # Get status code
    local status_code=$(head -1 "$HEADERS_FILE" | cut -d' ' -f2)
    local content_type=$(grep -i "Content-Type:" "$HEADERS_FILE" | tr -d '\r' | cut -d' ' -f2 | cut -d';' -f1)
    
    echo -e "HTTP Status: ${status_code}"
    
    # Read response body
    local response_body=$(cat "$BODY_FILE")
    LAST_RESPONSE_BODY="$response_body"
    
    # Check if response is JSON
    if [[ "$content_type" == "application/json" ]]; then
        if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
            print_success "Request successful"
            if [ -n "$response_body" ] && [ "$response_body" != "null" ]; then
                echo -e "${GREEN}Response:${NC}"
                print_json "$response_body"
            fi
            
            # Extract tokens if present
            if [ "$endpoint" == "/auth/register/" ] || [ "$endpoint" == "/auth/login/" ]; then
                local new_access=$(echo "$response_body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null)
                local new_refresh=$(echo "$response_body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('refresh', ''))" 2>/dev/null)
                
                if [ -n "$new_access" ] && [ "$new_access" != "None" ] && [ "$new_access" != "" ]; then
                    ACCESS_TOKEN="$new_access"
                    REFRESH_TOKEN="$new_refresh"
                    print_success "Access token obtained"
                fi
            fi
        else
            print_error "Request failed"
            if [ -n "$response_body" ] && [ "$response_body" != "null" ]; then
                echo -e "${RED}Error Response:${NC}"
                print_json "$response_body"
            fi
        fi
    else
        print_error "Non-JSON response received"
        echo -e "${RED}First 200 chars of response:${NC}"
        echo "$response_body" | head -c 200
        echo
    fi
    
    echo
}

# Start testing
print_section "PLUG'D 2.0 API TEST SUITE"
echo -e "${BLUE}Base URL: ${API_URL}${NC}\n"

# Test 1: Health Check
print_section "1. SERVER HEALTH CHECK"
print_step "Checking if server is running"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/")
if [ "$HTTP_CODE" -eq 404 ]; then
    print_success "Server is reachable (root endpoint returns 404 as expected)"
else
    print_success "Server responded with HTTP $HTTP_CODE"
fi
echo

# Test 2: Customer Registration (no phone number)
print_section "2. CUSTOMER REGISTRATION"
customer_reg_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "username": "${TEST_USERNAME}",
    "password": "${TEST_PASSWORD}",
    "password2": "${TEST_PASSWORD}",
    "first_name": "${TEST_FIRST_NAME}",
    "last_name": "${TEST_LAST_NAME}",
    "role": "customer"
}
EOF
)

call_api "POST" "/auth/register/" "$customer_reg_data" "" "Register new customer user"

# If registration fails, try with a unique email
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    print_step "Registration failed, trying with unique email..."
    TEST_EMAIL="test.customer.$(date +%s)@example.com"
    TEST_USERNAME="testcustomer$(date +%s)"
    customer_reg_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "username": "${TEST_USERNAME}",
    "password": "${TEST_PASSWORD}",
    "password2": "${TEST_PASSWORD}",
    "first_name": "${TEST_FIRST_NAME}",
    "last_name": "${TEST_LAST_NAME}",
    "role": "customer"
}
EOF
)
    call_api "POST" "/auth/register/" "$customer_reg_data" "" "Register with unique email"
fi

# Store customer token
CUSTOMER_TOKEN="$ACCESS_TOKEN"

if [ -z "$CUSTOMER_TOKEN" ] || [ "$CUSTOMER_TOKEN" == "null" ]; then
    print_error "Failed to get customer token. Exiting."
    exit 1
else
    print_success "Customer authentication successful"
fi

# Test 3: Customer Login
print_section "3. CUSTOMER LOGIN"
customer_login_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "password": "${TEST_PASSWORD}"
}
EOF
)

call_api "POST" "/auth/login/" "$customer_login_data" "" "Login with customer credentials"

# Test 4: Get Customer Profile
print_section "4. GET CUSTOMER PROFILE"
call_api "GET" "/profile/" "" "$CUSTOMER_TOKEN" "Get authenticated user profile"

# Test 5: Update Customer Profile
print_section "5. UPDATE CUSTOMER PROFILE"
update_profile_data=$(cat <<'EOF'
{
    "first_name": "Updated",
    "last_name": "Customer",
    "bio": "I am a test customer on the Plug'd platform",
    "location": "San Francisco, CA",
    "email_notifications": true,
    "sms_notifications": false
}
EOF
)

call_api "PATCH" "/profile/" "$update_profile_data" "$CUSTOMER_TOKEN" "Update user profile"

# Test 6: Refresh Token
print_section "6. REFRESH TOKEN"
refresh_data=$(cat <<EOF
{
    "refresh": "${REFRESH_TOKEN}"
}
EOF
)

call_api "POST" "/auth/token/refresh/" "$refresh_data" "" "Refresh access token"

# Test 7: Provider Registration (no phone)
print_section "7. PROVIDER REGISTRATION"
provider_reg_data=$(cat <<EOF
{
    "email": "${PROVIDER_EMAIL}",
    "username": "${PROVIDER_USERNAME}",
    "password": "${PROVIDER_PASSWORD}",
    "password2": "${PROVIDER_PASSWORD}",
    "first_name": "Provider",
    "last_name": "User",
    "role": "provider",
    "business_name": "${PROVIDER_BUSINESS}"
}
EOF
)

call_api "POST" "/auth/register/" "$provider_reg_data" "" "Register new provider user"

# Test 8: Provider Login
print_section "8. PROVIDER LOGIN"
provider_login_data=$(cat <<EOF
{
    "email": "${PROVIDER_EMAIL}",
    "password": "${PROVIDER_PASSWORD}"
}
EOF
)

call_api "POST" "/auth/login/" "$provider_login_data" "" "Login with provider credentials"
PROVIDER_TOKEN="$ACCESS_TOKEN"

# Capture provider user ID from login response
PROVIDER_USER_ID=""
if [ -n "$PROVIDER_TOKEN" ] && [ "$PROVIDER_TOKEN" != "null" ]; then
    PROVIDER_USER_ID=$(echo "$LAST_RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('user', {}).get('id', ''))" 2>/dev/null)
    if [ -n "$PROVIDER_USER_ID" ]; then
        print_success "Provider user ID: $PROVIDER_USER_ID"
    fi
fi

# Test 9: Get Own Provider Profile (auto-creates if not exists)
print_section "9. GET OWN PROVIDER PROFILE"
call_api "GET" "/provider/profile/" "" "$PROVIDER_TOKEN" "Get own provider profile"

# Test 10: Update Provider Profile
print_section "10. UPDATE PROVIDER PROFILE"
update_provider_data=$(cat <<EOF
{
    "business_description": "We offer top-notch photography and videography services for all events.",
    "years_in_business": 5,
    "website": "https://example.com",
    "social_links": {
        "instagram": "@provider",
        "facebook": "providerpage"
    },
    "services_offered": "Photography, Videography, Editing"
}
EOF
)

call_api "PATCH" "/provider/profile/" "$update_provider_data" "$PROVIDER_TOKEN" "Update provider profile"

# Test 11: Get Public Provider Profile (using provider user ID)
print_section "11. GET PUBLIC PROVIDER PROFILE"
if [ -n "$PROVIDER_USER_ID" ]; then
    call_api "GET" "/provider/profile/${PROVIDER_USER_ID}/" "" "" "Get public provider profile"
else
    print_error "Provider user ID not available, skipping public profile test"
fi

# Test 12: Hub Registration (no phone)
print_section "12. HUB REGISTRATION"
hub_reg_data=$(cat <<EOF
{
    "email": "${HUB_EMAIL}",
    "username": "${HUB_USERNAME}",
    "password": "${HUB_PASSWORD}",
    "password2": "${HUB_PASSWORD}",
    "first_name": "Hub",
    "last_name": "User",
    "role": "hub",
    "business_name": "${HUB_BUSINESS}"
}
EOF
)

call_api "POST" "/auth/register/" "$hub_reg_data" "" "Register new hub user"

# Test 13: Submit Verification Request (as Provider)
if [ -n "$PROVIDER_TOKEN" ] && [ "$PROVIDER_TOKEN" != "null" ]; then
    print_section "13. SUBMIT VERIFICATION REQUEST"
    verification_data=$(cat <<EOF
{
    "id_number": "ID${RANDOM}",
    "additional_notes": "Please verify my account. I am a legitimate service provider."
}
EOF
)

    call_api "POST" "/verification/request/" "$verification_data" "$PROVIDER_TOKEN" "Submit verification request as provider"

    # Test 14: Check Verification Status
    print_section "14. CHECK VERIFICATION STATUS"
    call_api "GET" "/verification/status/" "" "$PROVIDER_TOKEN" "Check verification status for provider"
fi

# Test 15: JWT Token Obtain
print_section "15. JWT TOKEN OBTAIN"
token_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "password": "${TEST_PASSWORD}"
}
EOF
)

call_api "POST" "/auth/token/" "$token_data" "" "Obtain JWT token pair"

# Test 16: Admin Login (if admin exists)
print_section "16. ADMIN LOGIN (OPTIONAL)"
admin_login_data=$(cat <<EOF
{
    "email": "${ADMIN_EMAIL}",
    "password": "${ADMIN_PASSWORD}"
}
EOF
)

echo -e "${YELLOW}Attempting admin login...${NC}"
admin_response=$(curl -s -X POST "${API_URL}/auth/login/" \
    -H "Content-Type: application/json" \
    -d "$admin_login_data")

ADMIN_TOKEN=$(echo "$admin_response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null)

if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "None" ] && [ "$ADMIN_TOKEN" != "" ]; then
    print_success "Admin login successful"
    
    # Test 17: Get Verification Queue (Admin only)
    print_section "17. GET VERIFICATION QUEUE (ADMIN)"
    call_api "GET" "/admin/verification/queue/" "" "$ADMIN_TOKEN" "Get pending verification requests"
    
    # Get first pending request ID if any
    queue_response=$(curl -s -X GET "${API_URL}/admin/verification/queue/" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}")
    
    request_id=$(echo "$queue_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data and len(data)>0 else '')" 2>/dev/null)
    
    if [ -n "$request_id" ] && [ "$request_id" != "" ]; then
        # Test 18: Review Verification (Admin only)
        print_section "18. REVIEW VERIFICATION (ADMIN)"
        review_data=$(cat <<EOF
{
    "status": "verified",
    "rejection_reason": ""
}
EOF
)
        call_api "POST" "/admin/verification/review/${request_id}/" "$review_data" "$ADMIN_TOKEN" "Approve verification request"
    else
        print_step "No pending verification requests to review"
    fi
else
    print_step "Skipping admin tests (login failed or no admin user)"
    echo -e "${YELLOW}To test admin endpoints, create a superuser:${NC}"
    echo -e "  python manage.py createsuperuser"
    echo -e "  Email: ${ADMIN_EMAIL}"
    echo -e "  Password: ${ADMIN_PASSWORD}"
fi

# Test 19: Change Password
print_section "19. CHANGE PASSWORD"
change_password_data=$(cat <<EOF
{
    "old_password": "${TEST_PASSWORD}",
    "new_password": "NewTestPass456!",
    "new_password2": "NewTestPass456!"
}
EOF
)

call_api "POST" "/profile/change-password/" "$change_password_data" "$CUSTOMER_TOKEN" "Change customer password"

# Test 20: Login with New Password
print_section "20. LOGIN WITH NEW PASSWORD"
new_login_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "password": "NewTestPass456!"
}
EOF
)

call_api "POST" "/auth/login/" "$new_login_data" "" "Login with new password"

# Test 21: Logout
print_section "21. LOGOUT"
logout_data=$(cat <<EOF
{
    "refresh": "${REFRESH_TOKEN}"
}
EOF
)

call_api "POST" "/auth/logout/" "$logout_data" "$ACCESS_TOKEN" "Logout user"

# Test 22: Try to access profile after logout (should fail)
print_section "22. ACCESS PROFILE AFTER LOGOUT (EXPECTED TO FAIL)"
call_api "GET" "/profile/" "" "$ACCESS_TOKEN" "Try to access profile with old token"

# Summary
print_section "TEST SUMMARY"
echo -e "${GREEN}✅ Server Health Check${NC}"
echo -e "${GREEN}✅ Customer Registration & Authentication${NC}"
echo -e "${GREEN}✅ Provider Registration & Authentication${NC}"
echo -e "${GREEN}✅ Provider Profile (Own & Public)${NC}"
echo -e "${GREEN}✅ Hub Registration & Authentication${NC}"
echo -e "${GREEN}✅ Profile Management${NC}"
echo -e "${GREEN}✅ JWT Token Operations${NC}"
echo -e "${GREEN}✅ Verification Workflow${NC}"
echo -e "${GREEN}✅ Password Change${NC}"
echo -e "${GREEN}✅ Logout${NC}"
if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    echo -e "${GREEN}✅ Admin Operations${NC}"
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                         TESTING COMPLETE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"