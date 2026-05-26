from typing import Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.db_url import normalize_database_url

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "Dushman AI"
    API_V1_STR: str = "/api"
    ENV: str = "development"
    
    # Security
    JWT_SECRET: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str = Field(..., min_length=10)
    SUPABASE_SSL_NO_VERIFY: bool = False

    # Redis / Cache
    REDIS_ENABLED: bool = False
    REDIS_URL: Optional[str] = None
    REDIS_CACHE_TTL_SECONDS: int = 30
    RATE_LIMIT_STORAGE_URL: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list[str] = []

    # Admin bootstrap
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_PRIORITY: int = 9
    
    # LLM Provider Configuration
    # Options: "nvidia", "gemini"
    LLM_PROVIDER: str = Field(..., min_length=3)
    
    # Model Mappings for Nvidia Provider
    NVIDIA_MODEL_DEFAULT: str = "meta/llama-3.1-70b-instruct"
    NVIDIA_MODEL_FAST: str = "meta/llama-3-8b-instruct"
    NVIDIA_MODEL_REASONING: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    
    # Model Mappings for Gemini Provider
    GEMINI_MODEL_DEFAULT: str = "gemini-1.5-flash"
    GEMINI_MODEL_FAST: str = "gemini-1.5-flash"
    GEMINI_MODEL_REASONING: str = "gemini-1.5-pro"
    
    # API Keys
    NVIDIA_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url_value(cls, value: str) -> str:
        if not value:
            return value
        return normalize_database_url(value)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
    
    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        provider = value.lower().strip()
        if provider not in {"nvidia", "gemini"}:
            raise ValueError("LLM_PROVIDER must be one of: nvidia, gemini")
        return provider
    
    @model_validator(mode="after")
    def validate_required_config(self):
        if not self.JWT_SECRET or "change-in-production" in self.JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a secure value.")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be configured.")
        if self.REDIS_ENABLED and not self.REDIS_URL:
            raise ValueError("REDIS_URL must be configured when REDIS_ENABLED=true.")
        if self.LLM_PROVIDER == "nvidia" and not self.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY must be configured when LLM_PROVIDER=nvidia.")
        if self.LLM_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be configured when LLM_PROVIDER=gemini.")
        if self.ENV == "production" and not self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS must be configured in production.")
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
