import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import BadHeaderError, send_mail

logger = logging.getLogger(__name__)


def send_onboarding_email(user, source="registration"):
    subject = "Welcome to Plug'd 2.0"
    first_name = user.first_name.strip() if user.first_name else ""
    greeting_name = first_name or user.email
    login_method = "Google" if source == "google" else "email and password"

    message = (
        f"Hi {greeting_name},\n\n"
        "Welcome to Plug'd 2.0.\n\n"
        f"Your account was created successfully using {login_method}.\n"
        "You can now log in, complete your profile, and continue onboarding.\n\n"
        "If you did not create this account, please contact support immediately.\n\n"
        "Thanks,\n"
        "Plug'd Support"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except BaseException as exc:
        logger.warning("Unable to send onboarding email to %s: %s", user.email, exc)


def build_password_reset_link(uidb64, token):
    query_string = urlencode({"uid": uidb64, "token": token})
    return f"{settings.FRONTEND_URL}/reset-password?{query_string}"


def send_password_reset_email(user, reset_link):
    subject = "Reset your Plug'd 2.0 password"
    first_name = user.first_name.strip() if user.first_name else ""
    greeting_name = first_name or user.email

    message = (
        f"Hi {greeting_name},\n\n"
        "We received a request to reset your Plug'd 2.0 password.\n\n"
        f"Reset your password here: {reset_link}\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "Thanks,\n"
        "Plug'd Support"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except BaseException as exc:
        logger.warning("Unable to send password reset email to %s: %s", user.email, exc)
