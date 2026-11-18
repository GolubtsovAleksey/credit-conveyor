from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict

"""Наследуясь от BaseSettings из библиотеки pydantic-settings, мы наделяем класс способностью автоматически искать переменные в .env
   Имя base_rate автоматически свяжется с BASE_RATE из файла .env"""
class Settings(BaseSettings):
    base_rate: Decimal = Decimal("15.0")
    insurance_cost: Decimal = Decimal("100000")

    """ указал, в каком файле искать переменные (env_file=".env")"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

"""Создаю единственный экземпляр (объект) настроек при старте приложения (аналог Singleton или Spring-бина).
   В других файлах я буду просто импортировать этот готовый объект settings и обращаться к settings.base_rate"""
settings = Settings()
