from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки из переменных окружения с префиксом PPU_ (локально читаются из .env)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PPU_")

    bot_token: SecretStr
    admin_chat_id: int
    archive_password: SecretStr
    templates_dir: str = "templates"


@lru_cache
def get_settings() -> Settings:
    return Settings()
