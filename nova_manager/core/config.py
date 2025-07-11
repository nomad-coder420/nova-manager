import os
from os import getenv
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


DATABASE_URL = getenv("DATABASE_URL") or ""
