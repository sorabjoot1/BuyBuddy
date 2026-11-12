"""Central configuration. All secrets are read from environment variables (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required credential / setting is missing."""


@dataclass(frozen=True)
class Settings:
    openai_model: str
    tavily_search_depth: str
    max_search_results: int
    default_currency: str
    min_options: int
    max_search_attempts: int

    @staticmethod
    def load() -> "Settings":
        return Settings(
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            tavily_search_depth=os.getenv("TAVILY_SEARCH_DEPTH", "basic"),
            max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "8")),
            default_currency=os.getenv("DEFAULT_CURRENCY", "USD"),
            min_options=int(os.getenv("MIN_OPTIONS", "3")),
            max_search_attempts=int(os.getenv("MAX_SEARCH_ATTEMPTS", "3")),
        )


def require_env(name: str, purpose: str) -> str:
    """Return an env var or raise a friendly error telling the user what to set."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing environment variable {name} ({purpose}). "
            f"Copy .env.example to .env and set it."
        )
    return value
