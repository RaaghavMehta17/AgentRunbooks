from __future__ import annotations

import json
import os
import time
from typing import Any

from .settings import settings
from .stubs import llm_stub


async def llm_complete(role: str, system: str, user: str) -> dict[str, Any]:
    """Call LLM provider or fallback to stub."""
    provider = settings.llm_provider.lower()
    api_key = None

    if provider == "openai":
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if api_key:
            return await _openai_complete(system, user)
    elif provider == "anthropic" or provider == "claude":
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            return await _anthropic_complete(system, user)

    # Fallback to stub
    return await llm_stub(role, system, user)


async def _openai_complete(system: str, user: str) -> dict[str, Any]:
    """OpenAI API wrapper."""
    try:
        import openai

        start = time.perf_counter()
        response = await openai.AsyncOpenAI(api_key=settings.openai_api_key).chat.completions.create(
            model=settings.cost_model.replace("openai_", ""),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens
        cost = (tokens_in * settings.token_price_input_usd) + (tokens_out * settings.token_price_output_usd)
        return {
            "text": response.choices[0].message.content or "{}",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": elapsed_ms,
            "cost_usd": cost,
        }
    except Exception:
        return await llm_stub("openai", system, user)


async def _anthropic_complete(system: str, user: str) -> dict[str, Any]:
    """Anthropic Claude API wrapper."""
    try:
        import anthropic

        start = time.perf_counter()
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        # Approximate Claude pricing (adjust as needed)
        cost = (tokens_in * 0.000003) + (tokens_out * 0.000015)
        return {
            "text": response.content[0].text if response.content else "{}",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": elapsed_ms,
            "cost_usd": cost,
        }
    except Exception:
        return await llm_stub("anthropic", system, user)

