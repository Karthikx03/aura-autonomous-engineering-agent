"""Central configuration for AURA.

All configuration is sourced from environment variables (or a local .env
file during development). Nothing in this module hard-codes a secret.
Only the provider(s) actually configured with an API key are required —
AURA runs happily with zero LLM keys set by falling back to the
deterministic MockProvider, which keeps the test suite and CI green
without network access or credentials.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "AURA"
    environment: str = "development"
    debug: bool = True

    # --- LLM providers (all optional; only the selected one must be set) ---
    default_llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    google_api_key: str | None = None
    google_model: str = "gemini-1.5-pro"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # --- Persistence ---
    database_url: str = "sqlite+aiosqlite:///./aura.db"
    redis_url: str = "redis://localhost:6379/0"

    # --- Orchestrator ---
    max_iterations: int = 5

    # --- Sandbox ---
    sandbox_enabled: bool = True
    sandbox_cpu_limit: float = 1.0
    sandbox_memory_limit_mb: int = 512
    sandbox_timeout_seconds: int = 60
    sandbox_network_disabled: bool = True
    sandbox_workdir: str = str(Path.home() / ".aura" / "sandboxes")

    # --- Security ---
    security_max_findings_before_block: int = 1

    # --- Observability ---
    log_level: str = "INFO"
    metrics_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
