"""Shared LLM HTTP client (Groq OpenAI-compatible chat completions)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.providers.base import LLMProvider
from app.ai.schemas import LLMRawResponse, LLMUsage
from app.core.config import settings
from app.core.exceptions import AINotConfiguredException, AIProviderException

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
T = TypeVar("T", bound=BaseModel)

# Verbose JSON Schema keys inflate Groq prompts and can trigger HTTP 413
# (Groq uses 413 when prompt + max_tokens exceeds the model context window).
_SCHEMA_DROP_KEYS = {
    "title",
    "description",
    "examples",
    "deprecated",
    "readOnly",
    "writeOnly",
    "default",
}


def compact_json_schema(schema: Any) -> Any:
    """Keep types/required/$ref only. Full validation still happens in parse_structured."""
    if isinstance(schema, dict):
        out: Dict[str, Any] = {}
        for key, value in schema.items():
            if key in _SCHEMA_DROP_KEYS:
                continue
            out[key] = compact_json_schema(value)
        return out
    if isinstance(schema, list):
        return [compact_json_schema(item) for item in schema]
    return schema


def schema_hint_for_prompt(response_model: Type[BaseModel]) -> str:
    compact = compact_json_schema(response_model.model_json_schema())
    return json.dumps(compact, separators=(",", ":"))


class GrokProvider(LLMProvider):
    name = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.llm_api_key) or ""
        self.api_key = self.api_key.strip()
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout if timeout is not None else settings.AI_REQUEST_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def ping(self) -> bool:
        if not self.is_configured():
            return False
        try:
            raw = await self.generate(
                system_prompt="You are a connectivity probe. Reply with exactly: ok",
                user_prompt="ping",
                temperature=0.0,
                max_tokens=8,
            )
            return bool(raw.content and raw.content.strip())
        except Exception as exc:  # noqa: BLE001 — ping must never raise secrets
            logger.warning("Groq ping failed: %s", type(exc).__name__)
            return False

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> LLMRawResponse:
        if not self.is_configured():
            raise AINotConfiguredException(
                detail="GROQ_API_KEY is not configured. Add it to the backend environment."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if response_model is not None:
            messages[0]["content"] = (
                f"{system_prompt}\n\n"
                "Return ONLY valid JSON that conforms to this JSON Schema. "
                "Do not wrap in markdown. Do not invent factual metrics.\n"
                f"{schema_hint_for_prompt(response_model)}"
            )
            # Groq 413 fires when prompt_tokens + max_tokens exceed the model window.
            max_tokens = min(int(max_tokens), 3072)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_model is not None:
            payload["response_format"] = {"type": "json_object"}

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                data = await self._post_chat(payload)
                content = self._extract_content(data)
                usage_raw = data.get("usage") or {}
                latency_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "[Auralytics AI] Groq response received Latency: %.0fms",
                    latency_ms,
                )
                return LLMRawResponse(
                    content=content,
                    model=data.get("model") or self.model,
                    finish_reason=(data.get("choices") or [{}])[0].get("finish_reason"),
                    usage=LLMUsage(
                        prompt_tokens=usage_raw.get("prompt_tokens"),
                        completion_tokens=usage_raw.get("completion_tokens"),
                        total_tokens=usage_raw.get("total_tokens"),
                    ),
                    provider=self.name,
                    latency_ms=latency_ms,
                )
            except AINotConfiguredException:
                raise
            except AIProviderException as exc:
                last_error = exc
                # Do not retry auth / validation-style failures.
                detail = (exc.detail or "").lower()
                if any(
                    x in detail
                    for x in ("401", "403", "413", "invalid api", "unauthorized", "too large")
                ):
                    raise
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(0.6 * (attempt + 1))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.max_retries:
                    logger.error("Groq generate failed: %s", type(exc).__name__)
                    raise AIProviderException(detail="Groq request failed") from exc
                await asyncio.sleep(0.6 * (attempt + 1))

        raise AIProviderException(detail=f"Groq request failed: {type(last_error).__name__}")

    async def _post_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderException(detail="Groq request timed out") from exc
        except httpx.HTTPError as exc:
            raise AIProviderException(detail="Groq network error") from exc

        if response.status_code in (401, 403):
            raise AIProviderException(detail="Groq authentication failed (check GROQ_API_KEY)")
        if response.status_code == 429:
            raise AIProviderException(detail="Groq rate limit exceeded")
        if response.status_code == 413:
            logger.warning("Groq rejected request as too large (HTTP 413)")
            raise AIProviderException(
                detail="Groq request rejected (413): prompt exceeds the model context window"
            )
        if response.status_code >= 500:
            raise AIProviderException(detail=f"Groq upstream error ({response.status_code})")
        if response.status_code >= 400:
            # Never echo response body — may contain sensitive fragments.
            raise AIProviderException(detail=f"Groq request rejected ({response.status_code})")

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise AIProviderException(detail="Groq returned non-JSON response") from exc

    @staticmethod
    def _extract_content(data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise AIProviderException(detail="Groq returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content or not str(content).strip():
            raise AIProviderException(detail="Groq returned empty content")
        return str(content).strip()


def extract_json_object(text: str) -> Dict[str, Any]:
    """Parse JSON from a model reply, tolerating optional markdown fences."""
    candidate = text.strip()
    fence = _JSON_FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def parse_structured(text: str, model: Type[T]) -> T:
    data = extract_json_object(text)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        logger.error(
            "Groq output failed schema validation for %s: %s | data keys: %s",
            getattr(model, "__name__", str(model)),
            exc.errors(),
            list(data.keys()) if isinstance(data, dict) else type(data),
        )
        first_err = exc.errors()[0] if exc.errors() else {}
        loc = " -> ".join(str(l) for l in first_err.get("loc", []))
        msg = first_err.get("msg", "schema mismatch")
        err_hint = f" ({loc}: {msg})" if loc else ""
        raise AIProviderException(
            detail=f"Groq output failed schema validation: {exc.error_count()} error(s){err_hint}"
        ) from exc
