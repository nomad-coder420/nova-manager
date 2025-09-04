import logging
import os

from nova_manager.service.email_service import email_service
from nova_manager.core.config import (
    ORG_INVITE_TEMPLATE_ID,
    WELCOME_TEMPLATE_ID,
    PASSWORD_RESET_TEMPLATE_ID,
)

logger = logging.getLogger(__name__)


def get_frontend_url() -> str:
    """Get frontend URL from environment or default"""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


async def send_invitation_email(
    email: str, invite_token: str, organisation_name: str, invited_by_name: str
) -> bool:
    """
    Send invitation email to user

    Args:
        email: Recipient email address
        invite_token: Invitation token for signup link
        organisation_name: Name of the organization
        invited_by_name: Name of person who sent invite

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    invite_link = f"{get_frontend_url()}/signup?invite={invite_token}"

    logger.info(f"Sending invitation email to: {email}")

    success, error_message = email_service.send_email(
        to=email,
        template_id=ORG_INVITE_TEMPLATE_ID,
        params={
            "invite_link": invite_link,
            "organisation_name": organisation_name,
            "invited_by_name": invited_by_name,
        },
    )

    if not success:
        logger.error(f"Failed to send invitation email to {email}: {error_message}")
        return False

    logger.info(f"Invitation email sent successfully to: {email}")
    return True


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """Send password reset email (for future use)"""
    # TODO: Implement when password reset feature is needed
    reset_link = f"{get_frontend_url()}/reset-password?token={reset_token}"

    logger.info(f"Sending password reset email to: {email}")
    success, error_message = email_service.send_email(
        to=email,
        template_id=PASSWORD_RESET_TEMPLATE_ID,
        params={
            "reset_link": reset_link,
        },
    )

    if not success:
        logger.error(f"Failed to send password reset email to {email}: {error_message}")
        return False

    logger.info(f"Password reset email sent successfully to: {email}")
    return True


async def send_welcome_email(email: str, name: str, organisation_name: str) -> bool:
    """Send welcome email after successful signup (for future use)"""
    # TODO: Implement welcome email template

    logger.info(f"Sending welcome email to: {email}")

    success, error_message = email_service.send_email(
        to=email,
        template_id=WELCOME_TEMPLATE_ID,
        params={
            "name": name,
            "organisation_name": organisation_name,
            "welcome_link": f"{get_frontend_url()}/console",
        },
    )
    if not success:
        logger.error(f"Failed to send welcome email to {email}: {error_message}")
        return False

    logger.info(f"Welcome email sent successfully to: {email}")
    return True
