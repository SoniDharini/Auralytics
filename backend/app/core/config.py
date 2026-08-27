from typing import List, Optional, Union
import json
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "InfluenceOS API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./influenceos.db"

    # JWT Authentication
    JWT_SECRET_KEY: str = "default-insecure-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cookie Settings
    REFRESH_COOKIE_NAME: str = "influenceos_refresh_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        return v

    # External Provider Configuration
    YOUTUBE_API_KEY: Optional[str] = None
    YOUTUBE_DISCOVERY_MAX_CREATORS: int = 50
    # search.list costs 100 quota units per call, so this is deliberately small.
    YOUTUBE_MAX_SEARCH_QUERIES: int = 5
    YOUTUBE_RECENT_VIDEO_SAMPLE: int = 8
    DISCOVERY_FINAL_RESULT_LIMIT: int = 20

    INSTAGRAM_APP_ID: Optional[str] = None
    INSTAGRAM_APP_SECRET: Optional[str] = None
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_API_VERSION: str = "v19.0"

    INFLUENCER_CACHE_TTL_HOURS: int = 6

    # Groq Cloud (OpenAI-compatible) — backend only. Never expose to the frontend.
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    # Legacy aliases (still accepted so existing .env files keep working).
    XAI_API_KEY: Optional[str] = None
    XAI_MODEL: Optional[str] = None
    XAI_BASE_URL: Optional[str] = None
    AI_REQUEST_TIMEOUT: float = 60.0
    AI_MAX_RETRIES: int = 2
    # Discovery ranking: explicit backend formula (deterministic + AI fit).
    DISCOVERY_DETERMINISTIC_SCORE_WEIGHT: float = 0.65
    DISCOVERY_AI_FIT_SCORE_WEIGHT: float = 0.35

    @property
    def llm_api_key(self) -> str:
        return (self.GROQ_API_KEY or self.XAI_API_KEY or "").strip()

    @property
    def llm_model(self) -> str:
        return (self.GROQ_MODEL or self.XAI_MODEL or "openai/gpt-oss-120b").strip()

    @property
    def llm_base_url(self) -> str:
        return (self.GROQ_BASE_URL or self.XAI_BASE_URL or "https://api.groq.com/openai/v1").rstrip("/")


settings = Settings()
