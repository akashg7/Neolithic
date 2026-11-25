"""Day 6 end-to-end verification for Krishi-Mitr agent, voice, safety, RAG, and failover.

Usage:
    # Offline / CI smoke check (exercises full FastAPI router, loop, guards, Qdrant, failover):
    python scripts/verify_day6_agent.py --mode offline

    # Live stack check (after `docker compose up` with real keys in `.env`):
    python scripts/verify_day6_agent.py --mode live --url http://localhost:80 --strict-latency
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_silent_wav(duration_s: float = 0.25, sample_rate: int = 16000) -> bytes:
    """Create a valid 16 kHz mono 16-bit PCM WAV clip for `/agent/voice-chat` checks."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * int(sample_rate * duration_s))
    return buf.getvalue()


async def _no_db():
    yield None


class _MemoryRedis:
    """Minimal async Redis stand-in for offline router verification."""

    def __init__(self) -> None:
        self._kv: dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._kv.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self._kv[key] = value

    async def delete(self, key: str) -> int:
        return int(self._kv.pop(key, None) is not None)


def _patch_offline_dependencies():
    """Patch external adapters (LLM failover, window, RAG, voice) cleanly for offline verification."""
    import importlib.util
    from unittest.mock import patch

    from openai import RateLimitError

    from app.adapters.voice_adapter import MockVoiceAdapter
    from app.agents.llm_client import OpenAICompatibleLLMClient, ProviderConfig
    from app.agents.memory import SessionMemoryStore
    from app.agents.tools import decision as decision_mod
    from app.engines.agent_engine import AgentEngine
    from app.main import app
    from app.nlp.translate import Translated
    from app.rag import qdrant_retriever, store
    from app.rag.chunker import approx_token_counter
    from app.rag.embedder import FakeEmbedder
    from app.routers import agent as agent_router

    state = {"no_advice_mode": False, "failover_attempts": []}

    async def fake_sale_window(db, **kw):
        action = "NO_ADVICE" if state["no_advice_mode"] else "HOLD"
        return {
            "action": action,
            "recommendation": action,
            "confidence": "LOW" if action == "NO_ADVICE" else "MEDIUM",
            "hold_days": None if action == "NO_ADVICE" else 5,
            "band_width_bps": 4100 if action == "NO_ADVICE" else 1600,
            "expected_gain_paise": 0 if action == "NO_ADVICE" else 185000,
            "worst_case_paise": 0 if action == "NO_ADVICE" else 40000,
            "sell_now_net_paise_per_qtl": 205000,
            "itemised_costs": {"total_paise_per_qtl": 9000},
            "pledge_quote": None,
            "refusal_reason": "Volatility band exceeds 35%" if action == "NO_ADVICE" else None,
            "explain_mr": "सल्ला नाही" if action == "NO_ADVICE" else "थांबा",
            "explain_en": "No advice" if action == "NO_ADVICE" else "Hold 5 days",
            "data_source": "AGMARKNET_ML",
            "inputs": {
                "commodity": {"slug": "cmd_onion", "name": "Onion", "name_mr": "कांदा", "id": 1},
                "market": {"slug": "mkt_lasalgaon", "name": "Lasalgaon APMC", "name_mr": "लासलगाव", "id": 1},
                "quantity_kg": kw.get("quantity_kg", 1000),
                "transport_included": True,
                "spot_price_source": "AGMARKNET",
                "spot_price_date": "2026-11-24",
            },
        }

    def _msg_with_tool(name: str, args: dict[str, Any], cid: str) -> Any:
        tc = SimpleNamespace(id=cid, function=SimpleNamespace(name=name, arguments=json.dumps(args)))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tc]))], usage=None)

    class FailoverMockSDK:
        def __init__(self, provider_name: str) -> None:
            self.provider_name = provider_name
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        async def _create(self, **kwargs):
            state["failover_attempts"].append(self.provider_name)
            if self.provider_name == "groq" and state["failover_attempts"].count("groq") == 1:
                req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
                raise RateLimitError("simulated 429", response=httpx.Response(429, request=req), body=None)

            msgs = kwargs.get("messages", [])
            tool_msgs = [m for m in msgs if m.get("role") == "tool"]
            last_user = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
            if not tool_msgs:
                if "KCC" in last_user or "loan" in last_user.lower() or "warehouse" in last_user.lower():
                    return _msg_with_tool("search_agri_knowledge", {"query": "WDRA warehouse pledge loan", "category": "schemes_finance"}, "tc_rag")
                if "khandi" in last_user.lower():
                    return _msg_with_tool("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 10, "unit": "khandi"}, "tc_unit")
                return _msg_with_tool("compute_sale_window", {"commodity": "onion", "mandi": "lasalgaon", "quantity": 20, "unit": "bori"}, "tc_win")

            payload = json.loads(tool_msgs[-1]["content"])
            data = payload.get("data") or {}
            if not payload.get("ok") and "NEEDS_INPUT" in str(payload.get("error") or ""):
                return _msg_with_tool(
                    "final_answer",
                    {"reply_text": "How many kg are in one khandi in your area? Please tell me in kg or quintals.", "intent": "WINDOW"},
                    "tc_ask",
                )
            if "chunks" in data and data["chunks"]:
                src = data["chunks"][0]["source_doc"]
                return _msg_with_tool("final_answer", {"reply_text": f"See {src} for pledge loan guidelines.", "intent": "RAG"}, "tc_fin")
            if state["no_advice_mode"]:
                return _msg_with_tool("final_answer", {"reply_text": "Market volatility is too high to advise.", "intent": "WINDOW"}, "tc_fin")
            return _msg_with_tool("final_answer", {"reply_text": "Hold for 5 days; expected gain is Rs 1850.", "intent": "WINDOW"}, "tc_fin")

    emb = FakeEmbedder()
    qdrant_client = store.connect(":memory:")
    store.ensure_collection(qdrant_client, "day6_kb", emb.dense_dim)
    spec = importlib.util.spec_from_file_location("ingest_rag_verify", ROOT / "scripts/ingest_rag.py")
    ingest_mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("ingest_rag_verify", ingest_mod)
    spec.loader.exec_module(ingest_mod)
    ingest_mod.ingest(ROOT / "data/rag_corpus", qdrant_client, "day6_kb", emb, approx_token_counter)
    retriever = qdrant_retriever.Retriever(client=qdrant_client, collection="day6_kb", embedder=emb, reranker=None)
    qdrant_retriever.set_retriever(retriever)

    providers = [
        ProviderConfig("groq", "https://api.groq.com/openai/v1", "k1", "openai/gpt-oss-120b"),
        ProviderConfig("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "k2", "gemini-2.5-flash"),
    ]
    llm = OpenAICompatibleLLMClient(providers, client_factory=lambda cfg, _t: FailoverMockSDK(cfg.name))
    mem = SessionMemoryStore(_MemoryRedis())
    engine = AgentEngine(llm_client=llm, memory=mem)

    return state, app, engine, mem, decision_mod, fake_sale_window, MockVoiceAdapter, patch, Translated


def _offline_catalog():
    """Build a minimal deterministic id_resolver Catalog so offline CLI runs resolve slugs."""
    from app.utils import id_resolver

    c = id_resolver.Catalog()
    c.add("commodity", id=1, name="Onion", name_mr="कांदा")
    c.add("district", id=1, name="Nashik", name_mr="नाशिक")
    c.add("market", id=1, name="Lasalgaon APMC", name_mr="लासलगाव कृषी उत्पन्न बाजार समिती", district_id=1, lat=20.1438, lng=74.2386)
    c.loaded = True
    return c


async def run_offline_verification() -> dict[str, Any]:
    """Run all Day 6 E2E acceptance checks offline via ASGI without external keys."""
    import time
    from unittest.mock import patch

    from app.database import get_db
    from app.dependencies.auth import get_optional_user
    from app.dependencies.voice import get_voice_provider
    from app.engines import agent_engine as engine_mod
    from app.rag import qdrant_retriever
    from app.routers import agent as agent_router
    from app.utils import id_resolver

    state, app, engine, mem, decision_mod, fake_sw, MockVoiceAdapter, _, Translated = _patch_offline_dependencies()
    results: dict[str, Any] = {}
    prev_idx = id_resolver._catalog._idx
    prev_loaded = id_resolver._catalog.loaded
    prev_ts = id_resolver._loaded_at
    cat = _offline_catalog()
    id_resolver._catalog._idx = cat._idx
    id_resolver._catalog.loaded = True
    id_resolver._loaded_at = time.monotonic()

    async def fake_to_en(*, text=None, audio=None, locale_hint=None):
        if audio is not None:
            return Translated(
                original="माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?",
                english="I have 20 bags of onion at Lasalgaon, when should I sell?",
                source_lang="mr",
                hints={"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000},
            )
        if "खंडी" in (text or ""):
            return Translated(
                original=text or "",
                english="Sell 10 khandi onion",
                source_lang="mr",
                hints={"commodity": "cmd_onion", "unit_unknown": "khandi"},
            )
        if "कर्ज" in (text or "") or "loan" in (text or "").lower():
            return Translated(original=text or "", english="Tell me about warehouse pledge loan", source_lang="mr", hints={})
        return Translated(
            original=text or "",
            english="I have 20 bags of onion at Lasalgaon, when should I sell?",
            source_lang="mr",
            hints={"commodity": "cmd_onion", "mandi": "mkt_lasalgaon", "quantity_kg": 1000},
        )

    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_optional_user] = lambda: SimpleNamespace(id=1, name="Ramesh Patil", role="FARMER", phone="9822011111")
    app.dependency_overrides[get_voice_provider] = lambda: MockVoiceAdapter()
    app.dependency_overrides[agent_router.get_agent_engine] = lambda: engine
    app.dependency_overrides[agent_router.get_session_memory] = lambda: mem

    try:
        with (
            patch.dict(os.environ, {"RETRIEVER": "real", "TRANSLATE_BACKEND": "stub", "TRANSLATE_PIVOT": "on"}),
            patch.object(decision_mod, "sale_window", fake_sw),
            patch.object(engine_mod, "to_english", fake_to_en),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://verify") as client:
                # 1. Marathi voice-chat + provider failover (groq 429 -> gemini takes over)
                vr = await client.post(
                    "/api/v1/agent/voice-chat",
                    data={"session_id": "d6_voice", "locale": "mr", "include_audio": "true"},
                    files={"audio": ("demo.wav", build_silent_wav(), "audio/wav")},
                )
                assert vr.status_code == 200, vr.text
                vb = vr.json()
                assert vb["intent_detected"] == "WINDOW"
                assert vb["audio_base64"] is not None
                assert any(c["type"] == "WINDOW_VERDICT" for c in vb["cards"])
                assert "groq" in state["failover_attempts"] and "gemini" in state["failover_attempts"]
                results["voice_marathi_e2e"] = {"ok": True, "intent": vb["intent_detected"], "has_audio": True}
                results["provider_failover_chain"] = {"ok": True, "attempts": list(state["failover_attempts"])}

                # 2. NO_ADVICE refusal demo
                state["no_advice_mode"] = True
                nr = await client.post("/api/v1/agent/chat", json={"session_id": "d6_no_adv", "message": "कांदा कधी विकू?", "locale": "mr"})
                assert nr.status_code == 200 and nr.json()["error_code"] == "NO_ADVICE"
                results["refusal_no_advice"] = {"ok": True, "error_code": nr.json()["error_code"]}
                state["no_advice_mode"] = False

                # 3. Chemical KVK refusal demo
                cr = await client.post(
                    "/api/v1/agent/chat",
                    json={"session_id": "d6_chem", "message": "कांद्यासाठी कोणते कीटकनाशक फवारू?", "locale": "mr"},
                )
                assert cr.status_code == 200 and cr.json()["error_code"] == "CHEMICAL_ADVICE_REFUSED"
                results["chemical_kvk_guard"] = {"ok": True, "error_code": cr.json()["error_code"]}

                # 4. Unknown local unit (khandi) asks farmer instead of guessing
                ur = await client.post(
                    "/api/v1/agent/chat",
                    json={"session_id": "d6_unit", "message": "१० खंडी कांदा विकू का?", "locale": "mr"},
                )
                assert ur.status_code == 200 and not ur.json()["cards"]
                results["unknown_unit_khandi"] = {"ok": True, "intent": ur.json()["intent_detected"]}

                # 5. RAG knowledge grounding
                rr = await client.post(
                    "/api/v1/agent/chat",
                    json={"session_id": "d6_rag", "message": "गोदामात कांदा ठेवून कर्ज कसे मिळते?", "locale": "mr"},
                )
                assert rr.status_code == 200 and len(rr.json()["citations"]) >= 1
                results["rag_scheme_citation"] = {"ok": True, "citations": len(rr.json()["citations"])}

                # 6. Metrics route
                mr = await client.get("/api/v1/agent/metrics?hours=24&limit=100")
                assert mr.status_code == 200 and "latency_ms" in mr.json()
                results["metrics_endpoint"] = {"ok": True}
    finally:
        app.dependency_overrides.clear()
        qdrant_retriever.set_retriever(None)
        id_resolver._catalog._idx = prev_idx
        id_resolver._catalog.loaded = prev_loaded
        id_resolver._loaded_at = prev_ts

    return results


async def run_live_verification(base_url: str, *, wav_path: Optional[str], strict_latency: bool) -> dict[str, Any]:
    """Run Day 6 live verification against a booted FastAPI stack."""
    wav_bytes = Path(wav_path).read_bytes() if wav_path else build_silent_wav()
    base = base_url.rstrip("/")
    results: dict[str, Any] = {}

    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        h = await client.get("/health")
        assert h.status_code == 200, f"Health check failed: {h.text}"

        # Authenticate demo farmer when DEMO_MODE / OTP dev_otp is enabled
        token = None
        otp_r = await client.post("/api/v1/auth/otp/request", json={"phone": "9822011111"})
        if otp_r.status_code == 200 and otp_r.json().get("dev_otp"):
            ver = await client.post("/api/v1/auth/otp/verify", json={"phone": "9822011111", "code": otp_r.json()["dev_otp"]})
            if ver.status_code == 200:
                token = ver.json().get("token") or ver.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        c1 = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "live_d6_chem", "message": "Which pesticide dosage for thrips?", "locale": "en"},
            headers=headers,
        )
        assert c1.status_code == 200 and c1.json().get("error_code") == "CHEMICAL_ADVICE_REFUSED"
        results["chemical_guard"] = c1.json().get("error_code")

        c2 = await client.post(
            "/api/v1/agent/chat",
            json={"session_id": "live_d6_win", "message": "माझ्याकडे २० बोरी कांदा आहे, लासलगावला कधी विकू?", "locale": "mr"},
            headers=headers,
        )
        assert c2.status_code == 200, c2.text
        results["marathi_chat"] = {"intent": c2.json().get("intent_detected"), "error_code": c2.json().get("error_code")}

        if wav_path:
            vc = await client.post(
                "/api/v1/agent/voice-chat",
                data={"session_id": "live_d6_voice", "locale": "mr", "include_audio": "true"},
                files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
                headers=headers,
            )
            assert vc.status_code == 200, vc.text
            results["marathi_voice"] = {"intent": vc.json().get("intent_detected"), "has_audio": bool(vc.json().get("audio_base64"))}

        met = await client.get("/api/v1/agent/metrics?hours=24&limit=500")
        assert met.status_code == 200
        mb = met.json()
        results["metrics"] = mb["latency_ms"]
        if strict_latency:
            t_p95 = mb["latency_ms"]["text"]["p95_ms"]
            v_p95 = mb["latency_ms"]["voice"]["p95_ms"]
            assert t_p95 is None or t_p95 <= 2000.0, f"Text P95 exceeded 2000ms: {t_p95}"
            assert v_p95 is None or v_p95 <= 3500.0, f"Voice P95 exceeded 3500ms: {v_p95}"

    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify Day 6 agent voice, refusals, RAG, failover, and latency.")
    ap.add_argument("--mode", choices=["offline", "live"], default="offline")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--wav", default=None, help="Optional real Marathi .wav clip for --mode live")
    ap.add_argument("--strict-latency", action="store_true", help="Fail if P95 text > 2000ms or voice > 3500ms")
    args = ap.parse_args()

    if args.mode == "offline":
        out = asyncio.run(run_offline_verification())
    else:
        out = asyncio.run(run_live_verification(args.url, wav_path=args.wav, strict_latency=args.strict_latency))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
