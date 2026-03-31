from pathlib import Path 

from pydantic_settings import BaseSettings, SettingsConfigDict 


BACKEND_DIR = Path(__file__).resolve().parent.parent 


class Settings(BaseSettings):
    # ---------------- Database ----------------
    MONGO_URL: str
    DB_NAME: str

    # ---------------- Auth ----------------
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_SECONDS: int = 3600

    # --------------- admin emails ----------------
    ADMIN_EMAILS: str

    # ---------------- CORS ----------------
    CORS_ORIGIN: str | None = None
    DEV_ALLOW_ALL_ORIGINS: bool = False

    # ---------------- App ----------------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8", 
        case_sensitive=True,
        extra="ignore", 
    )


settings = Settings()
