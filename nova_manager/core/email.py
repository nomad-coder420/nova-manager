import logging
import os

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

    # TODO: Implement actual email sending (SendGrid, Resend, AWS SES, etc.)
    # For now, just log the email details

    invite_link = f"{get_frontend_url()}/signup?invite={invite_token}"

    logger.info(
        f"""
    =================================
    EMAIL TO SEND:
    =================================
    To: {email}
    Subject: You're invited to join {organisation_name}
    
    Hi there!
    
    {invited_by_name} has invited you to join {organisation_name}.
    
    Click here to accept the invitation: {invite_link}
    
    This invitation will expire in 7 days.
    
    Best regards,
    The Xgaming Nova Team
    =================================
    """
    )

    # Return True for now (simulate success)
    return True


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """Send password reset email (for future use)"""
    # TODO: Implement when password reset feature is needed
    reset_link = f"{get_frontend_url()}/reset-password?token={reset_token}"

    logger.info(
        f"""
    =================================
    PASSWORD RESET EMAIL TO SEND:
    =================================
    To: {email}
    Subject: Reset your Xgaming Nova password
    
    Click here to reset your password: {reset_link}
    =================================
    """
    )
    return True


async def send_welcome_email(email: str, name: str, organisation_name: str) -> bool:
    """Send welcome email after successful signup (for future use)"""
    # TODO: Implement welcome email template

    logger.info(
        f"""
    =================================
    WELCOME EMAIL TO SEND:
    =================================
    To: {email}
    Subject: Welcome to {organisation_name}!
    
    Hi {name},
    
    Welcome to Xgaming Nova! You're now part of {organisation_name}.
    
    Get started: {get_frontend_url()}/console
    =================================
    """
    )
    return True
