from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

ENV_FILE = Path(__file__).with_name(".env")


def load_env(env_file: Path = ENV_FILE) -> None:
    """Simple .env loader (key=value per line, ignores comments)."""
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    target_unique_urls: int = 35
    max_tool_uses: int = 75
    max_search_attempts: int = 6
    claude_cooldown_seconds: int = 20
    content_multiplier: float = 2.0
    mock_mode: bool = False
    audio_enabled: bool = True
    reuse_cached: bool = True
    max_languages: int = 2
    env_file: Path = ENV_FILE


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@lru_cache(maxsize=1)
def get_settings(env_file: Optional[Path] = None) -> Settings:
    load_env(env_file or ENV_FILE)
    return Settings(
        target_unique_urls=_int_env("TARGET_UNIQUE_URLS", Settings.target_unique_urls),
        max_tool_uses=_int_env("MAX_TOOL_USES", Settings.max_tool_uses),
        max_search_attempts=_int_env(
            "MAX_SEARCH_ATTEMPTS", Settings.max_search_attempts
        ),
        claude_cooldown_seconds=_int_env(
            "CLAUDE_COOLDOWN_SECONDS", Settings.claude_cooldown_seconds
        ),
        content_multiplier=_float_env(
            "CONTENT_MULTIPLIER", Settings.content_multiplier
        ),
        mock_mode=_bool_env("MOCK_MODE", Settings.mock_mode),
        audio_enabled=_bool_env("AUDIO_ENABLED", Settings.audio_enabled),
        reuse_cached=_bool_env("REUSE_CACHED", Settings.reuse_cached),
        max_languages=_int_env("MAX_LANGUAGES", Settings.max_languages),
        env_file=env_file or ENV_FILE,
    )

