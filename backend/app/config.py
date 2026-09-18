from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Zentrale Anwendungseinstellungen (aus .env / Umgebungsvariablen)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anwendung
    APP_NAME: str = "Enterprise AI Platform"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Datenbank
    DATABASE_URL: str = "postgresql+psycopg2://enterprise_ai:change_me_db_password@localhost:5432/enterprise_ai"

    # Sicherheit
    JWT_SECRET_KEY: str = "CHANGE_ME_TO_A_RANDOM_SECRET"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    SESSION_TTL_HOURS: int = 24
    MAX_HISTORY_MESSAGES: int = 40

    # Datenschutz
    CHAT_RETENTION_DAYS: int = 30

    # CORS (kommaseparierte Liste)
    CORS_ORIGINS: str = "http://localhost:3000"

    # AWS / Bedrock
    AWS_REGION: str = "eu-central-1"
    BEDROCK_DEFAULT_MODEL_ID: str = "eu.anthropic.claude-3-5-sonnet-20241022-v2:0"
    # Mock-Modus: true = lokale Antwort-Simulation ohne AWS (Entwicklung/CI)
    MOCK_BEDROCK: bool = True

    # Seed
    SEED_ON_START: bool = False
    SEED_ADMIN_EMAIL: str = "admin@example.com"
    SEED_ADMIN_PASSWORD: str = "change_me_admin_password"
    SEED_DEMO_USER_EMAIL: str = "fabio@example.com"
    SEED_DEMO_USER_PASSWORD: str = "change_me_demo_password"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
