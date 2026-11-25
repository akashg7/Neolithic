"""Safety and grounding guards for the Krishi-Mitr agent loop.

Four mandatory guards (Two-Person Plan p.9):
  1. Number check: every number in the English reply must match a tool result
     (with deterministic paise->rupees, kg->quintals/bori/tons, bps->% conversions).
     A second number check runs after back-translation via `translate_back_checked`.
  2. NO_ADVICE guard: when `window_engine` returns `NO_ADVICE`, the reply must
     never suggest holding or selling and uses the pre-translated template.
  3. Language guard: English-only (no Devanagari) when `TRANSLATE_PIVOT=on`;
     mostly Devanagari for `mr`/`hi` when `TRANSLATE_PIVOT=off`.
  4. Chemicals guard: forbids pesticide/chemical dosage advice and refers the
     farmer to their local Krishi Vigyan Kendra (KVK).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from app.agents.tool_bridge import ExecutedToolCall
from app.nlp.numbers import extract_numbers

_DEVANAGARI_CHAR = re.compile(r"[\u0900-\u097F]")
_ALPHA_CHAR = re.compile(r"[A-Za-z\u0900-\u097F]")

# Careful keyword + dosage patterns for pesticide/chemical advice across en, mr, hi.
_CHEMICAL_PATTERNS = re.compile(
    r"(?i)"
    r"(?:\b(?:pesticide|pesticides|insecticide|insecticides|fungicide|fungicides|"
    r"herbicide|herbicides|weedicide|agrochemical|miticide|bactericide)\b"
    r"|\b(?:chemical\s+(?:spray|dose|dosage|treatment)|spray\s+(?:dose|dosage|medicine)|"
    r"which\s+(?:medicine|chemical|spray).{0,40}(?:use|spray|how\s+much))\b"
    r"|(?:कीटकनाशक|कीटकनाशके|बुरशीनाशक|तणनाशक|कीटनाशक|फफूंदनाशक|खरपतवारनाशी|"
    r"रसायनांच्या\s+मात्र|रसायनों\s+की\s+मात्रा|फवारणी\s+करू|कौन\s*सी\s*दवा.{0,25}कितनी|"
    r"कोणत्या\s+औषधाची.{0,25}फवारणी|कीड़े\s+लग\s+गए.{0,30}दवा))"
)

_HOLD_OR_SELL_DIRECTIVE = re.compile(
    r"(?i)\b(?:you\s+should\s+(?:hold|sell|wait)|i\s+recommend\s+(?:holding|selling|waiting)|"
    r"recommend\s+(?:holding|selling)|best\s+to\s+(?:hold|sell)|sell\s+now|hold\s+for\s+\d+)\b"
)

_NEGATED_DIRECTIVE = re.compile(
    r"(?i)\b(?:cannot|can't|not|never|unable\s+to)\s+(?:advise|recommend|suggest)\b"
)


@dataclass
class GuardFailure:
    guard: str
    reason: str


def is_chemical_query_or_advice(text: str) -> bool:
    """True when text asks for or prescribes pesticides/chemical dosages."""
    if not text:
        return False
    return bool(_CHEMICAL_PATTERNS.search(text))


def has_no_advice_tool_result(executed: list[ExecutedToolCall]) -> bool:
    """True if `compute_sale_window` (or price band) returned `NO_ADVICE`."""
    for item in executed:
        if not item.envelope.ok:
            continue
        data = item.envelope.data or {}
        if data.get("action") == "NO_ADVICE" or data.get("recommendation") == "NO_ADVICE":
            return True
        sw = data.get("sale_window")
        if isinstance(sw, dict) and sw.get("recommendation") == "NO_ADVICE":
            return True
        card = item.envelope.card or {}
        if isinstance(card, dict) and (card.get("data") or {}).get("action") == "NO_ADVICE":
            return True
    return False


def check_no_advice_compliance(reply_text: str, executed: list[ExecutedToolCall]) -> Optional[GuardFailure]:
    if not has_no_advice_tool_result(executed):
        return None
    if _HOLD_OR_SELL_DIRECTIVE.search(reply_text) and not _NEGATED_DIRECTIVE.search(reply_text):
        return GuardFailure(
            guard="NO_ADVICE",
            reason="Reply appears to advise holding or selling despite window_engine returning NO_ADVICE.",
        )
    return None


def check_language_compliance(
    reply_text: str,
    *,
    pivot_on: bool,
    target_lang: str,
) -> Optional[GuardFailure]:
    """Verify reply script obeys the pivot mode."""
    if not reply_text:
        return GuardFailure(guard="language", reason="Empty reply text.")
    if pivot_on or target_lang == "en":
        if _DEVANAGARI_CHAR.search(reply_text):
            return GuardFailure(
                guard="language",
                reason="Reply must be in English only with no Devanagari characters when TRANSLATE_PIVOT=on.",
            )
        return None

    if target_lang in ("mr", "hi"):
        alpha = _ALPHA_CHAR.findall(reply_text)
        if len(alpha) >= 5:
            deva = _DEVANAGARI_CHAR.findall(reply_text)
            if len(deva) / len(alpha) < 0.5:
                return GuardFailure(
                    guard="language",
                    reason=f"Reply for locale={target_lang} must be mostly Devanagari when TRANSLATE_PIVOT=off.",
                )
    return None


def _add_scaled_values(key: str, num: float, allowed: set[float]) -> None:
    k = key.lower()
    allowed.add(num)
    if "paise" in k:
        rupees = num / 100.0
        allowed.add(rupees)
        allowed.add(round(rupees, 2))
        allowed.add(float(int(round(rupees))))
        allowed.add(float(int(num // 100)))
    if k.endswith("_kg") or k in ("quantity_kg", "qty_kg", "stored_quantity_kg", "min_quantity_kg"):
        for divisor in (100.0, 50.0, 1000.0):  # quintal, bori, ton
            conv = num / divisor
            allowed.add(conv)
            allowed.add(round(conv, 2))
            if conv.is_integer():
                allowed.add(float(int(conv)))
    if "bps" in k:
        pct = num / 100.0
        allowed.add(pct)
        allowed.add(round(pct, 2))
        allowed.add(float(int(num // 100)))


_LAKH_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:lakh|lac)s?\b", re.IGNORECASE)
_CRORE_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*crores?\b", re.IGNORECASE)


def _collect_allowed_numbers(obj: Any, allowed: set[float], parent_key: str = "") -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        _add_scaled_values(parent_key, float(obj), allowed)
        return
    if isinstance(obj, str):
        for n in extract_numbers(obj):
            allowed.add(n)
        for m in _LAKH_NUM.finditer(obj):
            allowed.add(float(m.group(1).replace(",", "")) * 100_000.0)
        for m in _CRORE_NUM.finditer(obj):
            allowed.add(float(m.group(1).replace(",", "")) * 10_000_000.0)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            _collect_allowed_numbers(v, allowed, str(k))
        return
    if isinstance(obj, (list, tuple)):
        for item in obj:
            _collect_allowed_numbers(item, allowed, parent_key)


def _has_p10_reference(executed: list[ExecutedToolCall]) -> bool:
    for item in executed:
        if not item.envelope.ok:
            continue
        blob = repr(item.envelope.data)
        if "p10" in blob or "worst_case" in blob:
            return True
    return False


def check_numbers_against_tools(
    reply_text: str,
    executed: list[ExecutedToolCall],
    *,
    user_english_text: str = "",
    hints: Optional[dict[str, Any]] = None,
) -> Optional[GuardFailure]:
    """Ensure every number in `reply_text` is grounded in a tool result (or allowed conversions)."""
    text_to_scan = reply_text
    if _has_p10_reference(executed):
        # Allow the standard plain-language explanation for p10 ("worst 1-in-10 case").
        text_to_scan = re.sub(r"\b1[-\s]in[-\s]10\b", " ", text_to_scan, flags=re.IGNORECASE)

    found = extract_numbers(text_to_scan)
    if not found:
        return None

    allowed: set[float] = set()
    for item in executed:
        if not item.envelope.ok:
            continue
        _collect_allowed_numbers(item.envelope.data, allowed)
        _collect_allowed_numbers(item.envelope.card, allowed)
        _collect_allowed_numbers(item.citations, allowed)

    if user_english_text:
        for n in extract_numbers(user_english_text):
            allowed.add(n)
    if hints:
        _collect_allowed_numbers(hints, allowed)

    unmatched: list[float] = []
    for n in found:
        if not any(abs(n - a) <= 1e-3 for a in allowed):
            unmatched.append(n)

    if unmatched:
        return GuardFailure(
            guard="number_check",
            reason=f"Reply contains numbers {unmatched} not present in tool outputs.",
        )
    return None


__all__ = [
    "GuardFailure",
    "check_language_compliance",
    "check_no_advice_compliance",
    "check_numbers_against_tools",
    "has_no_advice_tool_result",
    "is_chemical_query_or_advice",
]
