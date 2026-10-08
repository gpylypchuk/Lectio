from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SecretStr masks the key in reprs, logs and tracebacks.
    anthropic_api_key: SecretStr
    # Not a secret, so a safe default saves setting it in every environment.
    llm_model: str = "claude-haiku-4-5-20251001"


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once; tests replace it via dependency_overrides.
    return Settings()
