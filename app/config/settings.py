import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = ""
    poll_interval_seconds: int = 60
    db_path: str = str(BASE_DIR / "data" / "alerts_bot.sqlite3")
    sources_path: str = str(BASE_DIR / "data" / "sources.json")
    radar_api_url: str = "https://radar-russia.ru/api/state"
    enable_radar_api: bool = True
    http_timeout_seconds: int = 20
    max_items_per_source: int = 12
    max_notices_per_message: int = 5
    startup_prime_existing: bool = True
    regions_per_page: int = 8
    cities_per_page: int = 10
    admin_ids: str = ""


settings = Settings()
