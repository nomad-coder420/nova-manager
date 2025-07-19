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
