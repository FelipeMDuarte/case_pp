from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["dev", "prod"] = "dev"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "case_pp"

    app_name: str = "case_pp API"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
