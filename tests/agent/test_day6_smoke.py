"""Day 6 smoke tests covering voice-chat WAV E2E, provider failover, and Docker infra wiring."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from app.agents.llm_client import OpenAICompatibleLLMClient, ProviderConfig
from scripts.verify_day6_agent import run_offline_verification


@pytest.mark.asyncio
async def test_day6_offline_verification_harness():
    res = await run_offline_verification()
    assert res["voice_marathi_e2e"]["ok"] is True
    assert res["provider_failover_chain"]["ok"] is True
    assert res["refusal_no_advice"]["error_code"] == "NO_ADVICE"
    assert res["chemical_kvk_guard"]["error_code"] == "CHEMICAL_ADVICE_REFUSED"
    assert res["unknown_unit_khandi"]["ok"] is True
    assert res["rag_scheme_citation"]["citations"] >= 1
    assert res["metrics_endpoint"]["ok"] is True


@pytest.mark.asyncio
async def test_multi_provider_failover_across_rate_limit_and_timeout():
    from types import SimpleNamespace

    calls: list[str] = []

    class MultiFailClient:
        def __init__(self, provider: str) -> None:
            self.provider = provider
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        async def _create(self, **kwargs):
            calls.append(self.provider)
            req = httpx.Request("POST", f"https://{self.provider}.example/v1/chat/completions")
            if self.provider == "groq":
                raise RateLimitError("429", response=httpx.Response(429, request=req), body=None)
            if self.provider == "gemini":
                raise APITimeoutError(request=req)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Handled by third provider", tool_calls=[]))],
                usage=None,
            )

    client = OpenAICompatibleLLMClient(
        [
            ProviderConfig("groq", "https://api.groq.com/openai/v1", "k1", "openai/gpt-oss-120b"),
            ProviderConfig("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "k2", "gemini-2.5-flash"),
            ProviderConfig("sarvam", "https://api.sarvam.ai/v1", "k3", "sarvam-105b"),
        ],
        client_factory=lambda cfg, _t: MultiFailClient(cfg.name),
    )
    resp = await client.complete([{"role": "user", "content": "Hello"}])
    assert calls == ["groq", "gemini", "sarvam"]
    assert resp.provider == "sarvam"
    assert resp.content == "Handled by third provider"


def test_docker_compose_wires_qdrant_and_agent_env():
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text("utf-8")
    assert "qdrant:" in compose
    assert "qdrantdata:" in compose
    assert "QDRANT_URL: http://qdrant:6333" in compose
    assert "RETRIEVER:" in compose
    assert "TRANSLATE_PIVOT:" in compose
