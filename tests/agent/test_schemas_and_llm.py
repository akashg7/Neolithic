"""Tests for Contract 1 schemas (`app/schemas/agent.py`) and LLM client fallback."""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import openai
import pytest
from pydantic import ValidationError

from app.agents.llm_client import (
    LLMUnavailableError,
    OpenAICompatibleLLMClient,
    ProviderConfig,
    build_provider_chain,
)
from app.contracts import INTENT_LABELS, Intent, ToolResult
from app.schemas.agent import (
    AgentCard,
    AgentChatRequest,
    AgentChatResponse,
    Citation,
    ScreenContext,
    UiAction,
)


def test_contract1_schemas_and_frozen_intents():
    assert len(INTENT_LABELS) == 10
    req = AgentChatRequest(
        session_id="sess_1",
        message="कांद्याचा भाव काय?",
        locale="mr",
        screen_context=ScreenContext(current_screen="S4_Home", active_commodity_id="cmd_onion"),
    )
    assert req.locale == "mr"

    resp = AgentChatResponse(
        session_id="sess_1",
        turn_id="turn_abc",
        transcript=req.message,
        intent_detected=Intent.WINDOW,
        reply_text="लासलगावमध्ये ५ दिवस थांबा.",
        cards=[
            AgentCard(type="WINDOW_VERDICT", data={"action": "HOLD"}),
            AgentCard(type="CONFIRM_ACTION", data={"action": "CREATE_LOT"}),
            AgentCard(type="ONBOARD_PROFILE", data={"name": "Ramesh"}),
        ],
        ui_action=UiAction(type="OFFER_NAVIGATION", target_screen="S9_Verdict", cta_label="पहा"),
        citations=[Citation(source="window_engine_v1")],
        quick_replies=["a", "b", "c"],
        error_code=None,
    )
    assert resp.intent_detected == Intent.WINDOW
    assert len(resp.cards) == 3

    env = ToolResult(ok=True, data={"x": 1}, source="window_engine_v1")
    assert env.ok and env.error is None


def test_schema_rejects_blank_inputs_and_too_many_quick_replies():
    with pytest.raises(ValidationError):
        AgentChatRequest(session_id="  ", message="hi")
    with pytest.raises(ValidationError):
        AgentChatRequest(session_id="s1", message="   ")
    with pytest.raises(ValidationError):
        AgentChatResponse(
            session_id="s1",
            turn_id="t1",
            transcript="hi",
            intent_detected=Intent.SMALLTALK,
            reply_text="ok",
            quick_replies=["1", "2", "3", "4"],
        )


def test_build_provider_chain_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GEMINI_API_KEY", "gem_test")
    monkeypatch.setenv("SARVAM_API_KEY", "sar_test")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_FALLBACK_CHAIN", "groq,gemini,sarvam,openai")

    chain = build_provider_chain()
    assert [c.name for c in chain] == ["groq", "gemini", "sarvam"]
    assert chain[0].model == "openai/gpt-oss-120b"
    assert chain[0].extra == {"reasoning_effort": "low"}
    assert chain[1].extra == {}


def _ok_completion(content: str = "done"):
    tc = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="final_answer", arguments='{"reply_text": "Onion is Rs 2150.", "intent": "PRICE"}'),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=[tc]))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _dummy_http_resp(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=httpx.Request("POST", "https://example.com/v1/chat/completions"))


@pytest.mark.parametrize(
    "exc_factory",
    [
        lambda: openai.RateLimitError("rate limited", response=_dummy_http_resp(429), body={}),
        lambda: openai.InternalServerError("server error", response=_dummy_http_resp(503), body={}),
        lambda: openai.APITimeoutError(request=httpx.Request("POST", "https://example.com/v1/chat/completions")),
    ],
)
@pytest.mark.asyncio
async def test_llm_client_fallback_on_429_5xx_and_timeout(exc_factory):
    seen_providers: list[str] = []
    seen_kwargs: list[dict] = []

    class FakeCompletions:
        def __init__(self, provider_name: str):
            self.provider_name = provider_name

        async def create(self, **kwargs):
            seen_providers.append(self.provider_name)
            seen_kwargs.append(kwargs)
            if self.provider_name == "groq":
                raise exc_factory()
            return _ok_completion()

    def factory(cfg: ProviderConfig, timeout_s: float):
        return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(cfg.name)))

    providers = [
        ProviderConfig("groq", "https://api.groq.com/openai/v1", "k1", "openai/gpt-oss-120b", {"reasoning_effort": "low"}),
        ProviderConfig("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "k2", "gemini-2.5-flash"),
    ]
    client = OpenAICompatibleLLMClient(providers, client_factory=factory)
    resp = await client.complete([{"role": "user", "content": "hi"}], tools=[{"type": "function", "function": {"name": "final_answer"}}])

    assert seen_providers == ["groq", "gemini"]
    assert seen_kwargs[0]["extra_body"] == {"reasoning_effort": "low"}
    assert "extra_body" not in seen_kwargs[1]
    assert resp.provider == "gemini"
    assert resp.tool_calls[0].name == "final_answer"


@pytest.mark.asyncio
async def test_llm_client_raises_when_all_providers_fail():
    class AlwaysFail:
        async def create(self, **kwargs):
            raise openai.APITimeoutError(request=httpx.Request("POST", "https://example.com"))

    client = OpenAICompatibleLLMClient(
        [ProviderConfig("groq", "https://api.groq.com/openai/v1", "k1", "openai/gpt-oss-120b")],
        client_factory=lambda cfg, t: SimpleNamespace(chat=SimpleNamespace(completions=AlwaysFail())),
    )
    with pytest.raises(LLMUnavailableError):
        await client.complete([{"role": "user", "content": "hi"}])
