"""Application configuration.

Centralises environment-driven settings for the CBSA Python port. Values can
be overridden by environment variables prefixed with ``CBSA_``.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CBSA_", case_sensitive=False)

    database_url: str = "sqlite:///./cbsa.db"
    company_name: str = "CICS Bank Sample Application"
    sort_code: str = "987654"


def get_settings() -> Settings:
    return Settings()
