from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    admin_token: str = "change-me"
    database_path: str = "/app/data/quotes.db"
    user_agent: str = "MusicRefs/1.0 (music-refs-dev.kladriva.ca; contact@kladriva.ca)"
    cors_origins: str = "*"
    rate_limit_per_minute: int = 120
    # MR-08 / MR-14 — Web Push (VAPID). Clés absentes = push désactivé (le service démarre quand même).
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:contact@kladriva.ca"
    push_reminder_hour: int = 19
    push_scheduler_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
