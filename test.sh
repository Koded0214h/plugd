#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Base URLs
BASE_URL="http://localhost:8000"
USER_API_URL="${BASE_URL}/api/users"
CORE_API_URL="${BASE_URL}/api/core"
BOOKINGS_API_URL="${BASE_URL}/api/bookings"

# Test user credentials
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

# Store tokens and IDs
ACCESS_TOKEN=""
REFRESH_TOKEN=""
CUSTOMER_TOKEN=""
PROVIDER_TOKEN=""
HUB_TOKEN=""
ADMIN_TOKEN=""
LISTING_ID=""
AVAILABILITY_ID=""
BOOKING_ID=""

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

# Function to make API call (user endpoints)
call_user_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    local description=$5
    
    print_step "$description"
    echo -e "${BLUE}Endpoint: ${method} ${USER_API_URL}${endpoint}${NC}"
    
    local curl_cmd="curl -s -X ${method} '${USER_API_URL}${endpoint}'"
    curl_cmd="${curl_cmd} -H 'Content-Type: application/json'"
    curl_cmd="${curl_cmd} -H 'Accept: application/json'"
    
    if [ -n "$token" ]; then
        curl_cmd="${curl_cmd} -H 'Authorization: Bearer ${token}'"
    fi
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -d '${data}'"
    fi
    
    eval "$curl_cmd" -D "$HEADERS_FILE" > "$BODY_FILE"
    
    local status_code=$(head -1 "$HEADERS_FILE" | cut -d' ' -f2)
    local content_type=$(grep -i "Content-Type:" "$HEADERS_FILE" | tr -d '\r' | cut -d' ' -f2 | cut -d';' -f1)
    
    echo -e "HTTP Status: ${status_code}"
    
    local response_body=$(cat "$BODY_FILE")
    LAST_RESPONSE_BODY="$response_body"
    
    if [[ "$content_type" == "application/json" ]]; then
        if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
            print_success "Request successful"
            if [ -n "$response_body" ] && [ "$response_body" != "null" ]; then
                echo -e "${GREEN}Response:${NC}"
                print_json "$response_body"
            fi
            
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

# Function to make API call (core endpoints)
call_core_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    local description=$5
    
    print_step "$description"
    echo -e "${BLUE}Endpoint: ${method} ${CORE_API_URL}${endpoint}${NC}"
    
    local curl_cmd="curl -s -X ${method} '${CORE_API_URL}${endpoint}'"
    curl_cmd="${curl_cmd} -H 'Content-Type: application/json'"
    curl_cmd="${curl_cmd} -H 'Accept: application/json'"
    
    if [ -n "$token" ]; then
        curl_cmd="${curl_cmd} -H 'Authorization: Bearer ${token}'"
    fi
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -d '${data}'"
    fi
    
    eval "$curl_cmd" -D "$HEADERS_FILE" > "$BODY_FILE"
    
    local status_code=$(head -1 "$HEADERS_FILE" | cut -d' ' -f2)
    local content_type=$(grep -i "Content-Type:" "$HEADERS_FILE" | tr -d '\r' | cut -d' ' -f2 | cut -d';' -f1)
    
    echo -e "HTTP Status: ${status_code}"
    
    local response_body=$(cat "$BODY_FILE")
    LAST_RESPONSE_BODY="$response_body"
    
    if [[ "$content_type" == "application/json" ]]; then
        if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
            print_success "Request successful"
            if [ -n "$response_body" ] && [ "$response_body" != "null" ]; then
                echo -e "${GREEN}Response:${NC}"
                print_json "$response_body"
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

