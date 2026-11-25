"""Translation layer (Person B provides, Person A calls).

    await to_english(text=..., audio=..., locale_hint=...) -> Translated
    await from_english(texts, target_lang)                 -> list[str]   (one batched call)
    await translate_back_checked(texts, target_lang)       -> (list[str], ok)

Backends (env TRANSLATE_BACKEND):
    stub    (default) fixed English text + fixed hints, no network. Day-1 stub for Person A.
    sarvam  real Sarvam APIs (Saaras speech, Mayura / Sarvam-Translate text).

Env: SARVAM_API_KEY, SARVAM_BASE_URL, SARVAM_STT_MODEL (saaras:v3),
     SARVAM_TRANSLATE_MODEL (mayura:v1), TRANSLATE_PIVOT=on|off,
     TRANSLATE_TIMEOUT_S (2.5), STT_TIMEOUT_S (6), SARVAM_TIMING_LOG (path, optional).

Behaviour (from the plan):
  * Voice in: two parallel STT calls (mode=transcribe -> original, mode=translate -> English).
  * Text in: English is detected locally and skips translation entirely.
  * Hints (quantity, commodity, mandi) are read from the ORIGINAL text before translating.
  * Batched outgoing translation, one retry, short timeouts, every call timed and logged.
  * Fixed safety messages are never translated live (messages.py).
  * TRANSLATE_PIVOT=off: English middle is skipped; the farmer's own text goes to the agent.
Failures raise TranslationUnavailable: Person A catches it and sends the pre-translated
FALLBACK message in the farmer's language.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import statistics
import time
import wave
from collections import defaultdict
from typing import Any, Optional

import httpx

from app.contracts import Translated
from app.nlp.hints import extract_hints
from app.nlp.messages import english_template_key, get_message
from app.nlp.normalize import fold, normalize_text
from app.nlp.numbers import numbers_preserved

log = logging.getLogger("krishi.translate")

LANG_CODES = {"en": "en-IN", "mr": "mr-IN", "hi": "hi-IN"}
MAX_REST_AUDIO_SECONDS = 30.0  # Sarvam REST speech limit; longer needs the batch API
_MODEL_CHAR_LIMIT = {"mayura:v1": 1000, "sarvam-translate:v1": 2000}


class TranslationUnavailable(Exception):
    """Translation failed after the retry. Caller sends the pre-translated FALLBACK."""


class EmptyTranscript(TranslationUnavailable):
    """Speech-to-text returned nothing (silence / noise). Ask the farmer to repeat."""


class AudioTooLong(TranslationUnavailable):
    pass


# --------------------------------------------------------------------------- config
def pivot_enabled() -> bool:
    return os.getenv("TRANSLATE_PIVOT", "on").strip().lower() != "off"


def backend() -> str:
    return os.getenv("TRANSLATE_BACKEND", "stub").strip().lower()


# --------------------------------------------------------------------------- language detection
_DEVA = re.compile(r"[ऀ-ॿ]")
_MR_MARKERS = {fold(w) for w in (
    "आहे", "आहेत", "मला", "माझा", "माझी", "माझे", "माझ्याकडे", "काय", "किती", "करू", "कसा", "कसे",
    "कशी", "नाही", "विकू", "थांबू", "पाहिजे", "द्या", "दाखव", "तुम्ही", "आत्ता", "पुढच्या", "आणि",
)}
_HI_MARKERS = {fold(w) for w in (
    "है", "हैं", "मुझे", "मेरा", "मेरे", "मेरी", "क्या", "कितना", "कितने", "करूं", "कैसे", "नहीं",
    "बेचूं", "चाहिए", "दिखाओ", "कौन", "और", "आप", "के", "की", "रहा",
)}
# markers that exist in only one language (used to break ties)
_MR_ONLY = _MR_MARKERS - _HI_MARKERS
_HI_ONLY = _HI_MARKERS - _MR_MARKERS
_ROMAN_INDIC = {
    "bhav", "bhaav", "bhaw", "kitna", "kitni", "kitne", "kya", "kaise", "aahe", "ahe", "mala", "mera",
    "meri", "mere", "mujhe", "chahiye", "nahi", "batao", "bataiye", "dikhao", "bechna", "becho",
    "vikaycha", "vikayche", "kay", "kiti", "majha", "majhya", "dar", "rate", "mandi", "aaj", "kal",
    "hai", "hain", "karu", "kara", "dya",
}
_ROMAN_STRONG = _ROMAN_INDIC - {"rate", "mandi", "dar", "aaj", "kal"}  # ambiguous with English
_EN_STOP = {"the", "is", "of", "what", "my", "i", "to", "at", "for", "and", "should", "me", "price",
            "sell", "today", "how", "do", "can", "show", "a", "in", "on", "it", "have", "want"}
_TOKENS = re.compile(r"[\wऀ-ॿ]+")


def detect_language(text: str, locale_hint: Optional[str] = None) -> Optional[str]:
    """'en' | 'mr' | 'hi' | 'indic' (Indic but unsure which) | None (undecided).

    Local and free. 'en' means translation can be skipped. Anything else goes to Sarvam.
    """
    norm = normalize_text(text)
    if not norm:
        return None
    tokens = _TOKENS.findall(fold(norm))
    if _DEVA.search(norm):
        mr = sum(t in _MR_MARKERS for t in tokens)
        hi = sum(t in _HI_MARKERS for t in tokens)
        mr_only = sum(t in _MR_ONLY for t in tokens)
        hi_only = sum(t in _HI_ONLY for t in tokens)
        if mr_only != hi_only:
            return "mr" if mr_only > hi_only else "hi"
        if mr != hi:
            return "mr" if mr > hi else "hi"
        return locale_hint if locale_hint in ("mr", "hi") else "indic"
    roman = sum(t in _ROMAN_STRONG for t in tokens)
    english = sum(t in _EN_STOP for t in tokens)
    if roman and roman >= english:
        return "indic"  # romanised Hindi/Marathi ("kanda bhav kay")
    return "en"


# --------------------------------------------------------------------------- timing log
_TIMINGS: dict[str, list[float]] = defaultdict(list)
_ERRORS: dict[str, int] = defaultdict(int)


def _record(endpoint: str, ms: float, ok: bool, size: int) -> None:
    _TIMINGS[endpoint].append(ms)
    if not ok:
        _ERRORS[endpoint] += 1
    log.info("sarvam %s %.0fms ok=%s size=%s", endpoint, ms, ok, size)
    path = os.getenv("SARVAM_TIMING_LOG")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.time(), "endpoint": endpoint, "ms": round(ms, 1),
                                    "ok": ok, "size": size}) + "\n")
        except OSError:  # logging must never break a turn
            pass


def timing_summary() -> dict[str, dict[str, float]]:
    """Per-endpoint call count, error count, p50/p95/max in ms. Use for the Day-1/2 latency check."""
    out = {}
    for ep, xs in _TIMINGS.items():
        xs_sorted = sorted(xs)
        p95 = xs_sorted[min(len(xs_sorted) - 1, int(round(0.95 * (len(xs_sorted) - 1))))]
        out[ep] = {"n": len(xs), "errors": _ERRORS[ep], "p50_ms": round(statistics.median(xs), 1),
                   "p95_ms": round(p95, 1), "max_ms": round(max(xs), 1)}
    return out


def reset_timings() -> None:
    _TIMINGS.clear()
    _ERRORS.clear()


# --------------------------------------------------------------------------- Sarvam client
def _sniff_audio(audio: bytes) -> tuple[str, str]:
    h = audio[:12]
    if h[:4] == b"RIFF":
        return "audio.wav", "audio/wav"
    if h[:4] == b"OggS":
        return "audio.ogg", "audio/ogg"
    if h[:4] == b"\x1aE\xdf\xa3":
        return "audio.webm", "audio/webm"
    if h[:3] == b"ID3" or h[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio.mp3", "audio/mpeg"
    if h[4:8] == b"ftyp":
        return "audio.m4a", "audio/mp4"
    if h[:4] == b"fLaC":
        return "audio.flac", "audio/flac"
    return "audio.wav", "audio/wav"


def _wav_seconds(audio: bytes) -> Optional[float]:
    if audio[:4] != b"RIFF":
        return None
    try:
        with wave.open(io.BytesIO(audio)) as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError):
        return None


def _short(code: Optional[str]) -> Optional[str]:
    return code.split("-")[0].lower() if code else None


class SarvamClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 transport: Optional[httpx.AsyncBaseTransport] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.base_url = (base_url or os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")).rstrip("/")
        self.stt_model = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
        self.translate_model = os.getenv("SARVAM_TRANSLATE_MODEL", "mayura:v1")
        self.text_timeout = float(os.getenv("TRANSLATE_TIMEOUT_S", "2.5"))
        self.stt_timeout = float(os.getenv("STT_TIMEOUT_S", "6"))
        self._http = httpx.AsyncClient(base_url=self.base_url, transport=transport)

    @property
    def char_limit(self) -> int:
        return _MODEL_CHAR_LIMIT.get(self.translate_model, 1000)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _post(self, endpoint: str, *, timeout: float, size: int, **kwargs: Any) -> dict:
        """POST with one retry on timeout / transport error / 429 / 5xx. Every attempt is timed."""
        if not self.api_key:
            raise TranslationUnavailable("SARVAM_API_KEY is not set")
        headers = {"api-subscription-key": self.api_key}
        last: Exception = RuntimeError("unreachable")
        for attempt in range(2):
            t0 = time.perf_counter()
            try:
                r = await self._http.post(endpoint, headers=headers, timeout=timeout, **kwargs)
                ms = (time.perf_counter() - t0) * 1000
                if r.status_code == 429 or r.status_code >= 500:
                    _record(endpoint, ms, False, size)
                    last = TranslationUnavailable(f"{endpoint} -> HTTP {r.status_code}")
                elif r.status_code >= 400:
                    _record(endpoint, ms, False, size)
                    raise TranslationUnavailable(f"{endpoint} -> HTTP {r.status_code}: {r.text[:200]}")
                else:
                    _record(endpoint, ms, True, size)
                    return r.json()
            except (httpx.TimeoutException, httpx.TransportError) as e:
                _record(endpoint, (time.perf_counter() - t0) * 1000, False, size)
                last = e
            if attempt == 0:
                await asyncio.sleep(0.15)
        raise TranslationUnavailable(f"{endpoint} failed after retry: {last!r}") from last

    # -- text -------------------------------------------------------------------
    async def translate(self, text: str, source: str, target: str) -> tuple[str, Optional[str]]:
        """-> (translated_text, detected source language short code). source may be 'auto'."""
        body: dict[str, Any] = {
            "input": text,
            "source_language_code": "auto" if source == "auto" else LANG_CODES.get(source, f"{source}-IN"),
            "target_language_code": LANG_CODES.get(target, f"{target}-IN"),
            "model": self.translate_model,
        }
        body["numerals_format"] = "international"  # keep 1000, not १०००  (both models support it)
        if self.translate_model.startswith("mayura"):
            body["mode"] = "modern-colloquial"  # sarvam-translate:v1 supports formal mode only
        elif source == "auto":
            raise TranslationUnavailable("sarvam-translate needs an explicit source language")
        data = await self._post("/translate", timeout=self.text_timeout, size=len(text), json=body)
        out = data.get("translated_text")
        if out is None:
            raise TranslationUnavailable("translate response had no translated_text")
        return out, _short(data.get("source_language_code"))

    # -- speech -----------------------------------------------------------------
    async def stt(self, audio: bytes, mode: str, locale_hint: Optional[str]) -> tuple[str, Optional[str]]:
        fname, mime = _sniff_audio(audio)
        data = {"model": self.stt_model, "mode": mode}
        if locale_hint in LANG_CODES:
            data["language_code"] = LANG_CODES[locale_hint]
        res = await self._post("/speech-to-text", timeout=self.stt_timeout, size=len(audio),
                               data=data, files={"file": (fname, audio, mime)})
        return (res.get("transcript") or "").strip(), _short(res.get("language_code"))


_client: Optional[SarvamClient] = None


def get_client() -> SarvamClient:
    global _client
    if _client is None:
        _client = SarvamClient()
    return _client


def set_client(client: Optional[SarvamClient]) -> None:
    """Tests / app startup can inject a client (e.g. with a mock transport)."""
    global _client
    _client = client


# --------------------------------------------------------------------------- helpers
def _chunk_text(text: str, limit: int) -> list[str]:
    """Split on sentence ends so each piece fits the API's character limit."""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    for sent in re.split(r"(?<=[.!?।])\s+", text):
        while len(sent) > limit:  # one very long sentence: hard split on a space
            cut = sent.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            pieces.append(sent[:cut])
            sent = sent[cut:].lstrip()
        if sent:
            pieces.append(sent)
    chunks: list[str] = []
    cur = ""
    for p in pieces:
        if cur and len(cur) + 1 + len(p) > limit:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        chunks.append(cur)
    return chunks


