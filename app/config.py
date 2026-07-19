"""Application configuration via environment variables."""
import json
import os
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # WhatsApp Cloud API
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "nisha_salon_verify"
    whatsapp_api_version: str = "v21.0"

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # Google Sheets
    google_sheet_id: str = ""
    google_sheets_credentials_json: str = ""

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    max_conversation_history: int = 20
    salon_database_url: str = "sqlite+aiosqlite:///./nisha_salon.db"

    @property
    def whatsapp_api_base_url(self) -> str:
        return f"https://graph.facebook.com/{self.whatsapp_api_version}"

    @property
    def google_sheets_credentials(self) -> Optional[dict]:
        """Parse service account JSON from env var."""
        if not self.google_sheets_credentials_json:
            return None
        try:
            return json.loads(self.google_sheets_credentials_json)
        except json.JSONDecodeError:
            return None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
