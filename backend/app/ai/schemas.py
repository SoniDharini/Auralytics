"""Shared AI / LLM types. Agents consume these; they never talk to xAI directly."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class LLMRawResponse(BaseModel):
    content: str
    model: Optional[str] = None
    usage: Optional[LLMUsage] = None
    finish_reason: Optional[str] = None
    provider: str = "groq"
    latency_ms: Optional[float] = None


class LLMGenerateRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    temperature: float = 0.2
    max_tokens: int = 4096
    response_schema: Optional[Type[BaseModel]] = Field(default=None, exclude=True)

    model_config = {"arbitrary_types_allowed": True}


class AIStatusResponse(BaseModel):
    provider: str = "groq"
    configured: bool
    reachable: bool
    model_configured: bool
    model: Optional[str] = None
    detail: Optional[str] = None


class AgentResultEnvelope(BaseModel):
    """Generic envelope used by AgentExecutionService responses."""

    status: str
    summary: str
    confidence: Optional[float] = None
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = None
    model: Optional[str] = None
    provider_latency_ms: Optional[float] = None
    grok_called: bool = False
