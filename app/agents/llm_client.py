"""OpenAI-SDK LLM client with .env configuration, timeouts, and provider fallback.

Uses one OpenAI SDK interface (`AsyncOpenAI`) across Groq (`openai/gpt-oss-120b`),
Gemini Flash (OpenAI-compatible endpoint), Sarvam-105B, and OpenAI. Falls back
to the next configured provider on HTTP 429, 5xx, timeout, or connection errors.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import openai
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.config import settings

logger = logging.getLogger("krishi.llm")


class LLMUnavailableError(RuntimeError):
    """Raised when no configured provider succeeds after fallback."""


@dataclass(frozen=True)
class ProviderConfig:
    """One OpenAI-compatible chat-completions endpoint."""

    name: str
    base_url: str
    api_key: str
    model: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMToolCall:
    """Normalized function call emitted by a provider."""

    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str = "{}"


@dataclass
class LLMResponse:
    """Normalized response from one LLM completion call."""

    content: Optional[str]
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    usage: dict[str, Any] = field(default_factory=dict)


class ILLMClient(ABC):
    """Provider-swappable interface consumed by `AgentEngine`."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        temperature: float = 0.2,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
    ) -> LLMResponse: ...


def _env_or_setting(env_key: str, default: Any = "") -> Any:
    val = os.getenv(env_key)
    if val is not None:
        cleaned = str(val).strip()
        return "" if cleaned.startswith("#") else cleaned
    sval = getattr(settings, env_key, default)
    if isinstance(sval, str) and sval.strip().startswith("#"):
        return default
    return sval


