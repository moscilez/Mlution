from functools import lru_cache
from pydantic import model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    database_url: str = "postgresql+psycopg://mlution:mlution-local-only@localhost:5433/mlution"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"
    cookie_secure: bool = False
    max_upload_size_mb: int = Field(default=25, ge=1, le=100)
    max_rows: int = Field(default=100000, ge=1, le=100000)
    max_columns: int = Field(default=200, ge=2, le=200)
    max_experiments: int = Field(default=6, ge=1, le=6)
    default_time_budget_seconds: int = Field(default=180, ge=30, le=600)
    redis_url: str = "redis://localhost:6379/0"
    job_mode: str = "redis"
    demo_enabled: bool = True
    seed_demo: bool = False
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.environment == "production":
            if len(self.jwt_secret) < 32 or not self.cookie_secure or self.demo_enabled:
                raise ValueError(
                    "Production requires JWT_SECRET (32+ characters), COOKIE_SECURE=true and DEMO_ENABLED=false"
                )
            if self.job_mode != "redis":
                raise ValueError("Production requires Redis jobs")
        if self.job_mode not in {"redis", "inline"}:
            raise ValueError("JOB_MODE must be redis or inline")
        if self.jwt_algorithm != "HS256":
            raise ValueError("Only HS256 is supported")
        if self.environment != "test" and not self.database_url.startswith("postgresql"):
            raise ValueError("DATABASE_URL must use PostgreSQL")
        return self


@lru_cache
def get_settings():
    return Settings()
