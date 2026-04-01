from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fake Content Detection Assistant"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model: str = "gemini-2.5-flash"

    sightengine_user: str = Field(..., alias="SIGHTENGINE_USER")
    sightengine_secret: str = Field(..., alias="SIGHTENGINE_SECRET")

    request_timeout_seconds: float = 45.0
    max_download_bytes: int = 10 * 1024 * 1024
    max_image_dimension: int = 1568

    cors_origins_raw: str = Field(default="*", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("cors_origins_raw")
    @classmethod
    def normalize_cors_origins(cls, value: str) -> str:
        return value.strip() or "*"

    @property
    def cors_origins(self) -> List[str]:
        if self.cors_origins_raw == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
