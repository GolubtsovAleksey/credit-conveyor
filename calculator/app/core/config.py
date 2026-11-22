from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    base_rate: Decimal = Decimal("15.0")
    insurance_cost: Decimal = Decimal("100000")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

"""Создаю единственный экземпляр (объект) настроек при старте приложения"""
settings = Settings()
