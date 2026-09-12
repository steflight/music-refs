from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    admin_token: str = "change-me"
    database_path: str = "/app/data/quotes.db"
    user_agent: str = "MusicRefs/1.0 (music-refs-dev.kladriva.ca; contact@kladriva.ca)"
    cors_origins: str = "*"
    rate_limit_per_minute: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
