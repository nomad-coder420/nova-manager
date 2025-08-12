import requests
import logging
from typing import List, Dict, Optional, Tuple
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
    ) -> Tuple[bool, Optional[str]]:
        """
        Send email and return success status with optional error message.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        raise NotImplementedError("send_email must be implemented by subclasses")

class BrevoAPIEmailService(EmailService):
    """
    Email service implementation using Brevo (formerly Sendinblue) API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or BREVO_API_KEY
        if not self.api_key:
            logger.error("Brevo API key is not configured")

    def send_email(
        self,
        to: str,
        template_id: int,
        params: Dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a transactional email using a Brevo template.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
            - (True, None) on success
            - (False, error_message) on failure
        """
        if not self.api_key:
            error_msg = "Brevo API key is not configured"
            logger.error(error_msg)
            return False, error_msg

        url = "https://api.brevo.com/v3/smtp/email"
        
        payload = {
            "templateId": template_id,
            "to": [{"email": to}],
            "params": params
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self.api_key,
            "User-Agent": "Mozilla/5.0 (compatible; TestClient/1.0)"
        }

        logger.info(f"Attempting to send email via Brevo API to: {to}")
        logger.debug(f"Brevo API payload: {payload}")

        try:
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=30)
            
            # Log response for debugging
            logger.debug(f"Brevo API response: {response.status_code} {response.text}")

            if response.status_code == 201:  # Brevo returns 201 for successful email
                data = response.json()
                message_id = data.get("messageId")
                logger.info(f"Email sent successfully, messageId: {message_id}")
                return True, None
            else:
                # Handle API errors (400, 401, 403, etc.)
                error_msg = f"Brevo API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = "Email service timeout - request took too long"
            logger.error(error_msg)
            return False, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "Email service connection error - unable to connect to Brevo API"
            logger.error(error_msg)
            return False, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Email service request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error in email service: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

email_service: EmailService = BrevoAPIEmailService()
