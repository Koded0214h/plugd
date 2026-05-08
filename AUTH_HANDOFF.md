# Auth Handoff

## Google OAuth

The backend handles Google sign-in by verifying a Google ID token, not by exchanging an authorization code.

Frontend flow:

1. Use Google Sign-In on the client.
2. Obtain a Google ID token.
3. Send `POST /api/users/auth/google/` with:
   - `id_token`
   - optional `role` for first-time account creation
4. The backend verifies the token using `GOOGLE_OAUTH_CLIENT_ID`.
5. If valid, the backend creates or reuses the user and returns Django JWT tokens:
   - `access`
   - `refresh`

What the frontend needs:

- `GOOGLE_OAUTH_CLIENT_ID`
- backend base URL
- the `/api/users/auth/google/` endpoint

What the frontend does not need:

- Google client secret
- Gmail SMTP settings
- any email-sending logic

## Onboarding Email

Onboarding emails are sent only on the server.

Triggers:

- `POST /api/users/auth/register/`
- first-time Google sign-up via `POST /api/users/auth/google/`

Behavior:

- The backend sends a welcome email after a user is created.
- SMTP is configured in Django settings with Gmail.
- The frontend does not send mail and does not need SMTP credentials.

## Forgot Password

Password reset is also handled by the backend.

Flow:

1. Frontend sends `POST /api/users/auth/password/forgot/` with the user email.
2. Backend emails a reset link to that address if the account exists.
3. Frontend opens the reset page with the `uid` and `token` query parameters.
4. Frontend sends `POST /api/users/auth/password/reset/` with:
   - `uid`
   - `token`
   - `new_password`
   - `new_password2`

The frontend never sees or handles SMTP credentials.
