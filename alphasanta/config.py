"""Configuration loading for AlphaSanta."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("ALPHASANTA_LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("ALPHASANTA_LLM_MODEL", "claude-haiku-4-5-20251001")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    desearch_api_key: str = os.getenv("DESEARCH_API_KEY", "")

    neofs_enabled: bool = _env_bool("ALPHASANTA_NEOFS_ENABLED", True)
    neofs_container_id: str = os.getenv("NEOFS_CONTAINER_ID", "")
    neofs_gateway_url: str = os.getenv("NEOFS_GATEWAY_URL", "")

    twitter_enabled: bool = _env_bool("ALPHASANTA_TWITTER_ENABLED", False)
    telegram_enabled: bool = _env_bool("ALPHASANTA_TELEGRAM_ENABLED", False)

    database_url: str = os.getenv("ALPHASANTA_DATABASE_URL", "sqlite:///alphasanta.db")

    queue_maxsize: int = _env_int("ALPHASANTA_QUEUE_MAXSIZE", 0)
    rate_limit_per_min: int = _env_int("ALPHASANTA_RATE_LIMIT_PER_MIN", 60)

    turnkey_base_url: str = os.getenv("TURNKEY_BASE_URL", "")
    turnkey_public_key: str = os.getenv("TURNKEY_API_PUBLIC_KEY", "")
    turnkey_private_key: str = os.getenv("TURNKEY_API_PRIVATE_KEY", "")
    turnkey_org_id: str = os.getenv("TURNKEY_ORG_ID", "")

    elf_transport: str = os.getenv("ALPHASANTA_ELF_TRANSPORT", "local").lower()
    a2a_micro_url: str = os.getenv("ALPHASANTA_A2A_MICRO_URL", "")
    a2a_mood_url: str = os.getenv("ALPHASANTA_A2A_MOOD_URL", "")
    a2a_macro_url: str = os.getenv("ALPHASANTA_A2A_MACRO_URL", "")
    a2a_timeout: float = _env_float("ALPHASANTA_A2A_TIMEOUT_SECONDS", 45.0)

    def turnkey_enabled(self) -> bool:
        return all([self.turnkey_base_url, self.turnkey_public_key, self.turnkey_private_key, self.turnkey_org_id])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
