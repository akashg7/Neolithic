"""Krishi-Mitr Agent Engine: English-pivot tool-calling loop, guards, and memory.

Executes one conversational or voice turn:
  1. Chemical pre-guard (immediate refusal + KVK referral).
  2. Translate in via Person B's `to_english` (text or audio) + extract hints.
  3. Build cache-friendly English context (system prompt -> profile -> Redis 8 turns -> screen/date -> query + hints).
  4. Tool-calling loop (`max 3` model calls, temperature `0.2`, one tool per step, `final_answer` termination).
  5. Pre-translation safety guards (chemicals, NO_ADVICE, language, number check with 1 retry then fallback).
  6. Build cards/citations/ui_action strictly in code from tool results.
  7. Translate out in one batched call via `translate_back_checked` (re-checks numbers).
  8. Save English turn to Redis DB 2 + log full turn asynchronously to `AgentTurnLog`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import build_context_messages, build_farmer_profile_block
from app.agents.guards import (
    check_language_compliance,
    check_no_advice_compliance,
    check_numbers_against_tools,
    has_no_advice_tool_result,
    is_chemical_query_or_advice,
)
from app.agents.llm_client import ILLMClient, LLMUnavailableError, OpenAICompatibleLLMClient
from app.agents.memory import SessionMemoryStore
from app.agents.response_builder import (
    build_card_fallback_reply,
    build_cards,
    build_citations,
    build_ui_action,
    normalize_quick_replies,
)
from app.agents.tool_bridge import ExecutedToolCall, agent_tool_schemas, execute_agent_tool
from app.agents.tools import ToolContext
from app.config import settings
from app.contracts import Intent, Translated
from app.models.user import User
from app.nlp.messages import MESSAGES, get_message
from app.nlp.translate import (
    EmptyTranscript,
    TranslationUnavailable,
    pivot_enabled,
    to_english,
    translate_back_checked,
)
from app.schemas.agent import AgentCard, AgentChatResponse, Citation, ScreenContext, UiAction
from app.services.agent_log_service import schedule_turn_log

logger = logging.getLogger("krishi.agent")

_ONBOARD_SCREENS = {"S3_Profile", "S03_Profile", "S2_Phone", "S1_Language", "S0_Splash"}


def _parse_intent(raw: Any, executed: list[ExecutedToolCall]) -> Intent:
    if isinstance(raw, str):
        try:
            return Intent(raw.strip().upper())
        except ValueError:
            pass
    # Infer deterministically from the first successful domain tool if model omitted/erred.
    name_to_intent = {
        "compute_sale_window": Intent.WINDOW,
        "get_price_forecast": Intent.PRICE,
        "calculate_grade": Intent.GRADE,
        "create_lot_draft": Intent.LOT,
        "get_farmer_portfolio": Intent.PORTFOLIO,
        "search_agri_knowledge": Intent.RAG,
        "navigate_screen": Intent.NAVIGATE,
        "extract_onboarding_profile": Intent.ONBOARD,
    }
    for item in executed:
        if item.tool_name in name_to_intent:
            return name_to_intent[item.tool_name]
    return Intent.SMALLTALK


def build_mock_response(
    *,
    session_id: str,
    turn_id: str,
    message: str,
    locale: str,
    screen_context: ScreenContext,
) -> AgentChatResponse:
    """Contract-valid deterministic mock mode so Member 1 & 3 can develop offline."""
    low = message.lower()
    if is_chemical_query_or_advice(message):
        return AgentChatResponse(
            session_id=session_id,
            turn_id=turn_id,
            transcript=message,
            intent_detected=Intent.OUT_OF_SCOPE,
            reply_text=get_message("CHEMICAL_REFERRAL", locale),
            error_code="CHEMICAL_ADVICE_REFUSED",
        )
    if any(w in low for w in ("कधी", "विकू", "थांबू", "sell", "hold", "when", "बेच", "रुक")):
        return AgentChatResponse(
            session_id=session_id,
            turn_id=turn_id,
            transcript=message,
            intent_detected=Intent.WINDOW,
            reply_text=(
                "तुमच्या १,००० किलो कांद्यासाठी लासलगाव मंडीत ५ दिवस थांबण्याचा सल्ला आहे. "
                "अंदाजे निव्वळ नफा ₹१,८५० होऊ शकतो; १० पैकी १ वाईट परिस्थितीतही ₹४०० नफा राहील."
                if locale == "mr"
                else "Holding your 1,000 kg of Onion for 5 days at Lasalgaon APMC gives an expected net gain of Rs 1,850 (worst 1-in-10 case: Rs 400)."
            ),
            cards=[
                AgentCard(
                    type="WINDOW_VERDICT",
                    data={
                        "action": "HOLD",
                        "hold_days": 5,
                        "expected_gain_paise": 185000,
                        "worst_case_paise": 40000,
                        "commodity": "Onion",
                        "commodity_mr": "कांदा",
                        "mandi": "Lasalgaon APMC",
                        "mandi_mr": "लासलगाव",
                        "quantity_kg": 1000,
                    },
                )
            ],
            ui_action=UiAction(
                type="OFFER_NAVIGATION",
                target_screen="S9_Verdict",
                cta_label="संपूर्ण तपशील पहा" if locale == "mr" else "See full details",
                params={"commodity_id": "cmd_onion", "market_id": "mkt_lasalgaon", "qty_kg": 1000},
            ),
            citations=[Citation(source="window_engine_v1", title="14-day LightGBM quantile forecast")],
            quick_replies=["लॉट तयार करा" if locale == "mr" else "Create a lot draft"],
        )
    if any(w in low for w in ("भाव", "दर", "price", "rate", "mandi")):
        return AgentChatResponse(
            session_id=session_id,
            turn_id=turn_id,
            transcript=message,
            intent_detected=Intent.PRICE,
            reply_text=(
                "लासलगाव मंडीत कांद्याचा आजचा सरासरी भाव ₹२,१५० प्रति क्विंटल आहे."
                if locale == "mr"
                else "Today's modal onion price at Lasalgaon APMC is Rs 2,150 per quintal."
            ),
            cards=[
                AgentCard(
                    type="PRICE_SNAPSHOT",
                    data={
                        "commodity": "Onion",
                        "commodity_mr": "कांदा",
                        "mandi": "Lasalgaon APMC",
                        "mandi_mr": "लासलगाव",
                        "modal_paise_per_qtl": 215000,
                        "min_paise_per_qtl": 180000,
                        "max_paise_per_qtl": 240000,
                        "change_bps": 750,
                        "obs_date": "2026-11-24",
                        "source": "ARCHIVE",
                    },
                )
            ],
            ui_action=UiAction(
                type="OFFER_NAVIGATION",
                target_screen="PricesIndex",
                cta_label="बाजारभाव पहा" if locale == "mr" else "View prices",
                params={"commodity_id": "cmd_onion", "market_id": "mkt_lasalgaon"},
            ),
            citations=[Citation(source="ARCHIVE", as_of="2026-11-24")],
            quick_replies=["कधी विकू?" if locale == "mr" else "Should I sell now?"],
        )
    if any(w in low for w in ("लॉट", "lot", "बोरी", "list")):
        return AgentChatResponse(
            session_id=session_id,
            turn_id=turn_id,
            transcript=message,
            intent_detected=Intent.LOT,
            reply_text=(
                "१,००० किलो कांद्याचा लॉट ड्राफ्ट तयार आहे. कृपया अपेक्षित भाव तपासून फॉर्ममध्ये भरा."
                if locale == "mr"
                else "Drafted a lot for 1,000 kg of Onion at Lasalgaon APMC. Please confirm your expected price."
            ),
            cards=[
                AgentCard(
                    type="LOT_DRAFT",
                    data={
                        "commodity": "Onion",
                        "commodity_mr": "कांदा",
                        "mandi": "Lasalgaon APMC",
                        "quantity_kg": 1000,
                        "suggested_price_paise_per_qtl": 215000,
                        "missing": ["expected_price_rupees_per_qtl"],
                    },
                )
            ],
            ui_action=UiAction(
                type="PREFILL",
                target_screen="S19_Quantity",
                cta_label="फॉर्ममध्ये भरा" if locale == "mr" else "Fill the form",
                params={"commodity_id": "cmd_onion", "market_id": "mkt_lasalgaon", "qty_kg": 1000},
            ),
            quick_replies=["ग्रेड तपासा" if locale == "mr" else "Check quality grade"],
        )
    return AgentChatResponse(
        session_id=session_id,
        turn_id=turn_id,
        transcript=message,
        intent_detected=Intent.RAG,
        reply_text=(
            "WDRA नोंदणीकृत गोदामात माल ठेवून ई-NWR पावतीवर ७५% पर्यंत तारण कर्ज मिळू शकते."
            if locale == "mr"
            else "You can obtain up to 75% pledge loan against e-NWR receipts at WDRA-registered warehouses."
        ),
        cards=[
            AgentCard(
                type="RAG_CITATION",
                data={"query": message, "chunks": [{"chunk_id": "stub_schemes_001", "source_doc": "schemes_finance/wdra.md"}]},
            )
        ],
        citations=[Citation(source="schemes_finance/wdra.md", title="WDRA Pledge Loan Guidelines", chunk_id="stub_schemes_001")],
        quick_replies=["जवळचे भाव पहा" if locale == "mr" else "Check mandi prices"],
    )


class AgentEngine:
    """Orchestrates one agent turn across translation, LLM loop, tools, guards, and logs."""

    def __init__(
        self,
        llm_client: Optional[ILLMClient] = None,
        memory: Optional[SessionMemoryStore] = None,
        *,
        max_steps: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.llm = llm_client or OpenAICompatibleLLMClient()
        self.memory = memory or SessionMemoryStore()
        self.max_steps = int(max_steps if max_steps is not None else settings.AGENT_MAX_STEPS)
        self.temperature = float(temperature if temperature is not None else settings.AGENT_TEMPERATURE)

    async def run_turn(
        self,
        *,
        db: Optional[AsyncSession],
        user: Optional[User],
        session_id: str,
        locale: str = "mr",
        screen_context: Optional[ScreenContext] = None,
        text: Optional[str] = None,
        audio: Optional[bytes] = None,
        pre_translated: Optional[Translated] = None,
        persist_log: bool = True,
    ) -> AgentChatResponse:
        t_start = time.perf_counter()
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        screen = screen_context or ScreenContext()
        target_lang = locale if locale in ("mr", "hi", "en") else "mr"

        # ── 0. Pre-translation chemical guard on typed text ─────────────────
        if text and is_chemical_query_or_advice(text):
            reply = get_message("CHEMICAL_REFERRAL", target_lang)
            resp = AgentChatResponse(
                session_id=session_id,
                turn_id=turn_id,
                transcript=text,
                intent_detected=Intent.OUT_OF_SCOPE,
                reply_text=reply,
                error_code="CHEMICAL_ADVICE_REFUSED",
            )
            self._log_turn_async(
                persist_log=persist_log,
                turn_id=turn_id,
                session_id=session_id,
                user=user,
                locale=target_lang,
                channel="voice" if audio is not None else "text",
                screen=screen,
                original_text=text,
                english_text=None,
                english_reply=get_message("CHEMICAL_REFERRAL", "en"),
                reply_text=reply,
                intent_detected=Intent.OUT_OF_SCOPE.value,
                executed=[],
                citations=[],
                latency_ms=int((time.perf_counter() - t_start) * 1000),
                error_code="CHEMICAL_ADVICE_REFUSED",
            )
            return resp

        # ── 1. Translate in (and extract hints from original) ───────────────
        try:
            translated = pre_translated or await to_english(
                text=text,
                audio=audio,
                locale_hint=target_lang,
            )
        except EmptyTranscript:
            reply = get_message("FALLBACK", target_lang)
            return AgentChatResponse(
                session_id=session_id,
                turn_id=turn_id,
                transcript="",
                intent_detected=Intent.SMALLTALK,
                reply_text=reply,
                error_code="EMPTY_TRANSCRIPT",
            )
        except TranslationUnavailable:
            reply = get_message("FALLBACK", target_lang)
            return AgentChatResponse(
                session_id=session_id,
                turn_id=turn_id,
                transcript=text or "",
                intent_detected=Intent.OUT_OF_SCOPE,
                reply_text=reply,
                error_code="TRANSLATION_UNAVAILABLE",
            )

        effective_lang = (
            translated.source_lang
            if translated.source_lang in ("mr", "hi", "en")
            else target_lang
        )

        # Chemical check on English translation as well
        if is_chemical_query_or_advice(translated.english):
            reply = get_message("CHEMICAL_REFERRAL", effective_lang)
            resp = AgentChatResponse(
                session_id=session_id,
                turn_id=turn_id,
                transcript=translated.original,
                intent_detected=Intent.OUT_OF_SCOPE,
                reply_text=reply,
                error_code="CHEMICAL_ADVICE_REFUSED",
            )
            self._log_turn_async(
                persist_log=persist_log,
                turn_id=turn_id,
                session_id=session_id,
                user=user,
                locale=effective_lang,
                channel="voice" if audio is not None else "text",
                screen=screen,
                original_text=translated.original,
                english_text=translated.english,
                english_reply=get_message("CHEMICAL_REFERRAL", "en"),
                reply_text=reply,
                intent_detected=Intent.OUT_OF_SCOPE.value,
                executed=[],
                citations=[],
                latency_ms=int((time.perf_counter() - t_start) * 1000),
                error_code="CHEMICAL_ADVICE_REFUSED",
            )
            return resp

        # ── 2. Build context (profile + Redis last 8 turns concurrently) ─────
        pivot = pivot_enabled()
        model_user_input = translated.english if pivot else translated.original
        profile_block, history_turns = await asyncio.gather(
            build_farmer_profile_block(db, user),
            self.memory.load_turns(session_id),
        )
        messages = build_context_messages(
            profile_block=profile_block,
            history_turns=history_turns,
            screen_context=screen,
            model_input_text=model_user_input,
            hints=translated.hints,
            pivot_on=pivot,
            target_lang=effective_lang,
        )

        include_onboarding = (screen.current_screen or "") in _ONBOARD_SCREENS
        schemas = agent_tool_schemas(include_onboarding=include_onboarding)
        final_only_schemas = [s for s in schemas if s["function"]["name"] == "final_answer"]
        tool_ctx = ToolContext(
            db=db,
            user=user,
            locale=effective_lang,
            screen=screen.model_dump(exclude_none=True),
        )

        # ── 3. Tool-calling loop (max 3 model calls + 1 guard retry) ────────
        executed: list[ExecutedToolCall] = []
        final_args: Optional[dict[str, Any]] = None
        guard_retried = False
        error_code: Optional[str] = None

        try:
            normal_steps = 0
            force_final_retry = False
            while normal_steps < self.max_steps or force_final_retry:
                is_last_normal = (normal_steps == self.max_steps - 1) and bool(executed)
                active_tools = final_only_schemas if (force_final_retry or is_last_normal) else schemas
                choice = "required" if (normal_steps == 0 or force_final_retry or is_last_normal) else "auto"
                llm_resp = await self.llm.complete(
                    messages,
                    tools=active_tools,
                    temperature=self.temperature,
                    tool_choice=choice,
                )
                if force_final_retry:
                    force_final_retry = False
                else:
                    normal_steps += 1

                calls = llm_resp.tool_calls
                if not calls:
                    # Plain-text response fallback when provider did not emit a tool call.
                    candidate_reply = (llm_resp.content or "").strip()
                    if not candidate_reply:
                        continue
                    final_args = {
                        "reply_text": candidate_reply,
                        "intent": _parse_intent(None, executed).value,
                        "quick_replies": [],
                    }
                    failure = self._check_pre_translation_guards(
                        final_args["reply_text"],
                        executed=executed,
                        pivot_on=pivot,
                        target_lang=effective_lang,
                        user_english_text=translated.english,
                        hints=translated.hints,
                    )
                    if failure is not None and not guard_retried:
                        guard_retried = True
                        force_final_retry = True
                        messages.append({"role": "assistant", "content": candidate_reply})
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Correction required ({failure.guard}): {failure.reason} Call `final_answer` cleanly.",
                            }
                        )
                        final_args = None
                        continue
                    break

                primary = calls[0]
                assistant_tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.raw_arguments},
                    }
                    for tc in calls
                ]
                messages.append({"role": "assistant", "content": llm_resp.content, "tool_calls": assistant_tool_calls})

                if primary.name == "final_answer":
                    candidate_reply = str(primary.arguments.get("reply_text") or "").strip()
                    failure = self._check_pre_translation_guards(
                        candidate_reply,
                        executed=executed,
                        pivot_on=pivot,
                        target_lang=effective_lang,
                        user_english_text=translated.english,
                        hints=translated.hints,
                    )
                    if failure is not None:
                        if failure.guard == "chemicals":
                            final_args = {
                                "reply_text": get_message("CHEMICAL_REFERRAL", "en" if pivot else effective_lang),
                                "intent": Intent.OUT_OF_SCOPE.value,
                                "quick_replies": [],
                            }
                            error_code = "CHEMICAL_ADVICE_REFUSED"
                            break
                        if failure.guard == "NO_ADVICE":
                            final_args = {
                                "reply_text": get_message("NO_ADVICE", "en" if pivot else effective_lang),
                                "intent": Intent.WINDOW.value,
                                "quick_replies": [],
                            }
                            error_code = "NO_ADVICE"
                            break
                        if not guard_retried:
                            guard_retried = True
                            force_final_retry = True
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": primary.id,
                                    "content": json.dumps({"ok": False, "error": failure.reason}),
                                }
                            )
                            for extra_tc in calls[1:]:
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": extra_tc.id,
                                        "content": json.dumps({"ok": False, "error": "Ignored extra call"}),
                                    }
                                )
                            continue
                        # Failed guard twice: mark error_code so response builder uses card fallback
                        error_code = "NUMBER_CHECK_FAILED" if failure.guard == "number_check" else "GUARD_FALLBACK"
                    final_args = dict(primary.arguments)
                    break

                # Execute the single domain tool (one tool per step)
                result = await execute_agent_tool(primary.name, tool_ctx, primary.arguments, hints=translated.hints)
                executed.append(result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": primary.id,
                        "content": result.envelope.model_dump_json(),
                    }
                )
                for extra_tc in calls[1:]:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": extra_tc.id,
                            "content": json.dumps(
                                {"ok": False, "error": "Only one tool call per step is allowed."}
                            ),
                        }
                    )
        except LLMUnavailableError as exc:
            logger.error("LLM unavailable on turn %s: %s", turn_id, exc)
            cards = build_cards(executed)
            citations = build_citations(executed)
            ui_action = build_ui_action(executed)
            fallback_reply = build_card_fallback_reply(cards, effective_lang)
            self._log_turn_async(
                persist_log=persist_log,
                turn_id=turn_id,
                session_id=session_id,
                user=user,
                locale=effective_lang,
                channel="voice" if audio is not None else "text",
                screen=screen,
                original_text=translated.original,
                english_text=translated.english,
                english_reply=get_message("FALLBACK", "en"),
                reply_text=fallback_reply,
                intent_detected=_parse_intent(None, executed).value,
                executed=executed,
                citations=citations,
                latency_ms=int((time.perf_counter() - t_start) * 1000),
                error_code="LLM_UNAVAILABLE",
            )
            return AgentChatResponse(
                session_id=session_id,
                turn_id=turn_id,
                transcript=translated.original,
                intent_detected=_parse_intent(None, executed),
                reply_text=fallback_reply,
                cards=cards,
                ui_action=ui_action,
                citations=citations,
                error_code="LLM_UNAVAILABLE",
            )

        # ── 4. Response Builder (cards, citations, ui_action in code) ───────
        cards = build_cards(executed)
        citations = build_citations(executed)
        model_ui_action = (final_args or {}).get("ui_action")
        ui_action = build_ui_action(executed, model_ui_action=model_ui_action)
        intent = _parse_intent((final_args or {}).get("intent"), executed)
        quick_replies = normalize_quick_replies((final_args or {}).get("quick_replies"))

        # Enforce NO_ADVICE template even if model tried to skip/alter it
        if has_no_advice_tool_result(executed):
            error_code = "NO_ADVICE"
            intent = Intent.WINDOW
            english_reply = MESSAGES["NO_ADVICE"]["en"]
            if not pivot and effective_lang != "en":
                english_reply = get_message("NO_ADVICE", effective_lang)
        elif error_code in ("NUMBER_CHECK_FAILED", "GUARD_FALLBACK") or not final_args:
            english_reply = MESSAGES["FALLBACK"]["en"]
            error_code = error_code or "EMPTY_RESPONSE"
        else:
            english_reply = str(final_args.get("reply_text") or "").strip() or MESSAGES["FALLBACK"]["en"]

        # ── 5. Translate out (one batched call + second number check) ───────
        final_reply = english_reply
        if error_code in ("NUMBER_CHECK_FAILED", "GUARD_FALLBACK"):
            final_reply = build_card_fallback_reply(cards, effective_lang)
            quick_replies = []
        elif pivot and effective_lang != "en":
            texts_to_translate = [english_reply, *quick_replies]
            translate_cta = bool(ui_action and not any("\u0900" <= ch <= "\u097F" for ch in ui_action.cta_label))
            if translate_cta and ui_action is not None:
                texts_to_translate.append(ui_action.cta_label)
            try:
                translated_out, numbers_ok = await translate_back_checked(texts_to_translate, effective_lang)
                if not numbers_ok:
                    final_reply = build_card_fallback_reply(cards, effective_lang)
                    quick_replies = []
                    error_code = error_code or "TRANSLATION_NUMBER_MISMATCH"
                else:
                    final_reply = translated_out[0]
                    qr_end = 1 + len(quick_replies)
                    quick_replies = translated_out[1:qr_end]
                    if translate_cta and ui_action is not None and len(translated_out) > qr_end:
                        ui_action.cta_label = translated_out[qr_end]
            except TranslationUnavailable:
                final_reply = build_card_fallback_reply(cards, effective_lang)
                quick_replies = []
                error_code = error_code or "TRANSLATION_UNAVAILABLE"

        # ── 6. Save English turn to Redis + schedule async Postgres turn log ─
        await self.memory.append_turn(
            session_id,
            user_text=model_user_input,
            assistant_text=english_reply,
            intent=intent.value,
            tool_summaries=[e.summary for e in executed if e.summary],
        )

        latency_ms = int((time.perf_counter() - t_start) * 1000)
        self._log_turn_async(
            persist_log=persist_log,
            turn_id=turn_id,
            session_id=session_id,
            user=user,
            locale=effective_lang,
            channel="voice" if audio is not None else "text",
            screen=screen,
            original_text=translated.original,
            english_text=translated.english if (pivot or effective_lang == "en") else None,
            english_reply=english_reply if (pivot or effective_lang == "en") else None,
            reply_text=final_reply,
            intent_detected=intent.value,
            executed=executed,
            citations=citations,
            latency_ms=latency_ms,
            error_code=error_code,
        )

        return AgentChatResponse(
            session_id=session_id,
            turn_id=turn_id,
            transcript=translated.original,
            intent_detected=intent,
            reply_text=final_reply,
            cards=cards,
            ui_action=ui_action,
            citations=citations,
            quick_replies=quick_replies,
            error_code=error_code,
        )

    @staticmethod
    def _check_pre_translation_guards(
        reply_text: str,
        *,
        executed: list[ExecutedToolCall],
        pivot_on: bool,
        target_lang: str,
        user_english_text: str,
        hints: dict[str, Any],
    ):
        if is_chemical_query_or_advice(reply_text):
            from app.agents.guards import GuardFailure

            return GuardFailure("chemicals", "Reply must not prescribe pesticides or chemical doses.")
        no_advice_fail = check_no_advice_compliance(reply_text, executed)
        if no_advice_fail is not None:
            return no_advice_fail
        lang_fail = check_language_compliance(reply_text, pivot_on=pivot_on, target_lang=target_lang)
        if lang_fail is not None:
            return lang_fail
        return check_numbers_against_tools(
            reply_text,
            executed,
            user_english_text=user_english_text,
            hints=hints,
        )

    @staticmethod
    def _log_turn_async(
        *,
        persist_log: bool,
        turn_id: str,
        session_id: str,
        user: Optional[User],
        locale: str,
        channel: str,
        screen: ScreenContext,
        original_text: Optional[str],
        english_text: Optional[str],
        english_reply: Optional[str],
        reply_text: Optional[str],
        intent_detected: Optional[str],
        executed: list[ExecutedToolCall],
        citations: list[Citation],
        latency_ms: int,
        error_code: Optional[str],
    ) -> None:
        if not persist_log:
            return
        schedule_turn_log(
            turn_id=turn_id,
            session_id=session_id,
            user_id=user.id if user is not None else None,
            locale=locale,
            channel=channel,
            screen_context=screen.model_dump(exclude_none=True),
            original_text=original_text,
            english_text=english_text,
            transcript=original_text,
            english_reply=english_reply,
            reply_text=reply_text,
            intent_detected=intent_detected,
            tools_called=[
                {"name": e.tool_name, "ok": e.envelope.ok, "source": e.envelope.source, "error": e.envelope.error}
                for e in executed
            ],
            rag_sources=[c.model_dump() for c in citations],
            latency_ms=latency_ms,
            error_code=error_code,
        )


__all__ = ["AgentEngine", "build_mock_response"]
