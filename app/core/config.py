from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/certificate_generator"
    STORAGE_DIR: str = "./storage"
    MAX_RECIPIENTS_PER_JOB: int = 1000
    LOG_LEVEL: str = "INFO"
    WORKER_POLL_INTERVAL_SECONDS: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


def get_storage_dir() -> Path:
    return Path(settings.STORAGE_DIR).expanduser().resolve()