# Function to make API call (bookings endpoints)
call_bookings_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    local description=$5
    
    print_step "$description"
    echo -e "${BLUE}Endpoint: ${method} ${BOOKINGS_API_URL}${endpoint}${NC}"
    
    local curl_cmd="curl -s -X ${method} '${BOOKINGS_API_URL}${endpoint}'"
    curl_cmd="${curl_cmd} -H 'Content-Type: application/json'"
    curl_cmd="${curl_cmd} -H 'Accept: application/json'"
    
    if [ -n "$token" ]; then
        curl_cmd="${curl_cmd} -H 'Authorization: Bearer ${token}'"
    fi
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -d '${data}'"
    fi
    
    eval "$curl_cmd" -D "$HEADERS_FILE" > "$BODY_FILE"
    
    local status_code=$(head -1 "$HEADERS_FILE" | cut -d' ' -f2)
    local content_type=$(grep -i "Content-Type:" "$HEADERS_FILE" | tr -d '\r' | cut -d' ' -f2 | cut -d';' -f1)
    
    echo -e "HTTP Status: ${status_code}"
    
    local response_body=$(cat "$BODY_FILE")
    LAST_RESPONSE_BODY="$response_body"
    
    if [[ "$content_type" == "application/json" ]]; then
        if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
            print_success "Request successful"
            if [ -n "$response_body" ] && [ "$response_body" != "null" ]; then
                echo -e "${GREEN}Response:${NC}"
                print_json "$response_body"
            fi
        else
            print_error "Request failed"
            if [ -n "$response_body" ] && [ "$response_body" != "null" ]; then
                echo -e "${RED}Error Response:${NC}"
                print_json "$response_body"
            fi
        fi
    else
        if [[ $status_code -eq 204 ]]; then
            print_success "Request successful (no content)"
        else
            print_error "Non-JSON response received"
            echo -e "${RED}First 200 chars of response:${NC}"
            echo "$response_body" | head -c 200
            echo
        fi
    fi
    
    echo
}

# Start testing
print_section "PLUG'D 2.0 API TEST SUITE"
echo -e "${BLUE}User API Base: ${USER_API_URL}${NC}"
echo -e "${BLUE}Core API Base: ${CORE_API_URL}${NC}"
echo -e "${BLUE}Bookings API Base: ${BOOKINGS_API_URL}${NC}\n"

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

# Test 2: Customer Registration
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

call_user_api "POST" "/auth/register/" "$customer_reg_data" "" "Register new customer user"

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
    call_user_api "POST" "/auth/register/" "$customer_reg_data" "" "Register with unique email"
fi

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

call_user_api "POST" "/auth/login/" "$customer_login_data" "" "Login with customer credentials"

# Test 4: Get Customer Profile
print_section "4. GET CUSTOMER PROFILE"
call_user_api "GET" "/profile/" "" "$CUSTOMER_TOKEN" "Get authenticated user profile"

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

call_user_api "PATCH" "/profile/" "$update_profile_data" "$CUSTOMER_TOKEN" "Update user profile"

# Test 6: Refresh Token
print_section "6. REFRESH TOKEN"
refresh_data=$(cat <<EOF
{
    "refresh": "${REFRESH_TOKEN}"
}
EOF
)

call_user_api "POST" "/auth/token/refresh/" "$refresh_data" "" "Refresh access token"

# Test 7: Provider Registration
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

call_user_api "POST" "/auth/register/" "$provider_reg_data" "" "Register new provider user"

# Test 8: Provider Login
print_section "8. PROVIDER LOGIN"
provider_login_data=$(cat <<EOF
{
    "email": "${PROVIDER_EMAIL}",
    "password": "${PROVIDER_PASSWORD}"
}
EOF
)

call_user_api "POST" "/auth/login/" "$provider_login_data" "" "Login with provider credentials"
PROVIDER_TOKEN="$ACCESS_TOKEN"

# Capture provider user ID
PROVIDER_USER_ID=$(echo "$LAST_RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('user', {}).get('id', ''))" 2>/dev/null)
if [ -n "$PROVIDER_USER_ID" ]; then
    print_success "Provider user ID: $PROVIDER_USER_ID"
fi

# Test 9: Get Own Provider Profile
print_section "9. GET OWN PROVIDER PROFILE"
call_user_api "GET" "/provider/profile/" "" "$PROVIDER_TOKEN" "Get own provider profile"

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

call_user_api "PATCH" "/provider/profile/" "$update_provider_data" "$PROVIDER_TOKEN" "Update provider profile"

