"""Agent executor — calls models through OpenRouter / direct APIs.

Reads the routing decision from UnifiedRouter, selects the primary model,
and falls back through the chain on failure.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ExecutionResult:
    tier: str
    model: str
    response: str
    latency_ms: float
    fallback_used: bool = False
    error: str | None = None


# OpenRouter API endpoint
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Direct Anthropic API
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _openrouter_headers() -> dict[str, str]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/antigravity-core",
        "X-Title": "Hermes Zera",
    }


def _anthropic_headers() -> dict[str, str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _call_openrouter(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 128000,
    timeout: float = 180.0,
) -> str:
    """Call a model via OpenRouter chat completions API."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
    }
    resp = httpx.post(
        _OPENROUTER_URL,
        headers=_openrouter_headers(),
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_anthropic_direct(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 128000,
    timeout: float = 180.0,
) -> str:
    """Call Anthropic API directly (for claude models)."""
    # Convert messages to Anthropic format
    anthropic_messages = []
    for msg in messages:
        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

    payload = {
        "model": model,
        "system": system,
        "messages": anthropic_messages,
        "max_tokens": max_tokens,
    }
    resp = httpx.post(
        _ANTHROPIC_URL,
        headers=_anthropic_headers(),
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]


def _execute_model(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 128000,
) -> str:
    """Execute a single model call, routing through the right provider."""
    # If it's a claude model and we have Anthropic key, use direct API
    if model.startswith("anthropic/") or model.startswith("claude"):
        clean_model = model.split("/")[-1] if "/" in model else model
        return _call_anthropic_direct(clean_model, system, messages, max_tokens)

    # Default: OpenRouter
    return _call_openrouter(model, system, messages, max_tokens)


def execute(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 128000,
    fallback_chain: list[str] | None = None,
) -> ExecutionResult:
    """Execute with fallback chain support.

    Args:
        model: primary model identifier
        system: system prompt (SOUL.md content)
        messages: conversation history
        max_tokens: max output tokens
        fallback_chain: list of fallback model identifiers
    """
    fallback_chain = fallback_chain or []
    models_to_try = [model] + fallback_chain

    for i, model_id in enumerate(models_to_try):
        fallback_used = i > 0
        try:
            t0 = time.perf_counter()
            response = _execute_model(model_id, system, messages, max_tokens)
            latency_ms = (time.perf_counter() - t0) * 1000
            return ExecutionResult(
                tier="",  # filled by caller
                model=model_id,
                response=response,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
            )
        except Exception as e:
            error_msg = str(e)
            if i == len(models_to_try) - 1:
                # All models failed
                return ExecutionResult(
                    tier="",
                    model=model_id,
                    response="",
                    latency_ms=0,
                    fallback_used=fallback_used,
                    error=error_msg,
                )
            # Continue to next fallback
            continue

    # Should not reach here, but just in case
    return ExecutionResult(
        tier="",
        model=model,
        response="",
        latency_ms=0,
        fallback_used=False,
        error="No models attempted",
    )
