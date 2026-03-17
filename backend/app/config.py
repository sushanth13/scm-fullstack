from pathlib import Path # For handling file paths (used to locate .env file relative to this config.py file)

from pydantic_settings import BaseSettings, SettingsConfigDict # For application configuration management using Pydantic (allows defining settings with type validation, default values, and loading from environment variables or .env files)


BACKEND_DIR = Path(__file__).resolve().parent.parent # Get parent directory of current file (backend/app/config.py) → backend


class Settings(BaseSettings):
    # ---------------- Database ----------------
    MONGO_URL: str
    DB_NAME: str

    # ---------------- Auth ----------------
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_SECONDS: int = 3600

    # ---------------- CORS ----------------
    CORS_ORIGIN: str | None = None
    DEV_ALLOW_ALL_ORIGINS: bool = False

    # ---------------- App ----------------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8", # Ensure .env is read as UTF-8 (important for special characters in secrets, etc.)
        case_sensitive=True,
        extra="ignore", # Ignore extra environment variables that are not defined in this Settings class (prevents errors if there are unrelated env vars in the environment)
    )


settings = Settings()
