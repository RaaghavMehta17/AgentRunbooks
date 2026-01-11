from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    llm_provider: str = os.getenv("LLM_PROVIDER", "stub")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    cost_model: str = os.getenv("COST_MODEL", "openai_gpt-4o")
    token_price_input_usd: float = float(os.getenv("TOKEN_PRICE_INPUT_USD", "0.000005"))
    token_price_output_usd: float = float(os.getenv("TOKEN_PRICE_OUTPUT_USD", "0.000015"))

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = AgentSettings()

