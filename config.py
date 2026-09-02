import logging
import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    AUTH_LOGIN_RATE_LIMIT = "5 per 15 minutes"
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    SQLALCHEMY_DATABASE_URI = "sqlite:///inframanager.db"


class TestingConfig(Config):
    LOG_LEVEL = logging.WARNING
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
