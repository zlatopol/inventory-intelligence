from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings; every field can be overridden via env (12-factor)."""

    database_url: str = "postgresql+psycopg://inventory:inventory@localhost:5432/inventory"
    app_name: str = "Inventory Intelligence"


@lru_cache
def get_settings() -> Settings:
    return Settings()
