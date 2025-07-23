import logging
from typing import List, Dict, Optional

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from nova_manager.core.config import BREVO_API_KEY

logger = logging.getLogger(__name__)

class EmailService:
    """
    Abstract email service interface. Implementations should provide send_email method.
    """
    def send_email(
        self,
        to: List[Dict[str, str]],
        template_id: int,
        params: Dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        raise NotImplementedError("send_email must be implemented by subclasses")

class BrevoEmailService(EmailService):
    """
    Email service implementation using Brevo (formerly Sendinblue) API.
    """
    def __init__(self, api_key: Optional[str] = None):
        # Use configured API key or provided override
        self.api_key = api_key or BREVO_API_KEY
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = self.api_key
        self.client = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    def send_email(
        self,
        to: List[Dict[str, str]],
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
        message = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            template_id=template_id,
            params=params,
            headers=headers or {},
        )
        try:
            response = self.client.send_transac_email(message)
            # SDK converts JSON keys to snake_case attributes
            message_id = getattr(response, 'message_id', None)
            logger.info(f"Email sent successfully, message_id={message_id}")
            return message_id
        except ApiException as e:
            logger.error(f"Failed to send email via Brevo: {e}")
            raise

# Default email service instance
email_service: EmailService = BrevoEmailService()
