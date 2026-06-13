"""Provider-agnostic LLM client.

Both Google Gemini and OpenRouter expose an OpenAI-compatible Chat Completions API, so a
single ``openai`` client with a swapped ``base_url`` covers both. The backend is selected by
``LLM_PROVIDER`` and the model by ``LLM_MODEL`` (defaults are intentionally conservative —
never hardcode aspirational version numbers).
"""

from __future__ import annotations

import os

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def _log_retry(state):
    exc = state.outcome.exception() if state.outcome else None
    sleep = getattr(state.next_action, "sleep", 0) if state.next_action else 0
    name = type(exc).__name__ if exc else "error"
    print(f"[llm] {name} (likely rate limit) — backing off {sleep:.0f}s "
          f"(attempt {state.attempt_number}/5)", flush=True)

PROVIDERS = {
    "gemini": dict(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-2.5-flash",
    ),
    "openrouter": dict(
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        default_model="google/gemini-2.5-flash",
    ),
}

_RETRYABLE = (RateLimitError, APIConnectionError, APITimeoutError)


class MissingAPIKey(RuntimeError):
    pass


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        provider = (provider or os.environ.get("LLM_PROVIDER") or "gemini").lower()
        if provider not in PROVIDERS:
            raise ValueError(f"unknown LLM_PROVIDER '{provider}' (expected one of {list(PROVIDERS)})")
        cfg = PROVIDERS[provider]
        key = os.environ.get(cfg["api_key_env"])
        if not key:
            raise MissingAPIKey(f"missing {cfg['api_key_env']} for provider '{provider}'")
        self.provider = provider
        self.model = model or os.environ.get("LLM_MODEL") or cfg["default_model"]
        self.client = OpenAI(base_url=cfg["base_url"], api_key=key)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        stop=stop_after_attempt(5),
        before_sleep=_log_retry,
        reraise=True,
    )
    def chat(self, messages, tools=None, tool_choice="auto", temperature: float = 0.2):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
        )
