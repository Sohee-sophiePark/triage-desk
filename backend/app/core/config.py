from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Triage Desk API"
    DATABASE_URL: str = "sqlite+aiosqlite:///../data/seed.db"

    # Environment configs (development or production)
    ENVIRONMENT: str = "development"

    # Comma-separated list of allowed CORS origins in production
    # e.g. ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
    ALLOWED_ORIGINS: str = ""

    # Required from .env — no default
    SECRET_KEY: str = Field(min_length=32)  # JWT signing key
    ALGORITHM: str = "HS256"

    # Rate limiting
    RATE_LIMIT_DEFAULT_RPM: int = 60
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_LOGIN_WINDOW: int = 900  # 15 minutes

    # Account lockout (SC-01 / A07)
    ACCOUNT_LOCKOUT_THRESHOLD: int = 10   # lock after N failed attempts
    ACCOUNT_LOCKOUT_DURATION: int = 1800  # 30 minutes in seconds

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        if self.ENVIRONMENT == "development":
            return 1440 # 24 hours
        return 15  # 15 minutes

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
