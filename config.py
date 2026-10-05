"""
==============================================================================
MODULE: config.py
DESCRIPTION: Centralized configuration management for the Expiry Tracker System.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
In a production-ready application, configuration should follow the Twelve-Factor
App methodology (https://12factor.net/config). We strictly decouple code from
configuration by:
1. Sourcing sensitive runtime values (passwords, API tokens) from the environment.
2. Providing a graceful fallback chain: System Env -> .env file -> Sensible Defaults.
3. Defining explicit data structures (dataclasses / pydantic) to ensure typing.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Locate and load the '.env' file from the project root directory
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Explicitly load .env file if it exists, without overriding existing OS env vars
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Configuration parameters for PostgreSQL persistence layer with psycopg2-binary.
    Includes an automatic fallback switch for local offline developer testing.
    """
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "postgres")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    fallback_to_sqlite: bool = os.getenv("FALLBACK_TO_SQLITE", "true").lower() in ("true", "1", "yes")

    @property
    def connection_string(self) -> str:
        """
        Builds a standard PostgreSQL connection DSN string if database_url is omitted.
        """
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class GeminiConfig:
    """
    Configuration parameters for the Google Gemini AI extraction engine.
    Leverages the official 'google-genai' SDK on the free tier.
    """
    api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    model_name: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-placeholder Gemini API key is available."""
        return bool(self.api_key) and not self.api_key.startswith("your_")


@dataclass(frozen=True)
class LifespanConfig:
    """
    Lifespan calculation rules and threshold boundaries.
    Equation: Days Remaining = Expiry Date - Current Date.
    Boundaries:
      - EXPIRED:     Days Remaining <= 0
      - NEAR EXPIRY: 0 < Days Remaining <= threshold_days
      - SAFE:        Days Remaining > threshold_days
    """
    threshold_days: int = int(os.getenv("EXPIRY_THRESHOLD_DAYS", "30"))


@dataclass(frozen=True)
class AlertConfig:
    """
    Alert dispatch and simulation parameters.
    """
    manager_email: str = os.getenv("MANAGER_ALERT_EMAIL", "inventory-manager@store.internal")
    sender_email: str = os.getenv("ALERT_SENDER_EMAIL", "alerts@inventory-system.internal")
    log_file: Path = BASE_DIR / os.getenv("ALERT_LOG_FILE", "alerts.log")


# Global instances of configurations for easy import across modules
db_config = DatabaseConfig()
gemini_config = GeminiConfig()
lifespan_config = LifespanConfig()
alert_config = AlertConfig()
