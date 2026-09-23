from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = Field(default='development', alias='APP_ENV')
    database_url: str = Field(default='sqlite:///./nebula.db', alias='DATABASE_URL')
    telegram_bot_token: str = Field(default='', alias='TELEGRAM_BOT_TOKEN')
    llm_api_key: str = Field(default='', alias='LLM_API_KEY')
    llm_provider: str = Field(default='mock', alias='LLM_PROVIDER')
    llm_model: str = Field(default='mock-router', alias='LLM_MODEL')
    webhook_url: str = Field(default='', alias='WEBHOOK_URL')
    store_name: str = Field(default='Sri Lakshmi Supermarket', alias='STORE_NAME')
    store_gstin: str = Field(default='DEMO-GSTIN', alias='STORE_GSTIN')
    store_address: str = Field(default='Coimbatore, Tamil Nadu', alias='STORE_ADDRESS')
    authorized_telegram_user_ids: str = Field(default='123456789', alias='AUTHORIZED_TELEGRAM_USER_IDS')
    debug: bool = Field(default=False, alias='DEBUG')

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()
