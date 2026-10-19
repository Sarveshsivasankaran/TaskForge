"""Application configuration module using Pydantic Settings."""

from typing import List, Union
from pydantic import Field, field_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TaskForge global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Core Application
    app_env: str = Field(default="development", description="Environment: development, test, production")
    app_name: str = Field(default="TaskForge", description="Application Name")
    api_host: str = Field(default="0.0.0.0", description="API Host")
    api_port: int = Field(default=8000, description="API Port")
    debug: bool = Field(default=False, description="Debug mode")

    # CORS
    frontend_url: str = Field(default="http://localhost:5173", description="Frontend Origin")
    cors_allowed_origins: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins"
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Supabase Configuration
    supabase_url: str = Field(
        default="http://localhost:54321",
        validation_alias=AliasChoices("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL", "VITE_SUPABASE_URL"),
        description="Supabase API URL"
    )
    supabase_anon_key: str = Field(
        default="dummy-anon-key",
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "VITE_SUPABASE_ANON_KEY"),
        description="Supabase public anon key"
    )
    supabase_service_role_key: str = Field(default="", description="Supabase privileged service role key")
    supabase_db_url: str = Field(
        default="sqlite+aiosqlite:///./taskforge_dev.db",
        description="SQLAlchemy Database URL"
    )
    supabase_jwt_secret: str = Field(default="taskforge-super-secret-jwt-key-minimum-32-chars", description="JWT secret")

    # Queue Configuration
    queue_name: str = Field(default="taskforge_jobs", description="Queue identifier")
    queue_type: str = Field(default="auto", description="pgmq, table, or auto")
    queue_poll_interval_seconds: float = Field(default=2.0, description="Worker queue polling interval")
    queue_visibility_timeout_seconds: int = Field(default=60, description="Message visibility timeout")

    # Worker & Execution Defaults
    worker_id: str = Field(default="worker-local-1", description="Worker instance ID")
    worker_concurrency: int = Field(default=4, description="Concurrent handler slots")
    worker_heartbeat_interval_seconds: int = Field(default=15, description="Heartbeat refresh interval")
    job_default_timeout_seconds: int = Field(default=300, description="Default job timeout")
    job_default_max_attempts: int = Field(default=5, description="Default maximum retry attempts")
    retry_base_delay_seconds: float = Field(default=2.0, description="Exponential backoff base delay")
    retry_max_delay_seconds: float = Field(default=60.0, description="Exponential backoff max delay")

    # Observability & Elasticsearch
    elasticsearch_url: str = Field(default="http://localhost:9200", description="Elasticsearch cluster URL")
    elasticsearch_api_key: str = Field(default="", description="Elasticsearch API key")
    elasticsearch_index_prefix: str = Field(default="taskforge-logs", description="Index prefix")
    elasticsearch_enabled: bool = Field(default=False, description="Enable Elasticsearch export")

    # AI Failure Investigator
    llm_provider: str = Field(default="nvidia", description="LLM provider: nvidia, openai, anthropic, gemini, mock")
    llm_base_url: str = Field(default="https://integrate.api.nvidia.com/v1", description="LLM base URL")
    llm_model: str = Field(default="openai/gpt-oss-20b", description="LLM model identifier")
    llm_api_key: str = Field(default="", description="LLM API key")



settings = Settings()
