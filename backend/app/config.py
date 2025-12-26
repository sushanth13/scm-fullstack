from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---------------- Database ----------------
    MONGO_URL: str
    DB_NAME: str

    # ---------------- Auth ----------------
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_SECONDS: int = 604800

    # ---------------- CORS ----------------
    CORS_ORIGIN: str | None = None
    DEV_ALLOW_ALL_ORIGINS: bool = False

    # ---------------- App ----------------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
