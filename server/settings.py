import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Defaults are provided for local development.
    """

    PORT: int = 8000
    HOST: str = "0.0.0.0"

    CACHE_TTL: int = 3600
    REQUEST_TIMEOUT: int = 15
    MAX_STREAMS: int = 10

    ENABLE_CACHE: bool = True
    ENABLE_VALIDATION: bool = True
    ENABLE_LOGGING: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()


import logging
import sys
from datetime import datetime


# Setup professional structured logging
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        level = record.levelname
        message = record.getMessage()
        return f"[{timestamp}] [{level}] {message}"


def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

    return logger


logger = get_logger("app")
