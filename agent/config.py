"""Runtime settings for the agent, sourced from environment variables (+ optional .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # dev-only dependency
    except Exception:
        return
    env = REPO_ROOT / ".env"
    if env.exists():
        load_dotenv(env)


_load_dotenv()


def _flag(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() not in ("0", "false", "no", "off", "")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


@dataclass
class Settings:
    provider: str
    model: str | None
    max_iters: int
    max_tool_calls: int
    max_new_entries: int
    max_per_task: int
    max_tokens: int
    wall_clock_seconds: int
    hf_token: str | None
    github_token: str | None
    enable_civitai: bool
    enable_pwc: bool


def load_settings() -> Settings:
    return Settings(
        provider=(os.environ.get("LLM_PROVIDER") or "gemini").lower(),
        model=os.environ.get("LLM_MODEL") or None,
        max_iters=_int("AGENT_MAX_ITERS", 12),
        max_tool_calls=_int("AGENT_MAX_TOOL_CALLS", 40),
        max_new_entries=_int("AGENT_MAX_NEW_ENTRIES", 40),
        max_per_task=_int("AGENT_MAX_PER_TASK", 5),
        max_tokens=_int("AGENT_MAX_TOKENS", 200_000),
        wall_clock_seconds=_int("AGENT_WALL_CLOCK_SECONDS", 1200),
        hf_token=os.environ.get("HF_TOKEN") or None,
        github_token=os.environ.get("GITHUB_TOKEN") or None,
        enable_civitai=_flag("AGENT_ENABLE_CIVITAI", True),
        enable_pwc=_flag("AGENT_ENABLE_PWC", False),  # paperswithcode.co is 403/anti-bot
    )
