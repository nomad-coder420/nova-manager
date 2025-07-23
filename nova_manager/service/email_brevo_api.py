
import requests
import logging
from typing import List, Dict, Optional

from nova_manager.core.config import BREVO_API_KEY

logger = logging.getLogger(__name__)

class EmailService:
    """
    Abstract email service interface. Implementations should provide send_email method.
    """
    def send_email(
        self,
        to: str,
        template_id: int,
        params: Dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        raise NotImplementedError("send_email must be implemented by subclasses")

class BrevoAPIEmailService(EmailService):
    """
    Email service implementation using Brevo (formerly Sendinblue) API.
    """
    def __init__(self, api_key: Optional[str] = None):
        # Use configured API key or provided override
        self.api_key = api_key or BREVO_API_KEY

    def send_email(
        self,
        to: str,
        template_id: int,
        params: Dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send a transactional email using a Brevo template.

        :param to: list of recipient dicts, e.g. [{"email": "a@b.com", "name": "Name"}]
        :param template_id: Brevo template ID to use
        :param params: parameters for the template
        :param headers: optional custom headers
        :return: message ID of the sent email
        :raises ApiException: when API call fails
        """

        url = "https://api.brevo.com/v3/smtp/email"
        # Construct proper payload per Brevo SMTP API
        payload = {
            "templateId": template_id,
            "to": [{"email": to}],
            "params": params
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self.api_key
        }
        response = requests.post(url, json=payload, headers=headers)
        # Log status and body for debugging
        logger.info(f"Brevo API response: {response.status_code} {response.text}")
        # Raise exception on HTTP errors
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Brevo API returned error: {e}")
            raise
        # Parse and return messageId
        data = response.json()
        return data.get("messageId")

email_service: EmailService = BrevoAPIEmailService()