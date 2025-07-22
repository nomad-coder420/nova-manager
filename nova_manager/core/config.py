import os
from os import getenv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


DATABASE_URL = getenv("DATABASE_URL") or ""
REDIS_URL = getenv("REDIS_URL") or "redis://localhost:6379/0"
GCP_PROJECT_ID = getenv("GCP_PROJECT_ID") or ""
GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS") or ""
BIGQUERY_DATASET_NAME = getenv("BIGQUERY_DATASET_NAME") or ""
BIGQUERY_RAW_EVENTS_TABLE_NAME = getenv("BIGQUERY_RAW_EVENTS_TABLE_NAME") or ""
