"""Thin wrapper around OpenAI Chat Completions API."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


class LLMClientError(RuntimeError):
    """Raised when an LLM call fails."""


@dataclass(frozen=True)
class LLMConfig:
    model: str = "gpt-4.1-mini"
    temperature: float = 0.3
    max_tokens: int = 4000
    timeout_seconds: int = 120


class OpenAIChatClient:
    def __init__(self, *, api_key: str | None = None, base_url: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientError("Missing OPENAI_API_KEY")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - import guard
            raise LLMClientError(
                "openai package is not installed. Run: pip install -r requirements.txt"
            ) from exc

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        config: LLMConfig,
        retries: int = 2,
    ) -> str:
        last_exc: Exception | None = None

        for attempt in range(retries + 1):
            try:
                response = self._create_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    config=config,
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMClientError("LLM returned empty content")
                return content.strip()
            except Exception as exc:  # pragma: no cover - external API behavior
                last_exc = exc
                if attempt < retries:
                    time.sleep(1.0 + attempt)
                    continue

        raise LLMClientError(f"LLM call failed: {last_exc}") from last_exc

    def _create_completion(self, *, system_prompt: str, user_prompt: str, config: LLMConfig):
        base_kwargs = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": config.temperature,
            "timeout": config.timeout_seconds,
        }

        # Different models/providers may expect either max_tokens or max_completion_tokens.
        token_variants = [
            {"max_completion_tokens": config.max_tokens},
            {"max_tokens": config.max_tokens},
        ]

        token_error: Exception | None = None
        for token_kwargs in token_variants:
            try:
                return self._client.chat.completions.create(
                    **base_kwargs,
                    **token_kwargs,
                )
            except Exception as exc:  # pragma: no cover - provider compatibility handling
                token_error = exc
                message = str(exc).lower()
                if "max_tokens" in message or "max_completion_tokens" in message:
                    continue
                raise

        raise LLMClientError(f"Token parameter negotiation failed: {token_error}")
