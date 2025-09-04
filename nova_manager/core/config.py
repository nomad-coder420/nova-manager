import os
from os import getenv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)  # don’t overwrite existing OS env vars


DATABASE_URL = getenv("DATABASE_URL") or ""
REDIS_URL = getenv("REDIS_URL") or "redis://localhost:6379/0"
OPENAI_API_KEY = getenv("OPENAI_API_KEY") or ""
GCP_PROJECT_ID = getenv("GCP_PROJECT_ID") or ""
GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS") or ""
BIGQUERY_LOCATION = getenv("BIGQUERY_LOCATION") or "US"
BREVO_API_KEY = getenv("BREVO_API_KEY") or ""
ORG_INVITE_TEMPLATE_ID = int(getenv("ORG_INVITE_TEMPLATE_ID") or "2")
PASSWORD_RESET_TEMPLATE_ID = int(getenv("PASSWORD_RESET_TEMPLATE_ID") or "3")
WELCOME_TEMPLATE_ID = int(getenv("WELCOME_TEMPLATE_ID") or "4")
