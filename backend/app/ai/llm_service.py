"""Central LLM service — all agents share one Grok provider instance."""

from __future__ import annotations

from typing import Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from app.ai.providers.grok import GrokProvider, parse_structured
from app.ai.schemas import AIStatusResponse, LLMRawResponse
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

_provider: Optional[GrokProvider] = None


def get_grok_provider() -> GrokProvider:
    global _provider
    if _provider is None:
        _provider = GrokProvider()
    return _provider


def reset_grok_provider() -> None:
    """Test helper to clear the singleton."""
    global _provider
    _provider = None


class LLMService:
    def __init__(self, provider: Optional[GrokProvider] = None) -> None:
        self.provider = provider or get_grok_provider()

    def is_configured(self) -> bool:
        return self.provider.is_configured()

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> LLMRawResponse:
        return await self.provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_model=response_model,
        )

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> T:
        parsed, _raw = await self.generate_structured_with_meta(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return parsed

    async def generate_structured_with_meta(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Tuple[T, LLMRawResponse]:
        raw = await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_model=response_model,
        )
        return parse_structured(raw.content, response_model), raw

    async def status(self, *, probe: bool = True) -> AIStatusResponse:
        configured = self.is_configured()
        model_name = settings.llm_model
        model_configured = bool(model_name)
        reachable = False
        detail: Optional[str] = None
        if not configured:
            detail = "GROQ_API_KEY is missing"
        elif probe:
            reachable = await self.provider.ping()
            if not reachable:
                detail = "Configured but unreachable"
        return AIStatusResponse(
            provider="groq",
            configured=configured,
            reachable=reachable,
            model_configured=model_configured,
            model=model_name if model_configured else None,
            detail=detail,
        )
