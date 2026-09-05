import base64
import logging
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


class Config:
    AUTH_LOGIN_RATE_LIMIT = "5 per 15 minutes"
    MFA_ISSUER_NAME = "InfraManager"
    MFA_PENDING_TTL_SECONDS = 300
    MFA_SETUP_RATE_LIMIT = "5 per 10 minutes"
    MFA_DISABLE_RATE_LIMIT = "5 per 15 minutes"
    MFA_ENCRYPTION_KEY = os.getenv("MFA_ENCRYPTION_KEY")
    MFA_VERIFY_RATE_LIMIT = "5 per 5 minutes"
    MAX_CONTENT_LENGTH = 64 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SECURITY_ALERT_WINDOW_MINUTES = 15
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_PERMANENT = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    SQLALCHEMY_DATABASE_URI = "sqlite:///inframanager.db"


class TestingConfig(Config):
    LOG_LEVEL = logging.WARNING
    MFA_ENCRYPTION_KEY = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("ascii")
    RATELIMIT_ENABLED = False
    SECRET_KEY = "testing-only-secret-key"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = logging.INFO
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


CONFIGURATIONS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
