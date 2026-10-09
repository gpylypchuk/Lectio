from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SecretStr masks the key in reprs, logs and tracebacks.
    anthropic_api_key: SecretStr
    # Not a secret, so a safe default saves setting it in every environment.
    llm_model: str = "claude-haiku-4-5-20251001"
    # Per HTTP request. The SDK default of 600 s is far too long for a synchronous API.
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    # SDK retries on transient errors. Each of our validation attempts can make 1 + this many calls.
    llm_max_retries: int = Field(default=2, ge=0)
    # Bounds the whole analysis, because SDK retries honor retry-after with no practical cap.
    # Keep it below the Cloud Run request timeout so the client gets a clean 503.
    llm_deadline_seconds: float = Field(default=90.0, gt=0)
    # Abuse protection for the public service. Every accepted analysis spends API credits (D19).
    rate_limit_per_ip: int = Field(default=5, ge=1)
    rate_limit_total: int = Field(default=30, ge=1)
    rate_limit_window_seconds: float = Field(default=3600.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once; tests replace it via dependency_overrides.
    return Settings()
