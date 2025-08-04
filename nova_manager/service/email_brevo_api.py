import requests
import logging
from typing import List, Dict, Optional


from nova_manager.core.config import BREVO_API_KEY

logger = logging.getLogger(__name__)

import os, ssl, logging, http.client as http_client, requests, urllib3, sys

# 1. Write TLS session keys for decryption (Wireshark)
os.environ["SSLKEYLOGFILE"] = "./sslkeys.log"

# 2. Enable verbose HTTP and TLS debug in urllib3
http_client.HTTPConnection.debuglevel = 1
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("urllib3").propagate = True

# 3. Print library versions
print("Python:", sys.version)
print("OpenSSL:", ssl.OPENSSL_VERSION)
print("requests:", requests.__version__)
print("urllib3:", urllib3.__version__)

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
            "api-key": self.api_key,
            "User-Agent": "Mozilla/5.0 (compatible; TestClient/1.0)"
        }
        
        # Log request details
        logger.info(f"Brevo API request: URL={url}")
        logger.info(f"Brevo API payload: {payload}")
        logger.info(f"Brevo API headers: {dict(headers)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers,verify=False)
            # Log response details
            logger.info(f"Brevo API response: {response.status_code} {response.text}")
            
            # Raise exception on HTTP errors
            response.raise_for_status()
            
            # Parse and return messageId
            data = response.json()
            message_id = data.get("messageId")
            logger.info(f"Brevo email sent successfully, messageId: {message_id}")
            return message_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Brevo API request failed: {type(e).__name__}: {e}")
            # Only log response details if response exists
            if 'response' in locals():
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response text: {response.text}")
            else:
                logger.error("No response received (connection failed)")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Brevo API call: {type(e).__name__}: {e}")
            raise

    def send_email_with_curl(
        self,
        to: str,
        template_id: int,
        params: Dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send a transactional email using Brevo template via curl subprocess.
        Returns response text (caller can parse messageId if needed).
        """
        import subprocess
        import json
        api_key = self.api_key
        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "templateId": template_id,
            "to": [{"email": to}],
            "params": params
        }
        payload_str = json.dumps(payload)
        curl_cmd = [
            "curl", "-X", "POST", url,
            "-H", f"api-key: {api_key}",
            "-H", "Content-Type: application/json",
            "-H", "User-Agent: Mozilla/5.0 (compatible; TestClient/1.0)",
            "-d", payload_str
        ]
        curl_cmd_str = ' '.join([f'"{c}"' if ' ' in c or c.startswith('-') else c for c in curl_cmd])
        logger.info(f"Brevo curl command: {curl_cmd_str}")

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
            logger.info(f"Brevo curl response: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Brevo curl failed: {e}")
            logger.error(f"stderr: {e.stderr}")
            raise

email_service: EmailService = BrevoAPIEmailService()