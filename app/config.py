import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "english_learning.db"
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
SESSION_EXPIRY_HOURS = 24
HOST = "127.0.0.1"
PORT = 8443
