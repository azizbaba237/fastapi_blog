"""
Configuration Module

Loads application settings from environment variables (via a .env file) using
Pydantic Settings. All sensitive values (e.g., secret_key) are stored securely
using SecretStr to prevent accidental exposure in logs or traces.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.

    Attributes:
        secret_key (SecretStr): The secret key used for signing JWT tokens.
            Must be kept secure and never hard-coded.
        algorithm (str): The cryptographic algorithm used for JWT signing.
            Defaults to "HS256" (HMAC with SHA-256).
        access_token_expire_minutes (int): The lifetime of JWT access tokens in minutes.
            Defaults to 30 minutes.
    """

    # --- Pydantic Settings Configuration ---
    # Instructs Pydantic to load values from a .env file (UTF-8 encoded)
    # and map them to the class attributes defined below.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore les variables d'environnement en trop si présent
    )

    # --- JWT Security Settings ---
    secret_key: SecretStr
    """The secret key used for signing JWT tokens. Read from the SECRET_KEY env variable."""

    algorithm: str = "HS256"
    """The JWT signing algorithm. Defaults to HS256."""

    access_token_expire_minutes: int = 30
    """Token expiration time in minutes. Defaults to 30 minutes."""
    
    # --- Database Settings ---
    database_url: str = "sqlite+aiosqlite:///./blog.db"
    
    # --- File Upload Settings ---
    max_upload_size_bytes: int  = 5 * 1024 * 1024  # 5 MB


# --- Singleton instance for use across the application ---
settings = Settings()