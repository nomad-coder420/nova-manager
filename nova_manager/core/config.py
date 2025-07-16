import os
from os import getenv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


DATABASE_URL = getenv("DATABASE_URL") or ""
# This key is for signing JWTs.
# It's crucial that this is a strong, randomly-generated secret
# and that it is NOT hardcoded in production.
# Use environment variables to set this value.
SECRET_KEY = getenv("SECRET_KEY") or "a-very-secret-key-that-is-not-secret"