def _provider_defaults(name: str) -> Optional[ProviderConfig]:
    key = name.strip().lower()
    if key == "groq":
        api_key = str(_env_or_setting("GROQ_API_KEY", ""))
        model = str(_env_or_setting("GROQ_MODEL", "openai/gpt-oss-120b"))
        base_url = str(_env_or_setting("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
        extra: dict[str, Any] = {}
        effort = str(_env_or_setting("LLM_REASONING_EFFORT", "low")).strip()
        if "gpt-oss" in model and effort:
            extra["reasoning_effort"] = effort
        return ProviderConfig(name="groq", base_url=base_url, api_key=api_key, model=model, extra=extra)
    if key == "gemini":
        return ProviderConfig(
            name="gemini",
            base_url=str(_env_or_setting("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")),
            api_key=str(_env_or_setting("GEMINI_API_KEY", "")),
            model=str(_env_or_setting("GEMINI_MODEL", "gemini-2.5-flash")),
        )
    if key == "sarvam":
        return ProviderConfig(
            name="sarvam",
            base_url=str(_env_or_setting("SARVAM_LLM_BASE_URL", "https://api.sarvam.ai/v1")),
            api_key=str(_env_or_setting("SARVAM_API_KEY", "")),
            model=str(_env_or_setting("SARVAM_LLM_MODEL", "sarvam-105b")),
        )
    if key == "openai":
        return ProviderConfig(
            name="openai",
            base_url=str(_env_or_setting("OPENAI_BASE_URL", "https://api.openai.com/v1")),
            api_key=str(_env_or_setting("OPENAI_API_KEY", "")),
            model=str(_env_or_setting("OPENAI_MODEL", "gpt-4o-mini")),
        )
    return None


def build_provider_chain() -> list[ProviderConfig]:
    """Assemble ordered primary + fallback providers from env/settings.

    Explicit `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` overrides the primary
    entry; remaining entries in `LLM_FALLBACK_CHAIN` act as automatic fallbacks
    whenever their API keys are configured.
    """
    primary_name = str(_env_or_setting("LLM_PROVIDER", "groq")).strip().lower()
    chain_raw = str(_env_or_setting("LLM_FALLBACK_CHAIN", "groq,gemini,sarvam,openai"))
    ordered_names: list[str] = [primary_name]
    for item in chain_raw.split(","):
        p = item.strip().lower()
        if p and p not in ordered_names:
            ordered_names.append(p)

    custom_base = str(_env_or_setting("LLM_BASE_URL", "")).strip()
    custom_model = str(_env_or_setting("LLM_MODEL", "")).strip()
    custom_key = str(_env_or_setting("LLM_API_KEY", "")).strip()

    configs: list[ProviderConfig] = []
    for idx, pname in enumerate(ordered_names):
        cfg = _provider_defaults(pname)
        if cfg is None:
            continue
        if idx == 0 and (custom_base or custom_model or custom_key):
            model = custom_model or cfg.model
            extra = dict(cfg.extra)
            if "gpt-oss" not in model:
                extra.pop("reasoning_effort", None)
            cfg = ProviderConfig(
                name=cfg.name,
                base_url=custom_base or cfg.base_url,
                api_key=custom_key or cfg.api_key,
                model=model,
                extra=extra,
            )
        if cfg.api_key:
            configs.append(cfg)
            if pname == "groq" and not custom_model:
                extra_models = str(_env_or_setting("GROQ_FALLBACK_MODELS", "") or "")
                for em in extra_models.split(","):
                    m_name = em.strip()
                    if not m_name or m_name == cfg.model:
                        continue
                    em_extra: dict[str, Any] = {}
                    effort = str(_env_or_setting("LLM_REASONING_EFFORT", "low")).strip()
                    if "gpt-oss" in m_name and effort:
                        em_extra["reasoning_effort"] = effort
                    configs.append(
                        ProviderConfig(
                            name=f"groq:{m_name}",
                            base_url=cfg.base_url,
                            api_key=cfg.api_key,
                            model=m_name,
                            extra=em_extra,
                        )
                    )
    return configs


def _parse_arguments(raw: Any) -> tuple[dict[str, Any], str]:
    if isinstance(raw, dict):
        return raw, json.dumps(raw, ensure_ascii=False)
    text = str(raw or "{}").strip()
    if not text:
        return {}, "{}"
    try:
        parsed = json.loads(text)
        return (parsed if isinstance(parsed, dict) else {}), text
    except json.JSONDecodeError:
        return {}, text


def _is_retryable_status(exc: APIStatusError) -> bool:
    code = getattr(exc, "status_code", None)
    return code in (401, 402, 403, 404, 408, 429) or (code is not None and code >= 500)


def _is_tool_use_error(exc: APIStatusError) -> bool:
    if getattr(exc, "status_code", None) != 400:
        return False
    msg = str(exc).lower()
    return "tool_use_failed" in msg or "tool call validation failed" in msg or "failed_generation" in msg


class OpenAICompatibleLLMClient(ILLMClient):
    """Single OpenAI-SDK client supporting Groq, Gemini, Sarvam, and OpenAI fallback."""

    def __init__(
        self,
        providers: Optional[list[ProviderConfig]] = None,
        *,
        timeout_s: Optional[float] = None,
        client_factory: Optional[Callable[[ProviderConfig, float], AsyncOpenAI]] = None,
    ) -> None:
        self.providers = providers if providers is not None else build_provider_chain()
        self.timeout_s = float(
            timeout_s if timeout_s is not None else _env_or_setting("LLM_TIMEOUT_S", 15.0)
        )
        self._client_factory = client_factory or self._default_factory
        self._clients: dict[tuple[str, str, str], AsyncOpenAI] = {}

    @staticmethod
    def _default_factory(cfg: ProviderConfig, timeout_s: float) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url.rstrip("/"),
            timeout=timeout_s,
            max_retries=0,  # fallback chain handles failover deterministically
        )

    def _get_client(self, cfg: ProviderConfig) -> AsyncOpenAI:
        key = (cfg.name, cfg.base_url, cfg.api_key)
        client = self._clients.get(key)
        if client is None:
            client = self._client_factory(cfg, self.timeout_s)
            self._clients[key] = client
        return client

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        temperature: float = 0.2,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.providers:
            raise LLMUnavailableError("No LLM provider API keys configured.")

        errors: list[str] = []
        for cfg in self.providers:
            client = self._get_client(cfg)
            kwargs: dict[str, Any] = {
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if cfg.extra:
                kwargs["extra_body"] = dict(cfg.extra)

            t0 = time.perf_counter()
            try:
                resp = await asyncio.wait_for(
                    client.chat.completions.create(**kwargs),
                    timeout=self.timeout_s + 1.0,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                return self._normalize(resp, cfg, latency_ms)
            except (RateLimitError, APITimeoutError, APIConnectionError, asyncio.TimeoutError) as exc:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                logger.warning("LLM provider %s (%s) failed in %.0fms: %s", cfg.name, cfg.model, latency_ms, exc)
                errors.append(f"{cfg.name}: {type(exc).__name__}")
                continue
            except APIStatusError as exc:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                if _is_tool_use_error(exc):
                    if tools and kwargs.get("tool_choice") == "required":
                        try:
                            retry_kwargs = dict(kwargs, tool_choice="auto")
                            resp = await asyncio.wait_for(
                                client.chat.completions.create(**retry_kwargs),
                                timeout=self.timeout_s + 1.0,
                            )
                            return self._normalize(resp, cfg, (time.perf_counter() - t0) * 1000.0)
                        except Exception as retry_exc:
                            logger.warning(
                                "LLM provider %s (%s) tool_use retry failed: %s",
                                cfg.name, cfg.model, retry_exc,
                            )
                    else:
                        logger.warning(
                            "LLM provider %s (%s) tool_use failed in %.0fms; failing over",
                            cfg.name, cfg.model, latency_ms,
                        )
                    errors.append(f"{cfg.name}: tool_use_failed")
                    continue
                if _is_retryable_status(exc):
                    logger.warning(
                        "LLM provider %s (%s) returned HTTP %s in %.0fms; failing over",
                        cfg.name, cfg.model, exc.status_code, latency_ms,
                    )
                    errors.append(f"{cfg.name}: HTTP {exc.status_code}")
                    continue
                logger.warning("LLM provider %s (%s) non-retryable HTTP %s", cfg.name, cfg.model, exc.status_code)
                raise LLMUnavailableError(f"{cfg.name} HTTP {exc.status_code}: {exc.message}") from exc
            except openai.OpenAIError as exc:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                logger.warning("LLM provider %s (%s) error in %.0fms: %s", cfg.name, cfg.model, latency_ms, exc)
                errors.append(f"{cfg.name}: {type(exc).__name__}")
                continue

        raise LLMUnavailableError("All configured LLM providers failed: " + "; ".join(errors))

    @staticmethod
    def _normalize(resp: Any, cfg: ProviderConfig, latency_ms: float) -> LLMResponse:
        choice = resp.choices[0]
        msg = choice.message
        tool_calls: list[LLMToolCall] = []
        for tc in getattr(msg, "tool_calls", None) or []:
            fn = tc.function
            args, raw = _parse_arguments(getattr(fn, "arguments", "{}"))
            tool_calls.append(
                LLMToolCall(
                    id=str(getattr(tc, "id", "") or f"call_{len(tool_calls)}"),
                    name=str(getattr(fn, "name", "")),
                    arguments=args,
                    raw_arguments=raw,
                )
            )
        usage_obj = getattr(resp, "usage", None)
        usage = {}
        if usage_obj is not None:
            usage = {
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
                "completion_tokens": getattr(usage_obj, "completion_tokens", None),
                "total_tokens": getattr(usage_obj, "total_tokens", None),
            }
        return LLMResponse(
            content=getattr(msg, "content", None),
            tool_calls=tool_calls,
            provider=cfg.name,
            model=cfg.model,
            latency_ms=round(latency_ms, 1),
            usage=usage,
        )


__all__ = [
    "ILLMClient",
    "LLMResponse",
    "LLMToolCall",
    "LLMUnavailableError",
    "OpenAICompatibleLLMClient",
    "ProviderConfig",
    "build_provider_chain",
]
