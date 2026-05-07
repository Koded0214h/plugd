import logging

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
    except (BadHeaderError, Exception) as exc:
        logger.warning("Unable to send onboarding email to %s: %s", user.email, exc)
