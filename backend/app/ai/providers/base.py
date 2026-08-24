from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from app.ai.schemas import LLMRawResponse

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Provider-agnostic interface. Agents must never call HTTP or hold API keys."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> LLMRawResponse:
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """Cheap connectivity check. Must not expose secrets."""
        ...
