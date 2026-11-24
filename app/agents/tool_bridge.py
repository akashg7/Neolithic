"""Canonical agent-loop tool bridge (Person A).

Exposes the coarse, single-call tools from the Two-Person Execution Plan and
`eval/bakeoff.py` (`compute_sale_window`, `get_price_forecast`, `calculate_grade`,
`create_lot_draft`, `get_farmer_portfolio`, `search_agri_knowledge`,
`navigate_screen`, plus `extract_onboarding_profile` and `final_answer`), wrapping
the underlying `app.agents.tools` handlers and Person B's NLP/RAG modules.

Key guarantees:
  * Hint-wins rule: `commodity`, `mandi`, and `quantity_kg` extracted from the
    farmer's original words override model arguments when they disagree.
  * Variable/unknown units (`khandi`, `goni`, `maund`) raise `UnknownUnitError`
    via `app.nlp.units.to_kg` and return `NEEDS_INPUT` instead of guessing.
  * Write tools NEVER write to Postgres; they emit `LOT_DRAFT` / `CONFIRM_ACTION`.
  * Every tool returns a uniform `ToolResult` envelope (`app.contracts.ToolResult`)
    plus metadata (`ui_action`, `citations`) for the response builder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.agents.memory import compact_tool_summary
from app.agents.tools import ToolContext, run_tool
from app.agents.tools.navigation import FarmerScreen
from app.contracts import INTENT_LABELS, ToolResult
from app.nlp.lexicon import resolve_commodity, resolve_mandi
from app.nlp.units import UnknownUnitError, to_kg as nlp_to_kg
from app.services import price_service
from app.utils.id_resolver import ResolveError, resolve as resolve_ref

_ALLOWED_SCREENS: set[str] = set(getattr(FarmerScreen, "__args__", ()))

_SCREEN_ALIASES: dict[str, str] = {
    "profile": "S35_FarmerProfile",
    "farmer_profile": "S35_FarmerProfile",
    "onboarding": "S3_Profile",
    "sell": "S15_MyLots",
    "my_lots": "S15_MyLots",
    "lots": "S15_MyLots",
    "create_lot": "S19_Quantity",
    "home": "S4_Home",
    "prices": "PricesIndex",
    "market": "PricesIndex",
    "verdict": "S9_Verdict",
    "sale_window": "S9_Verdict",
    "loan": "S13_CropLoan",
    "pledge_loan": "S13_CropLoan",
    "deals": "S31_DealsList",
    "transactions": "S31_DealsList",
    "grade": "S20_QualityDiagnostic",
    "quality": "S20_QualityDiagnostic",
    "assistant": "Assistant",
    "notifications": "S38_Notifications",
    "language": "LanguageSwitcher",
    "talks": "S37_Talks",
}

_CATEGORY_ENUM = ["schemes_finance", "grading", "platform", "glossary"]


def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def agent_tool_schemas(*, include_onboarding: bool = False) -> list[dict[str, Any]]:
    """OpenAI-format tool schemas passed to `ILLMClient.complete` in stable order."""
    schemas: list[dict[str, Any]] = [
        _fn(
            "compute_sale_window",
            "Should the farmer sell now or hold? Fetches the forecast itself and returns a SELL_NOW / HOLD / "
            "SPLIT / NO_ADVICE verdict with expected gain, worst 1-in-10 case, itemised costs (paise), "
            "and a WINDOW_VERDICT card. Always prefer this single coarse tool for sell-or-wait questions.",
            {
                "commodity": {"type": "string", "description": "Crop name or slug (e.g. 'onion', 'cmd_onion'). Omit to use screen context or lot."},
                "mandi": {"type": "string", "description": "Mandi name or slug (e.g. 'Lasalgaon', 'mkt_lasalgaon'). Omit to use screen context or lot."},
                "quantity": {"type": "number", "description": "Numeric quantity as the farmer said it (e.g. 20 for '20 bori')."},
                "unit": {"type": "string", "description": "Unit of quantity: 'kg', 'quintal', 'bori', 'ton', etc. Pass raw unit if unsure."},
                "grade": {"type": "string", "enum": ["A", "B", "C"], "description": "Produce grade if known (default 'A')."},
                "lot_id": {"type": "string", "description": "Optional existing lot ID."},
            },
            [],
        ),
        _fn(
            "get_price_forecast",
            "Get today's observed mandi rate (min, modal, max in paise/qtl + 7d change) and the 14-day p10/p50/p90 "
            "price forecast for a crop and mandi. Emits a PRICE_SNAPSHOT card.",
            {
                "commodity": {"type": "string", "description": "Crop name or slug. Omit to use screen context."},
                "mandi": {"type": "string", "description": "Mandi name or slug. Omit to use screen context."},
                "horizon_days": {"type": "integer", "description": "Forecast horizon in days (1 to 14, default 14)."},
            },
            [],
        ),
        _fn(
            "calculate_grade",
            "Calculate produce grade (A/B/C) from six self-check fields (size_uniform, colour_uniform, "
            "damage_pct, sprouting, moisture_feel, foreign_matter). If any fields are missing, returns the next "
            "question to ask the farmer one at a time.",
            {
                "commodity": {"type": "string", "description": "Crop name or slug."},
                "lot_id": {"type": "string", "description": "Optional lot ID to attach a Save Grade confirm card."},
                "size_uniform": {"type": "integer", "enum": [1, 2, 3], "description": "3=uniform, 2=mixed, 1=very mixed."},
                "colour_uniform": {"type": "integer", "enum": [1, 2, 3], "description": "3=uniform, 2=some variation, 1=uneven."},
                "damage_pct": {"type": "integer", "description": "Percent damaged (0-100)."},
                "sprouting": {"type": "integer", "enum": [1, 2, 3], "description": "3=none, 2=a little, 1=a lot."},
                "moisture_feel": {"type": "integer", "enum": [1, 2, 3], "description": "3=dry, 2=slightly damp, 1=wet."},
                "foreign_matter": {"type": "integer", "enum": [1, 2, 3], "description": "3=clean, 2=some debris, 1=a lot."},
                "assay": {"type": "object", "description": "Optional dict containing any of the 6 assay fields."},
            },
            [],
        ),
        _fn(
            "create_lot_draft",
            "Prepare a LOT_DRAFT card (or CONFIRM_ACTION card when confirm=true and price is agreed) from the "
            "farmer's words. NEVER writes to the database; the farmer taps Confirm in the app to save.",
            {
                "commodity": {"type": "string", "description": "Crop name or slug."},
                "quantity": {"type": "number", "description": "Numeric quantity."},
                "unit": {"type": "string", "description": "Unit ('kg', 'quintal', 'bori', 'ton', etc.)."},
                "mandi": {"type": "string", "description": "Target mandi if mentioned."},
                "expected_price_rupees": {"type": "number", "description": "Optional expected price in rupees per quintal."},
                "confirm": {"type": "boolean", "description": "Set true only when the farmer confirmed saving the lot."},
            },
            [],
        ),
        _fn(
            "get_farmer_portfolio",
            "Fetch the logged-in farmer's active lots, open buyer/farmer offers, and escrow deal statuses.",
            {},
            [],
        ),
        _fn(
            "search_agri_knowledge",
            "Search agricultural knowledge base: KCC, WDRA pledge loans, PMFBY insurance, e-NAM, AGMARK grading, "
            "post-harvest storage, escrow/pooling rules, and unit glossaries.",
            {
                "query": {"type": "string", "description": "Concise English search query."},
                "category": {"type": "string", "enum": _CATEGORY_ENUM, "description": "Optional corpus category."},
                "crop": {"type": "string", "description": "Optional crop filter."},
            },
            ["query"],
        ),
        _fn(
            "navigate_screen",
            "Offer a one-tap button to open a specific app screen (e.g. S15_MyLots, S9_Verdict, S13_CropLoan, "
            "S31_DealsList, S35_FarmerProfile, PricesIndex).",
            {
                "target_screen": {"type": "string", "description": "Screen name from the app navigation whitelist."},
                "params": {"type": "object", "description": "Optional IDs: commodity_id, market_id, district_id, lot_id, qty_kg."},
            },
            ["target_screen"],
        ),
    ]
    if include_onboarding:
        schemas.append(
            _fn(
                "extract_onboarding_profile",
                "Extract farmer registration details (name, village, district) during onboarding and emit an "
                "ONBOARD_PROFILE card to pre-fill the profile form.",
                {
                    "name": {"type": "string", "description": "Farmer's full name."},
                    "village": {"type": "string", "description": "Village or taluka name."},
                    "district": {"type": "string", "description": "Maharashtra district name or slug."},
                },
                [],
            )
        )
    schemas.append(
        _fn(
            "final_answer",
            "End the turn with a grounded English reply, frozen intent label, and up to 3 quick reply chips.",
            {
                "reply_text": {"type": "string", "description": "Concise English reply grounded strictly in tool results."},
                "intent": {"type": "string", "enum": INTENT_LABELS, "description": "Frozen intent label."},
                "quick_replies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Up to 3 short English follow-up suggestions.",
                },
                "ui_action": {
                    "type": "object",
                    "description": "Optional navigation override {target_screen, params}.",
                },
            },
            ["reply_text", "intent"],
        )
    )
    return schemas


@dataclass
class ExecutedToolCall:
    """Normalized outcome of executing one canonical agent tool."""

    tool_name: str
    envelope: ToolResult
    ui_action: Optional[dict[str, Any]] = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


def resolve_allowed_screen(target: str) -> Optional[str]:
    """Resolve friendly screen aliases and enforce the `FarmerScreen` whitelist."""
    if not target:
        return None
    cleaned = str(target).strip()
    if cleaned in _ALLOWED_SCREENS:
        return cleaned
    lowered = cleaned.lower().replace(" ", "_")
    mapped = _SCREEN_ALIASES.get(lowered)
    if mapped and mapped in _ALLOWED_SCREENS:
        return mapped
    return None


def _tool_result_from_raw(raw: dict[str, Any], source: str) -> ToolResult:
    if raw.get("ok"):
        return ToolResult(
            ok=True,
            data=raw.get("data") or {},
            source=source,
            card=raw.get("card"),
            error=None,
        )
    err = raw.get("error") or {}
    if isinstance(err, dict):
        code = err.get("code", "ERROR")
        msg = err.get("message", "Tool execution failed")
        err_text = f"{code}: {msg}"
    else:
        err_text = str(err)
    return ToolResult(ok=False, data={}, source=source, card=None, error=err_text)


def _apply_hint_wins_and_units(
    tool_name: str,
    args: dict[str, Any],
    hints: dict[str, Any],
    *,
    needs_quantity: bool = False,
) -> tuple[dict[str, Any], Optional[ToolResult]]:
    """Enforce PDF rules: original-text hints beat model args; variable units ask."""
    merged = dict(args)

    if needs_quantity and hints.get("unit_unknown"):
        u = hints["unit_unknown"]
        return merged, ToolResult(
            ok=False,
            source="unit_parser",
            error=f"NEEDS_INPUT: unknown or variable unit {u!r}. Ask the farmer for quantity in kg, quintals, or bags (bori).",
        )

    if "commodity" in hints and tool_name in ("compute_sale_window", "get_price_forecast", "create_lot_draft", "calculate_grade"):
        merged["commodity"] = hints["commodity"]
    if "crop" not in merged and "commodity" in hints and tool_name == "search_agri_knowledge":
        merged["crop"] = hints["commodity"]

    if "mandi" in hints and tool_name in ("compute_sale_window", "get_price_forecast"):
        merged["mandi"] = hints["mandi"]
    elif "mandi" in hints and tool_name == "create_lot_draft" and merged.get("mandi"):
        merged["mandi"] = hints["mandi"]

    if needs_quantity:
        if "quantity_kg" in hints:
            merged["quantity"] = hints["quantity_kg"]
            merged["unit"] = "kg"
        elif merged.get("quantity") is not None:
            raw_unit = str(merged.get("unit") or "kg")
            try:
                kg = nlp_to_kg(float(merged["quantity"]), raw_unit)
            except UnknownUnitError as exc:
                return merged, ToolResult(
                    ok=False,
                    source="unit_parser",
                    error=f"NEEDS_INPUT: {exc}. Ask the farmer to state quantity in kg, quintals, or bags (bori).",
                )
            except (ValueError, TypeError) as exc:
                return merged, ToolResult(
                    ok=False,
                    source="unit_parser",
                    error=f"NEEDS_INPUT: invalid quantity ({exc}). Ask the farmer for a positive quantity.",
                )
            merged["quantity"] = kg
            merged["unit"] = "kg"

    return merged, None


def _citations_from_raw(raw: dict[str, Any], source: str) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    data = raw.get("data") or {}
    chunks = data.get("chunks")
    if isinstance(chunks, list) and chunks:
        for ch in chunks:
            if isinstance(ch, dict):
                citations.append(
                    {
                        "source": str(ch.get("source_doc") or source),
                        "title": ch.get("section_title"),
                        "chunk_id": ch.get("chunk_id"),
                        "section_title": ch.get("section_title"),
                    }
                )
        return citations
    cit = raw.get("citation")
    if isinstance(cit, dict) and cit.get("source"):
        citations.append(
            {
                "source": str(cit["source"]),
                "title": cit.get("title") or cit.get("mandi"),
                "as_of": cit.get("as_of") or cit.get("price_date"),
            }
        )
    return citations


async def _pick_default_mandi(ctx: ToolContext, commodity_ref: str) -> Optional[str]:
    """When user omitted mandi and none is on screen, check DB for most active market."""
    if ctx.db is None:
        return None
    try:
        comm = await resolve_ref(ctx.db, "commodity", commodity_ref)
        latest = await price_service.latest_prices_by_market(ctx.db, comm.id)
        if not latest:
            return None
        best_mid = max(latest.items(), key=lambda kv: (kv[1].get("obs_date", ""), kv[1].get("arrivals_qtl", 0)))[0]
        return str(best_mid)
    except Exception:
        return None


async def execute_agent_tool(
    name: str,
    ctx: ToolContext,
    args: Optional[dict[str, Any]],
    *,
    hints: Optional[dict[str, Any]] = None,
) -> ExecutedToolCall:
    """Execute one canonical agent tool against backend services and return `ExecutedToolCall`."""
    raw_args = dict(args or {})
    hints = dict(hints or {})

    if name == "compute_sale_window":
        merged, err = _apply_hint_wins_and_units(name, raw_args, hints, needs_quantity=True)
        if err is not None:
            return ExecutedToolCall(name, err, summary=compact_tool_summary(name, err.model_dump()))
        mapped = {
            "crop": merged.get("commodity") or merged.get("crop"),
            "mandi": merged.get("mandi"),
            "quantity": merged.get("quantity"),
            "unit": merged.get("unit") or "kg",
            "grade": merged.get("grade") or "A",
            "lot_id": merged.get("lot_id"),
        }
        mapped = {k: v for k, v in mapped.items() if v is not None}
        raw = await run_tool("get_sale_window", ctx, mapped)
        env = _tool_result_from_raw(raw, "window_engine_v1")
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action=raw.get("ui_action"),
            citations=_citations_from_raw(raw, "window_engine_v1"),
            summary=compact_tool_summary(name, raw),
        )

    if name == "get_price_forecast":
        merged, _ = _apply_hint_wins_and_units(name, raw_args, hints, needs_quantity=False)
        crop_ref = merged.get("commodity") or merged.get("crop") or ctx.screen_value("active_commodity_id")
        mandi_ref = merged.get("mandi") or ctx.screen_value("active_market_id")
        horizon = int(merged.get("horizon_days") or 14)

        if not mandi_ref and crop_ref:
            mandi_ref = await _pick_default_mandi(ctx, str(crop_ref))

        price_args = {k: v for k, v in {"crop": crop_ref, "mandi": mandi_ref}.items() if v is not None}
        snap_raw = await run_tool("get_mandi_price", ctx, price_args)
        fc_args = {
            k: v
            for k, v in {"crop": crop_ref, "mandi": mandi_ref, "horizon_days": max(1, min(14, horizon))}.items()
            if v is not None
        }
        fc_raw = await run_tool("get_price_forecast", ctx, fc_args)

        if not snap_raw.get("ok") and not fc_raw.get("ok"):
            # Propagate missing/ambiguous input errors cleanly
            chosen = snap_raw if (snap_raw.get("error") or {}).get("code") in ("NEEDS_INPUT", "AMBIGUOUS", "NOT_FOUND") else fc_raw
            env = _tool_result_from_raw(chosen, "price_engine_v1")
            return ExecutedToolCall(name, env, summary=compact_tool_summary(name, chosen))

        combined_data: dict[str, Any] = {}
        citations: list[dict[str, Any]] = []
        card = None
        ui_action = None

        if snap_raw.get("ok"):
            sdata = snap_raw.get("data") or {}
            combined_data["commodity"] = sdata.get("commodity")
            combined_data["market"] = sdata.get("market")
            combined_data["snapshot"] = {
                k: sdata.get(k)
                for k in (
                    "obs_date",
                    "min_paise_per_qtl",
                    "max_paise_per_qtl",
                    "modal_paise_per_qtl",
                    "arrivals_qtl",
                    "change_paise_per_qtl",
                    "change_bps",
                    "source",
                )
            }
            card = snap_raw.get("card")
            ui_action = snap_raw.get("ui_action")
            citations.extend(_citations_from_raw(snap_raw, "AGMARKNET"))

        if fc_raw.get("ok"):
            fdata = fc_raw.get("data") or {}
            combined_data.setdefault("commodity", fdata.get("commodity"))
            combined_data.setdefault("market", fdata.get("market"))
            combined_data["forecast"] = {
                "source": fdata.get("source"),
                "summary": fdata.get("summary"),
                "points": fdata.get("points"),
            }
            ui_action = ui_action or fc_raw.get("ui_action")
            citations.extend(_citations_from_raw(fc_raw, fdata.get("source") or "price_engine_v1"))
        else:
            combined_data["forecast"] = None
            combined_data["forecast_unavailable"] = True

        src = (
            (combined_data.get("forecast") or {}).get("source")
            or (combined_data.get("snapshot") or {}).get("source")
            or "price_engine_v1"
        )
        env = ToolResult(ok=True, data=combined_data, source=str(src), card=card, error=None)
        summary = compact_tool_summary(
            name,
            {"ok": True, "data": {**combined_data, **(combined_data.get("snapshot") or {})}, "card": card},
        )
        return ExecutedToolCall(name, env, ui_action=ui_action, citations=citations, summary=summary)

    if name == "calculate_grade":
        assay = raw_args.get("assay")
        flat: dict[str, Any] = dict(assay) if isinstance(assay, dict) else {}
        for k in ("lot_id", "size_uniform", "colour_uniform", "damage_pct", "sprouting", "moisture_feel", "foreign_matter"):
            if k in raw_args and raw_args[k] is not None:
                flat[k] = raw_args[k]
        raw = await run_tool("run_quality_check", ctx, flat)
        env = _tool_result_from_raw(raw, "grading_engine_v1")
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action=raw.get("ui_action"),
            citations=[{"source": "grading_engine_v1", "title": "AGMARK Self-Assay Grading"}] if env.ok else [],
            summary=compact_tool_summary(name, raw),
        )

    if name == "create_lot_draft":
        merged, err = _apply_hint_wins_and_units(name, raw_args, hints, needs_quantity=True)
        if err is not None:
            return ExecutedToolCall(name, err, summary=compact_tool_summary(name, err.model_dump()))
        want_confirm = bool(merged.get("confirm")) and merged.get("expected_price_rupees") is not None and ctx.user is not None
        mapped = {
            "crop": merged.get("commodity") or merged.get("crop"),
            "quantity": merged.get("quantity"),
            "unit": merged.get("unit") or "kg",
            "mandi": merged.get("mandi"),
            "expected_price_rupees_per_qtl": merged.get("expected_price_rupees"),
        }
        mapped = {k: v for k, v in mapped.items() if v is not None}
        inner_name = "create_lot" if want_confirm else "draft_lot"
        raw = await run_tool(inner_name, ctx, mapped)
        env = _tool_result_from_raw(raw, "lot_service_v1")
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action=raw.get("ui_action"),
            citations=[],
            summary=compact_tool_summary(name, raw),
        )

    if name == "get_farmer_portfolio":
        raw = await run_tool("get_farmer_portfolio", ctx, {})
        env = _tool_result_from_raw(raw, "krishi_mitr_db")
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action=raw.get("ui_action"),
            citations=_citations_from_raw(raw, "krishi_mitr_db"),
            summary=compact_tool_summary(name, raw),
        )

    if name == "search_agri_knowledge":
        merged, _ = _apply_hint_wins_and_units(name, raw_args, hints, needs_quantity=False)
        mapped = {k: v for k, v in merged.items() if k in ("query", "category", "crop") and v is not None}
        raw = await run_tool("search_agri_knowledge", ctx, mapped)
        env = _tool_result_from_raw(raw, "rag_kb_v1")
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action=raw.get("ui_action"),
            citations=_citations_from_raw(raw, "rag_kb_v1"),
            summary=compact_tool_summary(name, raw),
        )

    if name == "navigate_screen":
        raw_target = str(raw_args.get("target_screen") or "")
        resolved_screen = resolve_allowed_screen(raw_target)
        if resolved_screen is None:
            env = ToolResult(
                ok=False,
                source="navigation",
                error=f"NEEDS_INPUT: unknown screen {raw_target!r}; choose a valid FarmerScreen.",
            )
            return ExecutedToolCall(name, env, summary=f"[{name}: invalid screen {raw_target!r}]")
        mapped = {"target_screen": resolved_screen, "params": raw_args.get("params") or {}}
        raw = await run_tool("open_screen", ctx, mapped)
        env = _tool_result_from_raw(raw, "navigation")
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action=raw.get("ui_action"),
            citations=[],
            summary=compact_tool_summary(name, raw),
        )

    if name == "extract_onboarding_profile":
        district_raw = raw_args.get("district")
        district_slug = None
        district_name = None
        if district_raw:
            if ctx.db is not None:
                try:
                    ent = await resolve_ref(ctx.db, "district", str(district_raw))
                    district_slug = ent.slug
                    district_name = ent.name
                except ResolveError as exc:
                    if exc.ambiguous:
                        return ExecutedToolCall(
                            name,
                            ToolResult(ok=False, source="onboard", error=f"AMBIGUOUS: multiple districts match {district_raw!r}"),
                            summary=f"[{name}: ambiguous district]",
                        )
            else:
                district_slug = str(district_raw)
                district_name = str(district_raw)
        profile_data = {
            "name": raw_args.get("name"),
            "village": raw_args.get("village"),
            "district_id": district_slug,
            "district_name": district_name,
        }
        card = {"type": "ONBOARD_PROFILE", "data": profile_data}
        env = ToolResult(ok=True, data=profile_data, source="onboarding", card=card, error=None)
        return ExecutedToolCall(
            tool_name=name,
            envelope=env,
            ui_action={
                "type": "PREFILL",
                "target_screen": "S3_Profile",
                "cta_label": ctx.t("फॉर्ममध्ये भरा", "फ़ॉर्म में भरें", "Fill profile"),
                "params": {k: v for k, v in {"district_id": district_slug}.items() if v},
            },
            summary=f"[{name}: name={profile_data['name']}, district={district_slug}]",
        )

    return ExecutedToolCall(
        tool_name=name,
        envelope=ToolResult(ok=False, source="agent", error=f"UNKNOWN_TOOL: {name!r}"),
        summary=f"[{name}: unknown tool]",
    )


__all__ = [
    "ExecutedToolCall",
    "agent_tool_schemas",
    "execute_agent_tool",
    "resolve_allowed_screen",
]