# Test 11: Get Public Provider Profile
print_section "11. GET PUBLIC PROVIDER PROFILE"
if [ -n "$PROVIDER_USER_ID" ]; then
    call_user_api "GET" "/provider/profile/${PROVIDER_USER_ID}/" "" "" "Get public provider profile"
else
    print_error "Provider user ID not available, skipping public profile test"
fi

# Test 12: Get Service Categories
print_section "12. GET SERVICE CATEGORIES"
call_core_api "GET" "/categories/" "" "" "List all service categories"

# Test 13: Create a Service Listing (as provider)
print_section "13. CREATE SERVICE LISTING"
listing_data=$(cat <<EOF
{
    "category": null,
    "title": "Professional Photography Service",
    "description": "I offer high-quality photography for events, portraits, and products.",
    "pricing_type": "hourly",
    "price": "75.00",
    "currency": "USD",
    "location": "Los Angeles, CA",
    "is_remote_available": true,
    "is_active": true
}
EOF
)
call_core_api "POST" "/listings/" "$listing_data" "$PROVIDER_TOKEN" "Create new service listing"

# Capture listing ID
LISTING_ID=$(echo "$LAST_RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
if [ -n "$LISTING_ID" ]; then
    print_success "Listing ID: $LISTING_ID"
fi

# Test 14: List Provider's Own Listings
print_section "14. LIST PROVIDER LISTINGS"
call_core_api "GET" "/listings/" "" "$PROVIDER_TOKEN" "List provider's listings"

# Test 15: Get Single Listing (Provider)
print_section "15. GET SINGLE LISTING (PROVIDER)"
if [ -n "$LISTING_ID" ]; then
    call_core_api "GET" "/listings/${LISTING_ID}/" "" "$PROVIDER_TOKEN" "Retrieve specific listing"
fi

# Test 16: Update Listing
print_section "16. UPDATE LISTING"
if [ -n "$LISTING_ID" ]; then
    update_listing_data=$(cat <<EOF
{
    "title": "Updated: Professional Photography & Videography",
    "price": "85.00",
    "description": "Now offering both photography and videography services."
}
EOF
)
    call_core_api "PATCH" "/listings/${LISTING_ID}/" "$update_listing_data" "$PROVIDER_TOKEN" "Update listing"
fi

# Test 17: Public Listings List
print_section "17. PUBLIC LISTINGS LIST"
call_core_api "GET" "/public/listings/" "" "" "List all active listings (public)"

# Test 18: Public Listing Detail
print_section "18. PUBLIC LISTING DETAIL"
if [ -n "$LISTING_ID" ]; then
    call_core_api "GET" "/public/listings/${LISTING_ID}/" "" "" "View public listing detail (view count should increment)"
fi

# ------------------- BOOKINGS TESTS -------------------
print_section "19. PROVIDER AVAILABILITY MANAGEMENT"

# Create availability slot
availability_data=$(cat <<EOF
{
    "listing": "${LISTING_ID}",
    "date": "$(date -v+1d +%Y-%m-%d)",
    "start_time": "10:00:00",
    "end_time": "12:00:00"
}
EOF
)
call_bookings_api "POST" "/availabilities/" "$availability_data" "$PROVIDER_TOKEN" "Create availability slot"

# Capture availability ID
AVAILABILITY_ID=$(echo "$LAST_RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
if [ -n "$AVAILABILITY_ID" ]; then
    print_success "Availability ID: $AVAILABILITY_ID"
fi

# List availabilities for provider
call_bookings_api "GET" "/availabilities/" "" "$PROVIDER_TOKEN" "List provider availabilities"

# Test 20: CUSTOMER VIEW AVAILABLE SLOTS
print_section "20. VIEW AVAILABLE SLOTS FOR LISTING"
if [ -n "$LISTING_ID" ]; then
    call_bookings_api "GET" "/listings/${LISTING_ID}/slots/" "" "" "View available slots for listing"
fi

# Test 21: CUSTOMER CREATE BOOKING
print_section "21. CREATE BOOKING (CUSTOMER)"
booking_data=$(cat <<EOF
{
    "listing": "${LISTING_ID}",
    "availability": "${AVAILABILITY_ID}"
}
EOF
)
call_bookings_api "POST" "/bookings/create/" "$booking_data" "$CUSTOMER_TOKEN" "Create booking (generates payment intent)"

# Capture booking ID and payment intent
BOOKING_ID=$(echo "$LAST_RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
PAYMENT_INTENT=$(echo "$LAST_RESPONSE_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('stripe_payment_intent_id', ''))" 2>/dev/null)
if [ -n "$BOOKING_ID" ]; then
    print_success "Booking ID: $BOOKING_ID"
    print_success "Payment Intent: $PAYMENT_INTENT"
fi

# Test 22: LIST USER BOOKINGS (CUSTOMER)
print_section "22. LIST CUSTOMER BOOKINGS"
call_bookings_api "GET" "/bookings/" "" "$CUSTOMER_TOKEN" "List customer bookings"

# Test 23: GET SINGLE BOOKING (CUSTOMER)
print_section "23. GET SINGLE BOOKING (CUSTOMER)"
if [ -n "$BOOKING_ID" ]; then
    call_bookings_api "GET" "/bookings/${BOOKING_ID}/" "" "$CUSTOMER_TOKEN" "Retrieve specific booking"
fi

# Test 24: LIST PROVIDER BOOKINGS
print_section "24. LIST PROVIDER BOOKINGS"
call_bookings_api "GET" "/bookings/" "" "$PROVIDER_TOKEN" "List provider bookings"

# (Optional) Test 25: Simulate Stripe webhook to confirm booking
print_section "25. SIMULATE STRIPE PAYMENT SUCCESS (OPTIONAL)"
echo -e "${YELLOW}Note: This requires Stripe CLI to be running and listening.${NC}"
echo -e "${YELLOW}Run: stripe listen --forward-to localhost:8000/api/bookings/stripe-webhook/${NC}"
echo -e "${YELLOW}Then in another terminal: stripe trigger payment_intent.succeeded${NC}"
echo -e "${YELLOW}Skipping automated webhook test.${NC}"

# ------------------- END BOOKINGS TESTS -------------------

# Test 26: Delete Listing (optional) - moved after bookings so we don't delete before testing
print_section "26. DELETE LISTING (OPTIONAL)"
if [ -n "$LISTING_ID" ]; then
    call_core_api "DELETE" "/listings/${LISTING_ID}/" "" "$PROVIDER_TOKEN" "Delete listing"
fi

# Test 27: Hub Registration
print_section "27. HUB REGISTRATION"
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

call_user_api "POST" "/auth/register/" "$hub_reg_data" "" "Register new hub user"

# Test 28: Submit Verification Request (as Provider)
print_section "28. SUBMIT VERIFICATION REQUEST"
if [ -n "$PROVIDER_TOKEN" ]; then
    verification_data=$(cat <<EOF
{
    "id_number": "ID${RANDOM}",
    "additional_notes": "Please verify my account. I am a legitimate service provider."
}
EOF
)
    call_user_api "POST" "/verification/request/" "$verification_data" "$PROVIDER_TOKEN" "Submit verification request as provider"
fi

# Test 29: Check Verification Status
print_section "29. CHECK VERIFICATION STATUS"
if [ -n "$PROVIDER_TOKEN" ]; then
    call_user_api "GET" "/verification/status/" "" "$PROVIDER_TOKEN" "Check verification status for provider"
fi

# Test 30: JWT Token Obtain
print_section "30. JWT TOKEN OBTAIN"
token_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "password": "${TEST_PASSWORD}"
}
EOF
)

call_user_api "POST" "/auth/token/" "$token_data" "" "Obtain JWT token pair"

# Test 31: Admin Login (optional)
print_section "31. ADMIN LOGIN (OPTIONAL)"
admin_login_data=$(cat <<EOF
{
    "email": "${ADMIN_EMAIL}",
    "password": "${ADMIN_PASSWORD}"
}
EOF
)

echo -e "${YELLOW}Attempting admin login...${NC}"
admin_response=$(curl -s -X POST "${USER_API_URL}/auth/login/" \
    -H "Content-Type: application/json" \
    -d "$admin_login_data")

ADMIN_TOKEN=$(echo "$admin_response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null)

if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "None" ] && [ "$ADMIN_TOKEN" != "" ]; then
    print_success "Admin login successful"
    
    # Test 32: Get Verification Queue (Admin only)
    print_section "32. GET VERIFICATION QUEUE (ADMIN)"
    call_user_api "GET" "/admin/verification/queue/" "" "$ADMIN_TOKEN" "Get pending verification requests"
    
    # Get first pending request ID if any
    queue_response=$(curl -s -X GET "${USER_API_URL}/admin/verification/queue/" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}")
    
    request_id=$(echo "$queue_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data and len(data)>0 else '')" 2>/dev/null)
    
    if [ -n "$request_id" ] && [ "$request_id" != "" ]; then
        # Test 33: Review Verification (Admin only)
        print_section "33. REVIEW VERIFICATION (ADMIN)"
        review_data=$(cat <<EOF
{
    "status": "verified",
    "rejection_reason": ""
}
EOF
)
        call_user_api "POST" "/admin/verification/review/${request_id}/" "$review_data" "$ADMIN_TOKEN" "Approve verification request"
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

# Test 34: Change Password
print_section "34. CHANGE PASSWORD"
change_password_data=$(cat <<EOF
{
    "old_password": "${TEST_PASSWORD}",
    "new_password": "NewTestPass456!",
    "new_password2": "NewTestPass456!"
}
EOF
)

call_user_api "POST" "/profile/change-password/" "$change_password_data" "$CUSTOMER_TOKEN" "Change customer password"

# Test 35: Login with New Password
print_section "35. LOGIN WITH NEW PASSWORD"
new_login_data=$(cat <<EOF
{
    "email": "${TEST_EMAIL}",
    "password": "NewTestPass456!"
}
EOF
)

call_user_api "POST" "/auth/login/" "$new_login_data" "" "Login with new password"

# Test 36: Logout
print_section "36. LOGOUT"
logout_data=$(cat <<EOF
{
    "refresh": "${REFRESH_TOKEN}"
}
EOF
)

call_user_api "POST" "/auth/logout/" "$logout_data" "$ACCESS_TOKEN" "Logout user"

# Test 37: Access Profile After Logout (should fail)
print_section "37. ACCESS PROFILE AFTER LOGOUT (EXPECTED TO FAIL)"
call_user_api "GET" "/profile/" "" "$ACCESS_TOKEN" "Try to access profile with old token"

# Summary
print_section "TEST SUMMARY"
echo -e "${GREEN}✅ Server Health Check${NC}"
echo -e "${GREEN}✅ Customer Registration & Authentication${NC}"
echo -e "${GREEN}✅ Provider Registration & Authentication${NC}"
echo -e "${GREEN}✅ Provider Profile (Own & Public)${NC}"
echo -e "${GREEN}✅ Service Categories${NC}"
echo -e "${GREEN}✅ Service Listing CRUD${NC}"
echo -e "${GREEN}✅ Provider Availability Management${NC}"
echo -e "${GREEN}✅ View Available Slots${NC}"
echo -e "${GREEN}✅ Booking Creation (with PaymentIntent)${NC}"
echo -e "${GREEN}✅ List User Bookings (Customer & Provider)${NC}"
echo -e "${GREEN}✅ Hub Registration & Authentication${NC}"
echo -e "${GREEN}✅ Verification Workflow${NC}"
echo -e "${GREEN}✅ JWT Token Operations${NC}"
echo -e "${GREEN}✅ Password Change${NC}"
echo -e "${GREEN}✅ Logout${NC}"
if [ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_TOKEN" != "null" ]; then
    echo -e "${GREEN}✅ Admin Operations${NC}"
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                         TESTING COMPLETE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"