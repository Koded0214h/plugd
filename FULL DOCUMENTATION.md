# Plug'd 2.0 API Documentation (Frontend)

## Base URL
All endpoints are prefixed with:
```
https://plugd-9u4v.onrender.com/api
```

## API Explorer & Schema
- **Swagger UI:** `/api/docs/`
- **ReDoc:** `/api/redoc/`
- **JSON Schema:** `/api/schema/`

---

## 1. Authentication

### Register (Customer, Provider, Hub)
**POST** `/users/auth/register/`

**Request body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securePass123!",
  "password2": "securePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "role": "customer", // "customer", "provider", "hub"
  "business_name": "My Business" // required for provider/hub
}
```

**Response (201 Created):** returns `user` object, `access`, `refresh`.

---

### Login
**POST** `/users/auth/login/`

**Request body:**
```json
{ "email": "user@example.com", "password": "securePass123!" }
```

**Response (200 OK):** returns `user` object, `access`, `refresh`.

---

### Admin Register / Login
**POST** `/users/auth/admin/register/` (public, creates admin)  
**POST** `/users/auth/admin/login/` (dedicated admin login)

---

### Refresh Token
**POST** `/users/auth/token/refresh/`

**Request body:** `{ "refresh": "..." }` → `{ "access": "..." }`

---

### Logout
**POST** `/users/auth/logout/` (requires auth, body: `{ "refresh": "..." }`)

---

## 2. User & Provider Profiles

### Get / Update Own User Profile
**GET** `/users/profile/`  
**PATCH** `/users/profile/`

**Response:** `UserProfile` (id, email, role, verification_status, business_name, stripe_onboarding_complete, etc.)

### Change Password
**POST** `/users/profile/change-password/`

**Body:** `{ "old_password": "...", "new_password": "...", "new_password2": "..." }`

### Provider Business Profile
**GET** `/users/provider/profile/`  
**PATCH** `/users/provider/profile/`

**Response:** `ProviderProfile` (business_description, years_in_business, social_links, services_offered, average_rating, total_reviews, completed_bookings)

### Public Provider Profile
**GET** `/users/provider/profile/<user_id>/` (no auth)

---

## 3. Service Categories & Listings

### List Categories
**GET** `/core/categories/` (public, searchable)

### Provider Listings (CRUD)
- **GET** `/core/listings/` – list provider’s own listings
- **POST** `/core/listings/` – create (fields: title, description, pricing_type, price, currency, location, is_remote_available, booking_approval_type, category, featured_image, is_active)
- **GET** `/core/listings/<id>/`
- **PATCH** `/core/listings/<id>/`
- **DELETE** `/core/listings/<id>/`

### Public Listings (Browse)
- **GET** `/core/public/listings/` – filters: `category`, `pricing_type`, `is_remote_available`, `search`, `ordering`
- **GET** `/core/public/listings/<id>/` – increments view count

---

## 4. Availability (Provider)

### Manage Slots
- **GET / POST** `/bookings/availabilities/` – list or create (requires auth)
- **GET / PUT / PATCH / DELETE** `/bookings/availabilities/<id>/`

**Create body:** `{ "listing": "uuid", "date": "YYYY-MM-DD", "start_time": "HH:MM:SS", "end_time": "HH:MM:SS" }`

### Public Available Slots
**GET** `/bookings/listings/<listing_id>/slots/` – returns unbooked slots for that listing.

---

## 5. Bookings & Payments

### Create Booking (Customer)
**POST** `/bookings/bookings/create/`

**Body:** `{ "listing": "uuid", "availability": "uuid", "coupon_code": "optional" }`

**Response:** Booking object with `stripe_payment_intent_id`, `stripe_client_secret`, `status` (pending / pending_approval).

### List / Retrieve Bookings
- **GET** `/bookings/bookings/` (for authenticated user)
- **GET** `/bookings/bookings/<id>/`

### Provider Approve / Reject (for manual approval bookings)
- **POST** `/bookings/bookings/<id>/approve/` – creates PaymentIntent, status → pending
- **POST** `/bookings/bookings/<id>/reject/` – status → cancelled

### Stripe Webhook (backend only)
**POST** `/bookings/stripe-webhook/` – handled by server.

---

## 6. Coupons & Discounts

### Provider Coupon CRUD
- **GET / POST** `/coupons/provider/coupons/`
- **GET / PUT / PATCH / DELETE** `/coupons/provider/coupons/<id>/`

**POST body:** `{ "code": "SAVE10", "discount_type": "percentage", "discount_value": 10, "applicable_listings": [...], "usage_limit": 50, "per_user_limit": 1, "valid_until": "2026-12-31T23:59:59Z", "min_order_amount": 20, "is_active": true }`

### Admin Coupon CRUD (global)
- **GET / POST** `/coupons/admin/coupons/`
- **GET / PUT / PATCH / DELETE** `/coupons/admin/coupons/<id>/`

### Apply Coupon (Checkout)
**POST** `/coupons/apply/` (requires auth)

**Body:** `{ "code": "SAVE10", "total_amount": 100 }`

**Response:** `{ "coupon": {...}, "original_amount": "100.00", "discounted_amount": "90.00", "message": "Coupon is valid." }`

*Note: In booking creation, pass `coupon_code` directly – discount will be applied automatically.*

---

## 7. Service Requests & Quotes (Request & Quote System)

### Service Requests (Customer)
- **GET / POST** `/core/requests/` (customer creates, provider sees open requests)
- **GET** `/core/requests/<id>/`
- **PUT / PATCH** `/core/requests/<id>/update-status/` (customer can close/cancel)

**POST body:** `{ "title": "...", "description": "...", "category": "uuid", "budget": 500, "location": "...", "preferred_date": "2026-05-01", "preferred_time": "14:00:00", "is_remote_friendly": true }`

### Quotes (Provider)
- **GET / POST** `/core/requests/<service_request_id>/quotes/` (provider submits quote)
- **GET** `/core/quotes/<id>/`
- **POST** `/core/quotes/<id>/accept/` (customer accepts quote → creates booking automatically)
- **POST** `/core/quotes/<id>/reject/` (provider rejects own quote)

**Quote POST body:** `{ "description": "...", "price": 450, "estimated_duration": "3 hours", "valid_until": "2026-05-07T23:59:59Z" }`

---

## 8. Reviews

### Customer Creates Review (for a completed booking)
**POST** `/core/reviews/create/`

**Body:** `{ "booking": "uuid", "rating": 5, "comment": "Great work!" }` (requires auth, only customer of that booking)

### Provider Sees Received Reviews
**GET** `/core/provider/reviews/` (provider only)

**Response:** list of reviews with `rating`, `comment`, `customer_name`, `created_at`.

---

## 9. Hub Projects (Agency/Coordinator)

### Hub Project CRUD
- **GET / POST** `/bookings/projects/` (hub creates project)
- **GET / PUT / PATCH / DELETE** `/bookings/projects/<id>/`

**POST body:** `{ "title": "Smith Wedding", "description": "...", "budget": 5000, "customer": "customer_uuid" }`

### Invite Provider to Project
**POST** `/bookings/projects/<project_id>/invite/`

**Body:** `{ "provider_id": "provider_uuid" }`

### Manage Project Members
- **PATCH** `/bookings/projects/<project_id>/members/<member_id>/` – provider accepts/rejects invitation (`{ "status": "accepted" }`)
- **DELETE** `/bookings/projects/<project_id>/members/<member_id>/` – hub removes member

### Create Availability for Project Member (Hub only)
**POST** `/bookings/projects/<project_id>/members/<member_id>/availabilities/`

**Body:** same as regular availability (listing not required, `project_member` set automatically)

### View All Project Availabilities
**GET** `/bookings/projects/<project_id>/availabilities/`

### Create Unified Package for Customer
**POST** `/bookings/projects/<project_id>/package/`

**Body:** `{ "total_price": 4800, "description": "Package includes photography, venue, catering", "expires_at": "2026-06-01T23:59:59Z" }`

---

## 10. Payouts & Financials (Provider)

### Request Payout & View History
- **GET / POST** `/bookings/payouts/`

**POST body:** `{ "amount": 150.00 }` – triggers Stripe transfer automatically.

### View Available & Pending Balance
**GET** `/bookings/payouts/balance/`

**Response:** `{ "available_balance": "245.50", "pending_balance": "30.00" }`

---

## 11. Admin Financial & Payout Management

### View All Payout Requests
**GET** `/bookings/admin/payouts/`

### View Pending Payout Queue
**GET** `/bookings/admin/payouts/queue/`

### Platform Revenue Overview
**GET** `/bookings/admin/revenue/`

**Response:** `{ "total_platform_earnings": "1234.56", "total_payouts": "800.00", "net_revenue": "434.56", "pending_payouts": "150.00", "total_bookings": 42, "total_transactions": 38, "new_users_count": 12 }`

### All Transactions (Reconciliation)
**GET** `/bookings/admin/transactions/`

### Platform Settings (commission rate, etc.)
- **GET / POST** `/core/admin/settings/`
- **GET / PUT / PATCH** `/core/admin/settings/<key>/` (e.g., key = `commission_rate`)

---

## 12. Messaging & Real-time Chat

### Start / Get Conversation
**POST** `/messaging/conversations/start/` – `{ "user_id": "other_uuid" }`  
**POST** `/messaging/conversations/start/project/` – `{ "project_id": "uuid" }`

### List Conversations
**GET** `/messaging/conversations/`

### Message History
**GET** `/messaging/conversations/<conversation_id>/history/`

### Mark as Read
**POST** `/messaging/conversations/<conversation_id>/read/`

### WebSocket Chat
**URL:** `wss://plugd-9u4v.onrender.com/ws/chat/<conversation_id>/?token=<access_token>`  
**Send:** `{"message": "Hello"}`  
**Receive:** `{ "message": { "id": "...", "sender": "...", "text": "...", "created_at": "..." } }`

---

## Important Notes
- **Authentication:** All endpoints except public ones require `Authorization: Bearer <access_token>`.
- **UUIDs:** Use the full UUID format.
- **Pagination:** Listing endpoints (public listings, bookings, conversations) support `page` and `page_size`.
- **Stripe Connect:** Providers must complete Stripe onboarding before they can receive payments. Use `/users/stripe/create-account/` to get the onboarding link.

---

For any questions, contact the backend team (coder0214h@gmail.com).