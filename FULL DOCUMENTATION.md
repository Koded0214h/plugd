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

### Register
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
  "role": "customer", // "customer", "provider", or "hub"
  "business_name": "My Business" // required for provider/hub
}
```

**Response (201 Created):**
```json
{
  "user": { ... },   // full user profile
  "refresh": "...",
  "access": "...",
  "message": "User created successfully"
}
```

---

### Login
**POST** `/users/auth/login/`

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securePass123!"
}
```

**Response (200 OK):**
```json
{
  "user": { ... },
  "refresh": "...",
  "access": "..."
}
```

---

### Admin Register (Dedicated)
**POST** `/users/auth/admin/register/`

Allows creation of an admin user. Automatically sets `is_staff=True` and `verification_status="verified"`.
*No Authentication required (Public for initial setup).*

---

### Admin Login (Dedicated)
**POST** `/users/auth/admin/login/`

Dedicated login for admins. Rejects any user who does not have the `admin` role.

---

### Refresh Token
**POST** `/users/auth/token/refresh/`

**Request body:**
```json
{ "refresh": "..." }
```

**Response (200 OK):**
```json
{ "access": "..." }
```

---

### Logout
**POST** `/users/auth/logout/`

**Request body:** `{ "refresh": "..." }`
*Requires Authentication.*

---

## 2. User & Provider Profiles

### Get/Update Own User Profile
**GET** `/users/profile/`  
**PATCH** `/users/profile/` (partial update)

Contains basic user information, verification status, and Stripe onboarding status.
*Requires Authentication.*