async def _translate_long(client: SarvamClient, text: str, source: str, target: str) -> tuple[str, Optional[str]]:
    chunks = _chunk_text(text, client.char_limit)
    results = await asyncio.gather(*(client.translate(c, source, target) for c in chunks))
    return " ".join(r[0] for r in results), results[0][1]


# --------------------------------------------------------------------------- public API: stub
STUB_ENGLISH = "I have 20 bags of onion. Should I sell now at Lasalgaon?"
STUB_HINTS = {"quantity_kg": 1000, "commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}


async def _stub_to_english(text, audio, locale_hint) -> Translated:
    if text is not None and detect_language(text, locale_hint) == "en":
        return Translated(original=text, english=normalize_text(text), source_lang="en",
                          hints=extract_hints(text))
    return Translated(original=text or "<audio>", english=STUB_ENGLISH,
                      source_lang=locale_hint if locale_hint in ("mr", "hi") else "mr",
                      hints=dict(STUB_HINTS))


async def _stub_from_english(texts: list[str], target_lang: str) -> list[str]:
    out = []
    for t in texts:
        key = english_template_key(t)
        out.append(get_message(key, target_lang) if key else (t if target_lang == "en" else f"[{target_lang}] {t}"))
    return out


# --------------------------------------------------------------------------- public API
async def to_english(text: Optional[str] = None, audio: Optional[bytes] = None,
                     locale_hint: Optional[str] = None) -> Translated:
    """Farmer's text or audio -> original + English + hints (hints come from the original)."""
    if text is None and audio is None:
        raise ValueError("to_english needs text or audio")
    if backend() == "stub":
        return await _stub_to_english(text, audio, locale_hint)
    client = get_client()
    pivot = pivot_enabled()

    # ---- voice: original + English in parallel --------------------------------
    if audio is not None:
        secs = _wav_seconds(audio)
        if secs is not None and secs > MAX_REST_AUDIO_SECONDS:
            raise AudioTooLong(f"{secs:.1f}s audio; REST limit is {MAX_REST_AUDIO_SECONDS:.0f}s")
        jobs = [client.stt(audio, "transcribe", locale_hint)]
        if pivot:
            jobs.append(client.stt(audio, "translate", locale_hint))
        res = await asyncio.gather(*jobs, return_exceptions=True)
        orig_res, eng_res = res[0], (res[1] if pivot else None)
        if isinstance(orig_res, Exception) and (eng_res is None or isinstance(eng_res, Exception)):
            raise TranslationUnavailable(f"speech-to-text failed: {orig_res!r}") from orig_res
        if not isinstance(orig_res, Exception):
            original, lang = orig_res
        else:  # transcribe failed, translate worked: original unknown
            original, lang = eng_res[0], eng_res[1]
        if not original:
            raise EmptyTranscript("no speech detected")
        lang = lang or detect_language(original, locale_hint) or locale_hint or "mr"
        hints = extract_hints(original)
        if not pivot or lang == "en":
            return Translated(original=original, english=original, source_lang=lang, hints=hints)
        if eng_res is not None and not isinstance(eng_res, Exception) and eng_res[0]:
            return Translated(original=original, english=eng_res[0], source_lang=lang, hints=hints)
        # translate-mode failed: translate the transcript as text (slower, but works)
        english, _ = await _translate_long(client, normalize_text(original), lang if lang in LANG_CODES else "auto", "en")
        return Translated(original=original, english=english, source_lang=lang, hints=hints)

    # ---- text -------------------------------------------------------------------
    assert text is not None
    original = text
    hints = extract_hints(original)
    lang = detect_language(original, locale_hint)
    if lang == "en":
        return Translated(original=original, english=normalize_text(original), source_lang="en", hints=hints)
    if not pivot:
        return Translated(original=original, english=original,
                          source_lang=lang if lang in ("mr", "hi") else (locale_hint or "mr"), hints=hints)
    source = lang if lang in ("mr", "hi") else "auto"
    english, detected = await _translate_long(client, normalize_text(original), source, "en")
    final_lang = lang if lang in ("mr", "hi") else (detected or locale_hint or "hi")
    if final_lang == "en":  # Sarvam says it was English after all
        english = normalize_text(original)
    return Translated(original=original, english=english, source_lang=final_lang, hints=hints)


async def from_english(texts: list[str], target_lang: str) -> list[str]:
    """English replies -> farmer's language in ONE batched call. Order and count preserved.

    Exact fixed templates (messages.py) are swapped for their reviewed translation
    without calling the API. Raises TranslationUnavailable if the API fails after retry.
    """
    if not texts or target_lang == "en":
        return list(texts)
    if backend() == "stub":
        return await _stub_from_english(texts, target_lang)

    out: list[Optional[str]] = [None] * len(texts)
    todo: list[int] = []
    for i, t in enumerate(texts):
        key = english_template_key(t) if t else None
        if key:
            out[i] = get_message(key, target_lang)
        elif not t or not t.strip():
            out[i] = t
        else:
            todo.append(i)
    if todo:
        client = get_client()
        clean = {i: re.sub(r"\s*\n+\s*", " ", texts[i]).strip() for i in todo}
        # pack as many items per call as the limit allows (normally exactly one call)
        batches: list[list[int]] = []
        cur: list[int] = []
        size = 0
        for i in todo:
            n = len(clean[i]) + 1
            if cur and size + n > client.char_limit:
                batches.append(cur)
                cur, size = [], 0
            cur.append(i)
            size += n
        if cur:
            batches.append(cur)

        async def run(batch: list[int]) -> None:
            joined = "\n".join(clean[i] for i in batch)
            translated, _ = await client.translate(joined, "en", target_lang) if len(joined) <= client.char_limit \
                else await _translate_long(client, joined, "en", target_lang)
            lines = [ln.strip() for ln in translated.split("\n") if ln.strip()]
            if len(lines) == len(batch):
                for i, ln in zip(batch, lines):
                    out[i] = ln
            else:  # model merged or split lines: translate each item on its own
                log.warning("batched translation returned %d lines for %d items; retrying individually",
                            len(lines), len(batch))
                singles = await asyncio.gather(*(_translate_long(client, clean[i], "en", target_lang) for i in batch))
                for i, (tt, _) in zip(batch, singles):
                    out[i] = tt

        await asyncio.gather(*(run(b) for b in batches))
    return [o if o is not None else "" for o in out]


async def translate_back_checked(texts: list[str], target_lang: str) -> tuple[list[str], bool]:
    """from_english + the second number check (plan: 'numbers are checked twice').

    Returns (translated, ok). If any text lost a number, those items are retried once;
    still failing -> ok=False and the caller sends the pre-translated FALLBACK built from
    card data. Fixed templates carry no numbers from the model so always pass.
    """
    if target_lang == "en":
        return list(texts), True
    translated = await from_english(texts, target_lang)
    bad = [i for i, (s, t) in enumerate(zip(texts, translated)) if not numbers_preserved(s, t)]
    if bad:
        retried = await from_english([texts[i] for i in bad], target_lang)
        for i, t in zip(bad, retried):
            translated[i] = t
        bad = [i for i in bad if not numbers_preserved(texts[i], translated[i])]
    return translated, not bad
