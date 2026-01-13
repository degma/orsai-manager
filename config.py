import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///instance/app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TELEGRAM_INGEST_SECRET = os.environ.get("TELEGRAM_INGEST_SECRET")
    TELEGRAM_ADMIN_IDS = os.environ.get("TELEGRAM_ADMIN_IDS", "")
