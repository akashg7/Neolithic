"""Name lexicon: commodity and mandi names in mr / hi / en / romanized forms.

    resolve_commodity("कांदा")        -> "cmd_onion"
    resolve_commodity("kanda")        -> "cmd_onion"
    resolve_mandi("लासलगाव")           -> "mkt_lasalgaon"
    resolve_commodity("zzz")          -> None          (below cutoff: never guess)
    scan("माझा कांद्याचा भाव लासलगाव")  -> [Match(commodity,cmd_onion), Match(mandi,mkt_lasalgaon)]

Matching order: exact alias -> stem + case suffix (कांद्याचा) -> fuzzy (rapidfuzz)
above a cutoff. If two different IDs are equally good, resolve returns None and
`candidates()` lists them, so the agent asks the farmer instead of guessing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz, process

from app.nlp.normalize import fold

_DEFAULT = json.loads((Path(__file__).parent / "data" / "lexicon.json").read_text("utf-8"))

KINDS = ("commodity", "mandi")
_SECTION = {"commodity": "commodities", "mandi": "mandis"}

# Marathi / Hindi case suffixes (folded) that can follow a stem.
_SUFFIXES = tuple(
    fold(s)
    for s in (
        "", "चा", "ची", "चे", "चं", "च्या", "ला", "ना", "ने", "त", "मध्ये", "मधे", "में",
        "का", "की", "के", "वर", "साठी", "ांचा", "ांची", "ांचे", "ाचा", "ाची", "ाचे",
        "ाला", "ाने", "ात", "ाच्या", "ांना", "ही", "च", "ं",
    )
)

RESOLVE_CUTOFF = 85  # resolve_*(): a single name
SCAN_CUTOFF = 90  # scan(): names inside sentences (stricter, fewer false hints)
TIE_MARGIN = 3  # two IDs this close => ambiguous
_MIN_FUZZY_LEN = 5
_TOKEN = re.compile(r"[\wऀ-ॿ]+")
# Words that follow a mandi name but are not part of it ("Lasalgaon market").
_NOISE = {fold(w) for w in ("market", "mandi", "apmc", "bazaar", "bazar", "मंडी", "बाजार", "बाजारात", "समिती", "मार्केट")}


@dataclass(frozen=True)
class Match:
    kind: str  # commodity | mandi
    id: str
    matched: str  # folded text that matched
    score: float  # 100 = exact / stem match


class Lexicon:
    def __init__(self, data: Optional[dict] = None):
        data = data or _DEFAULT
        self._alias: dict[str, dict[str, set[str]]] = {k: {} for k in KINDS}
        self._stem: dict[str, dict[str, set[str]]] = {k: {} for k in KINDS}
        for kind in KINDS:
            for _id, spec in data[_SECTION[kind]].items():
                for a in spec["aliases"]:
                    self._alias[kind].setdefault(fold(a), set()).add(_id)
                for st in spec.get("stems", []):
                    self._stem[kind].setdefault(fold(st), set()).add(_id)
        self._fuzzy_keys = {
            k: [a for a in self._alias[k] if len(a) >= _MIN_FUZZY_LEN] for k in KINDS
        }

    # -- core -------------------------------------------------------------------
    def _exact(self, kind: str, text: str) -> set[str]:
        ids = set(self._alias[kind].get(text, ()))
        if ids:
            return ids
        for stem, sids in self._stem[kind].items():
            if text.startswith(stem) and text[len(stem):] in _SUFFIXES:
                ids |= sids
        return ids

    def _fuzzy(self, kind: str, text: str, cutoff: float) -> list[tuple[str, float]]:
        """[(id, best score)] for IDs scoring >= cutoff, best first."""
        if len(text) < _MIN_FUZZY_LEN or not self._fuzzy_keys[kind]:
            return []
        best: dict[str, float] = {}
        for alias, score, _ in process.extract(
            text, self._fuzzy_keys[kind], scorer=fuzz.ratio, score_cutoff=cutoff, limit=6
        ):
            for _id in self._alias[kind][alias]:
                best[_id] = max(best.get(_id, 0.0), score)
        return sorted(best.items(), key=lambda kv: -kv[1])

    def candidates(self, kind: str, name: str, cutoff: float = RESOLVE_CUTOFF) -> list[str]:
        """All IDs the name could mean (0 = unknown, 1 = resolved, 2+ = ambiguous)."""
        text = fold(name)
        kept = [t for t in text.split() if t not in _NOISE]
        text = " ".join(kept) if kept else text
        if not text:
            return []
        ids = self._exact(kind, text)
        if ids:
            return sorted(ids)
        ranked = self._fuzzy(kind, text, cutoff)
        if not ranked:
            return []
        top = ranked[0][1]
        return [i for i, s in ranked if top - s <= TIE_MARGIN]

    def resolve(self, kind: str, name: str, cutoff: float = RESOLVE_CUTOFF) -> Optional[str]:
        c = self.candidates(kind, name, cutoff)
        return c[0] if len(c) == 1 else None

    # -- sentence scan ------------------------------------------------------------
    def scan(self, text: str, max_ngram: int = 3) -> list[Match]:
        tokens = _TOKEN.findall(fold(text))
        out: list[Match] = []
        i = 0
        while i < len(tokens):
            hit = None
            for n in range(min(max_ngram, len(tokens) - i), 0, -1):
                gram = " ".join(tokens[i : i + n])
                for kind in KINDS:
                    ids = self._exact(kind, gram)
                    if ids:
                        hit = (n, [Match(kind, _id, gram, 100.0) for _id in sorted(ids)])
                        break
                if hit:
                    break
                if n <= 2:  # fuzzy only on short n-grams
                    for kind in KINDS:
                        ranked = self._fuzzy(kind, gram, SCAN_CUTOFF)
                        if ranked:
                            top = ranked[0][1]
                            hit = (n, [Match(kind, _id, gram, s) for _id, s in ranked if top - s <= TIE_MARGIN])
                            break
                if hit:
                    break
            if hit:
                out.extend(hit[1])
                i += hit[0]
            else:
                i += 1
        return out


_lex = Lexicon()


def resolve_commodity(name: str) -> Optional[str]:
    """'कांदा', 'kanda', 'onion' -> 'cmd_onion'. None if unknown/ambiguous."""
    return _lex.resolve("commodity", name)


def resolve_mandi(name: str) -> Optional[str]:
    """'लासलगाव' -> 'mkt_lasalgaon'. None if unknown/ambiguous."""
    return _lex.resolve("mandi", name)


def commodity_candidates(name: str) -> list[str]:
    return _lex.candidates("commodity", name)


def mandi_candidates(name: str) -> list[str]:
    return _lex.candidates("mandi", name)


def scan_names(text: str) -> list[Match]:
    return _lex.scan(text)
