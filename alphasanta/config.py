"""Configuration loading for AlphaSanta."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict

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


def _parse_agent_id_map(raw: str) -> Dict[str, str]:
    """
    Parse ALPHASANTA_AGENT_ID_MAP env values such as:
    micro:uuid1,mood:uuid2,macro:uuid3,santa:uuid4
    """
    mapping: Dict[str, str] = {}
    if not raw:
        return mapping
    for part in raw.split(","):
        piece = part.strip()
        if not piece or ":" not in piece:
            continue
        key, value = piece.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            mapping[key] = value
    return mapping


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("ALPHASANTA_LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("ALPHASANTA_LLM_MODEL", "claude-haiku-4-5-20251001")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    desearch_api_key: str = os.getenv("DESEARCH_API_KEY", "")

    neofs_enabled: bool = _env_bool("ALPHASANTA_NEOFS_ENABLED", True)
    neofs_container_id: str = os.getenv("NEOFS_CONTAINER_ID", "")
    neofs_gateway_url: str = os.getenv("NEOFS_GATEWAY_URL", "")

    twitter_enabled: bool = _env_bool("ALPHASANTA_TWITTER_ENABLED", True)
    telegram_enabled: bool = _env_bool("ALPHASANTA_TELEGRAM_ENABLED", True)

    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    agent_id_map: Dict[str, str] = field(default_factory=lambda: _parse_agent_id_map(os.getenv("ALPHASANTA_AGENT_ID_MAP", "")))

    queue_maxsize: int = _env_int("ALPHASANTA_QUEUE_MAXSIZE", 0)
    rate_limit_per_min: int = _env_int("ALPHASANTA_RATE_LIMIT_PER_MIN", 60)

    elf_transport: str = os.getenv("ALPHASANTA_ELF_TRANSPORT", "local").lower()
    a2a_micro_url: str = os.getenv("ALPHASANTA_A2A_MICRO_URL", "")
    a2a_mood_url: str = os.getenv("ALPHASANTA_A2A_MOOD_URL", "")
    a2a_macro_url: str = os.getenv("ALPHASANTA_A2A_MACRO_URL", "")
    a2a_timeout: float = _env_float("ALPHASANTA_A2A_TIMEOUT_SECONDS", 45.0)

    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