**Response example:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "role": "customer",
  "verification_status": "unverified",
  "avatar": null,
  "avatar_url": null,
  "bio": "",
  "location": "",
  "business_name": "",
  "stripe_onboarding_complete": false,
  "last_active": "2026-03-28T12:00:00Z",
  "is_online": true
}
```

---

### Change Password
**POST** `/users/profile/change-password/`

**Request body:**
```json
{
  "old_password": "currentPassword123",
  "new_password": "newSecurePass456!",
  "new_password2": "newSecurePass456!"
}
```
*Requires Authentication.*

---

### Get/Update Provider Business Profile
**GET** `/users/provider/profile/`  
**PATCH** `/users/provider/profile/` (partial update)

Specifically for provider-only business details (logo, social links, ratings).
*Requires Authentication (Provider/Hub only).*

**Response:**
```json
{
  "id": "uuid",
  "user": "user_id",
  "user_email": "...",
  "user_full_name": "...",
  "business_logo": null,
  "business_description": "...",
  "years_in_business": 5,
  "website": "...",
  "social_links": {...},
  "services_offered": "...",
  "average_rating": 0.0,
  "total_reviews": 0,
  "completed_bookings": 0
}
```

---

### Public Provider Profile
**GET** `/users/provider/profile/<user_id>/`  
*No Authentication required.*

---

## 3. Categories & Listings

### List Categories
**GET** `/core/categories/`

Returns all active categories for filtering or listing creation.
*No Authentication required.*

---

### Create Listing (Provider only)
**POST** `/core/listings/`

```json
{
  "category": "category_uuid",
  "title": "Professional Photography",
  "description": "...",
  "pricing_type": "hourly", // "fixed", "hourly", "daily"
  "price": 75.00,
  "currency": "USD",
  "location": "Los Angeles, CA",
  "is_remote_available": true,
  "is_active": true
}
```
*Requires Authentication (Provider only).*

---

### List/Update/Delete Provider's Listings
**GET** `/core/listings/` → list all of your listings  
**GET** `/core/listings/<id>/` → retrieve one  
**PATCH** `/core/listings/<id>/` → update  
**DELETE** `/core/listings/<id>/` → delete  
*Requires Authentication (Provider only).*

---

### Public Listings (Browse)
**GET** `/core/public/listings/?category=...&pricing_type=...&search=...&ordering=price`  
Returns list of active listings (paginated).

**GET** `/core/public/listings/<id>/` → view a single listing (increments view count)

---

## 4. Availability (Provider)

### Create Availability
**POST** `/bookings/availabilities/`

```json
{
  "listing": "listing_id",
  "date": "2026-03-24",
  "start_time": "10:00:00",
  "end_time": "12:00:00"
}
```
*Requires Authentication (Provider only).*

### List/Update/Delete Availabilities
**GET** `/bookings/availabilities/` → list all yours  
**GET/PATCH/DELETE** `/bookings/availabilities/<id>/`

---

### Get Available Slots for a Listing (Public)
**GET** `/bookings/listings/<listing_id>/slots/` → returns list of unbooked slots

---

## 5. Bookings & Payments

### Create Booking (Customer)
**POST** `/bookings/bookings/create/`

```json
{
  "listing": "listing_id",
  "availability": "availability_id"
}
```
*Requires Authentication.*

**Response (201):**
```json
{
  "id": "booking_id",
  "stripe_payment_intent_id": "...",
  "stripe_client_secret": "...",
  "status": "pending",
  "total_amount": "85.00",
  "platform_fee": "8.50",
  "provider_amount": "76.50",
  ...
}
```

### List Bookings
**GET** `/bookings/bookings/`  
Returns list of bookings for authenticated user (customer or provider).

### Get Single Booking
**GET** `/bookings/bookings/<id>/`

### Payment Confirmation (Webhook)
The backend handles Stripe webhooks automatically to update status to `confirmed`. Frontend should use the `stripe_client_secret` with Stripe Elements to complete the payment.

---

## 6. Stripe Connect Onboarding (Provider)

### Start Onboarding / Get Dashboard Link
**POST** `/users/stripe/create-account/`

Returns a Stripe Connect onboarding URL if not completed, or a Dashboard link if already completed.
*Requires Authentication (Provider only).*

### Onboarding Flow Handlers
- **GET** `/users/stripe/refresh/`: User is redirected here if they exit onboarding early. Returns instructions to restart.
- **GET** `/users/stripe/return/`: User is redirected here after successful onboarding. Backend validates status and updates `stripe_onboarding_complete`.

---

## 7. Verification

### Submit Verification (ID upload)
**POST** `/users/verification/request/` (multipart/form-data)

- `id_number`: string
- `document`: file (image of ID)
- `additional_notes`: string (optional)

### Check Status
**GET** `/users/verification/status/`

**Response:**
```json
{
  "status": "pending", // "pending", "verified", "rejected"
  "submitted_at": "...",
  "rejection_reason": ""
}
```

---

## 8. Admin Only

### View Verification Queue
**GET** `/users/admin/verification/queue/` (admin token required)

### Review Verification
**POST** `/users/admin/verification/review/<request_id>/`
```json
{
  "status": "verified", // or "rejected"
  "rejection_reason": "Optional"
}
```

---

## 9. Messaging & Real-time Chat

### Start/Get Conversation
**POST** `/messaging/conversations/start/`
**Body:** `{"user_id": "other_user_uuid"}`
*Requires Authentication.*
Returns the `conversation_id` and existing message metadata.

### List Conversations
**GET** `/messaging/conversations/`
*Requires Authentication.*
Returns a list of all conversations the user is participating in, including the last message and unread count.

### Message History
**GET** `/messaging/conversations/<conversation_id>/history/`
*Requires Authentication.*
Returns all messages in the specified conversation.

### Mark Messages as Read
**POST** `/messaging/conversations/<conversation_id>/read/`
*Requires Authentication.*
Marks all messages sent by the *other* user in this conversation as read.

---

### Real-time WebSockets (Chat)
**Endpoint:** `ws://localhost:8000/ws/chat/<conversation_id>/?token=<access_token>`

- **Authentication**: Pass the user's JWT `access` token in the `token` query parameter.
- **Connection**: Only participants of the conversation can connect.
- **Sending Messages**: 
  Send JSON: `{"message": "Your text here"}`
- **Receiving Messages**:
  Backend broadcasts JSON to all participants in the room:
  ```json
  {
    "message": {
      "id": "message_uuid",
      "conversation": "...",
      "sender": "sender_id",
      "sender_email": "...",
      "text": "...",
      "is_read": false,
      "created_at": "..."
    }
  }
  ```

---

## Important Notes
- **Authentication**: All private endpoints require `Authorization: Bearer <access_token>`.
- **UUIDs**: Most ID fields use UUID format.
- **Pagination**: Public listing and booking lists are paginated.
- **Stripe**: Use test card numbers (e.g., 4242...) for payment testing in the sandbox.

---

For any questions, contact the backend team (coder0214h@gamil.com).
