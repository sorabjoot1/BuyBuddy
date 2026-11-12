"""Terminal entry point."""
from __future__ import annotations

from .config import ConfigError, Settings, require_env


def main() -> None:
    try:
        settings = Settings.load()
        require_env("OPENAI_API_KEY", "OpenAI LLM")
        require_env("TAVILY_API_KEY", "Tavily web search")
        from .crew import ShoppingCrewRunner

        ShoppingCrewRunner(settings).run()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}")
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
