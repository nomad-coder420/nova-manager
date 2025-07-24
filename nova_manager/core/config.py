import os
from os import getenv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


DATABASE_URL = getenv("DATABASE_URL") or ""
GCP_PROJECT_ID = getenv("GCP_PROJECT_ID") or ""
GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS") or ""
BIGQUERY_DATASET_NAME = getenv("BIGQUERY_DATASET_NAME") or ""
BIGQUERY_RAW_EVENTS_TABLE_NAME = getenv("BIGQUERY_RAW_EVENTS_TABLE_NAME") or ""
# This key is for signing JWTs.
# It's crucial that this is a strong, randomly-generated secret
# and that it is NOT hardcoded in production.
# Use environment variables to set this value.
SECRET_KEY = getenv("SECRET_KEY") or "a-very-secret-key-that-is-not-secret"
DEBUG = getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Brevo (Sendinblue) API key for transactional emails
BREVO_API_KEY = getenv("BREVO_API_KEY") or ""

# Base URL for generating absolute links (e.g., invitations)
BASE_URL = getenv("BASE_URL") or ""
# Frontend URL for redirects after invitation acceptance
FRONTEND_URL = getenv("FRONTEND_URL") or "http://localhost:3000"
# Default template ID for invitation emails (Brevo)
APP_INVITE_TEMPLATE_ID = int(getenv("APP_INVITE_TEMPLATE_ID") or "1")
ORG_INVITE_TEMPLATE_ID = int(getenv("ORG_INVITE_TEMPLATE_ID") or "2")
