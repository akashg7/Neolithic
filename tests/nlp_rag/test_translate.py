import asyncio
import io
import json
import struct
import wave

import httpx
import pytest

from app.nlp import translate as T
from app.nlp.numbers import extract_numbers, numbers_preserved


def run(coro):
    return asyncio.run(coro)


class Mock:
    """httpx MockTransport that records requests and plays scripted responses."""

    def __init__(self, handler):
        self.calls = []
        self.handler = handler
        self.transport = httpx.MockTransport(self._h)

    def _h(self, request: httpx.Request):
        body = request.content
        rec = {"path": request.url.path, "headers": dict(request.headers), "raw": body}
        if request.headers.get("content-type", "").startswith("application/json"):
            rec["json"] = json.loads(body)
        else:
            rec["form"] = body.decode("latin-1")
        self.calls.append(rec)
        return self.handler(rec, len(self.calls))


@pytest.fixture(autouse=True)
def sarvam_env(monkeypatch):
    monkeypatch.setenv("TRANSLATE_BACKEND", "sarvam")
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    monkeypatch.setenv("TRANSLATE_PIVOT", "on")
    monkeypatch.delenv("SARVAM_TIMING_LOG", raising=False)
    T.reset_timings()
    yield
    T.set_client(None)


def install(handler) -> Mock:
    m = Mock(handler)
    T.set_client(T.SarvamClient(transport=m.transport))
    return m


def ok(**payload):
    return httpx.Response(200, json=payload)


def wav_bytes(seconds: float, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(seconds * rate))
    return buf.getvalue()


# ----------------------------------------------------------------------------- detection
@pytest.mark.parametrize(
    "text,lang",
    [
        ("माझा २० बोरी कांदा लासलगावला विकायचा आहे", "mr"),
        ("मला कांद्याचा भाव किती आहे ते सांगा", "mr"),
        ("मुझे 5 क्विंटल प्याज़ नासिक में बेचना है", "hi"),
        ("आज प्याज का भाव क्या है", "hi"),
        ("What is the price of onion at Lasalgaon", "en"),
        ("sell 20 bags now?", "en"),
        ("kanda bhav kay aahe", "indic"),
        ("mujhe pyaz ka rate batao", "indic"),
    ],
)
def test_detect_language(text, lang):
    assert T.detect_language(text) == lang


def test_detect_uses_locale_hint_on_tie():
    assert T.detect_language("कांदा", "mr") == "mr"
    assert T.detect_language("कांदा") == "indic"


# ----------------------------------------------------------------------------- text in
def test_text_marathi_translates_and_hints_come_from_original():
    m = install(lambda rec, n: ok(translated_text="I have 20 bags of onion, should I sell at Lasalgaon?",
                                  source_language_code="mr-IN"))
    r = run(T.to_english(text="माझ्याकडे २० बोरी कांदा आहे, लासलगावला विकू का?"))
    assert r.source_lang == "mr"
    assert r.english.startswith("I have 20 bags")
    assert r.original.startswith("माझ्याकडे")
    assert r.hints == {"quantity_kg": 1000, "commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}
    assert len(m.calls) == 1
    c = m.calls[0]
    assert c["path"] == "/translate"
    assert c["headers"]["api-subscription-key"] == "test-key"
    assert c["json"]["source_language_code"] == "mr-IN"
    assert c["json"]["target_language_code"] == "en-IN"
    assert c["json"]["numerals_format"] == "international"
    assert "20 बोरी" in c["json"]["input"]  # normalised digits sent, not Devanagari


def test_text_english_skips_translation_entirely():
    m = install(lambda rec, n: pytest.fail("no API call expected"))
    r = run(T.to_english(text="Price of onion at Lasalgaon for 1000 kg"))
    assert r.source_lang == "en" and r.english.startswith("Price of onion")
    assert r.hints == {"quantity_kg": 1000, "commodity": "cmd_onion", "mandi": "mkt_lasalgaon"}
    assert m.calls == []


def test_text_romanised_uses_auto_and_reports_detected_language():
    m = install(lambda rec, n: ok(translated_text="what is the onion price", source_language_code="hi-IN"))
    r = run(T.to_english(text="pyaz ka bhav kya hai"))
    assert m.calls[0]["json"]["source_language_code"] == "auto"
    assert r.source_lang == "hi"


def test_pivot_off_sends_original_to_agent_with_no_api_call(monkeypatch):
    monkeypatch.setenv("TRANSLATE_PIVOT", "off")
    m = install(lambda rec, n: pytest.fail("no API call expected"))
    r = run(T.to_english(text="माझा २० बोरी कांदा लासलगावला विकायचा आहे"))
    assert r.english == r.original and r.source_lang == "mr"
    assert r.hints["quantity_kg"] == 1000
    assert m.calls == []


def test_long_text_is_chunked_under_the_limit():
    long_text = "माझा कांदा आहे. " * 200  # ~3000 chars
    m = install(lambda rec, n: ok(translated_text="piece", source_language_code="mr-IN"))
    r = run(T.to_english(text=long_text))
    assert len(m.calls) > 1
    assert all(len(c["json"]["input"]) <= 1000 for c in m.calls)
    assert r.english.count("piece") == len(m.calls)


def test_chunk_text_hard_splits_a_single_long_sentence():
    chunks = T._chunk_text("word " * 500, 100)
    assert all(len(c) <= 100 for c in chunks)
    assert " ".join(chunks).split() == ("word " * 500).split()


# ----------------------------------------------------------------------------- voice in
def test_voice_two_parallel_calls_original_and_english():
    def handler(rec, n):
        mode = "translate" if "translate" in rec["form"].split('name="mode"')[1][:30] else "transcribe"
        if mode == "transcribe":
            return ok(transcript="माझ्याकडे २० बोरी कांदा आहे", language_code="mr-IN")
        return ok(transcript="I have 20 bags of onion", language_code="en-IN")

    m = install(handler)
    r = run(T.to_english(audio=wav_bytes(2.0)))
    assert len(m.calls) == 2
    assert {c["path"] for c in m.calls} == {"/speech-to-text"}
    forms = " ".join(c["form"] for c in m.calls)
    assert 'name="mode"' in forms and "saaras:v3" in forms
    assert r.original.startswith("माझ्याकडे") and r.english == "I have 20 bags of onion"
    assert r.source_lang == "mr"
    assert r.hints["quantity_kg"] == 1000 and r.hints["commodity"] == "cmd_onion"


def test_voice_translate_mode_fails_falls_back_to_text_translation():
    def handler(rec, n):
        if rec["path"] == "/translate":
            return ok(translated_text="I have 20 bags of onion", source_language_code="mr-IN")
        if "translate" in rec["form"].split('name="mode"')[1][:30]:
            return httpx.Response(400, text="bad")
        return ok(transcript="माझ्याकडे २० बोरी कांदा आहे", language_code="mr-IN")

    install(handler)
    r = run(T.to_english(audio=wav_bytes(1.0)))
    assert r.english == "I have 20 bags of onion" and r.original.startswith("माझ्याकडे")


def test_voice_pivot_off_makes_one_call(monkeypatch):
    monkeypatch.setenv("TRANSLATE_PIVOT", "off")
    m = install(lambda rec, n: ok(transcript="माझा कांदा", language_code="mr-IN"))
    r = run(T.to_english(audio=wav_bytes(1.0)))
    assert len(m.calls) == 1 and r.english == r.original


def test_voice_empty_transcript():
    install(lambda rec, n: ok(transcript="  ", language_code="unknown"))
    with pytest.raises(T.EmptyTranscript):
        run(T.to_english(audio=wav_bytes(1.0)))


def test_voice_too_long_wav_rejected_before_any_call():
    m = install(lambda rec, n: pytest.fail("no API call expected"))
    with pytest.raises(T.AudioTooLong):
        run(T.to_english(audio=wav_bytes(31.0, rate=1000)))
    assert m.calls == []


def test_needs_text_or_audio():
    with pytest.raises(ValueError):
        run(T.to_english())


# ----------------------------------------------------------------------------- retry / failure / timing
def test_retries_once_on_5xx_then_succeeds():
    def handler(rec, n):
        return httpx.Response(503) if n == 1 else ok(translated_text="ok", source_language_code="mr-IN")

    m = install(handler)
    r = run(T.to_english(text="माझा कांदा आहे"))
    assert r.english == "ok" and len(m.calls) == 2


def test_two_failures_raise_translation_unavailable():
    m = install(lambda rec, n: httpx.Response(500))
    with pytest.raises(T.TranslationUnavailable):
        run(T.to_english(text="माझा कांदा आहे"))
    assert len(m.calls) == 2


def test_4xx_is_not_retried():
    m = install(lambda rec, n: httpx.Response(401, text="bad key"))
    with pytest.raises(T.TranslationUnavailable):
        run(T.to_english(text="माझा कांदा आहे"))
    assert len(m.calls) == 1


def test_timeout_is_retried_then_raises():
    def handler(rec, n):
        raise httpx.ReadTimeout("slow")

    m = install(handler)
    with pytest.raises(T.TranslationUnavailable):
        run(T.to_english(text="माझा कांदा आहे"))
    assert len(m.calls) == 2


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY")
    T.set_client(T.SarvamClient(api_key=""))
    with pytest.raises(T.TranslationUnavailable):
        run(T.to_english(text="माझा कांदा आहे"))


def test_every_call_is_timed(tmp_path, monkeypatch):
    log = tmp_path / "timing.jsonl"
    monkeypatch.setenv("SARVAM_TIMING_LOG", str(log))
    install(lambda rec, n: ok(translated_text="x", source_language_code="mr-IN"))
    for _ in range(3):
        run(T.to_english(text="माझा कांदा आहे"))
    s = T.timing_summary()["/translate"]
    assert s["n"] == 3 and s["errors"] == 0 and s["p95_ms"] >= s["p50_ms"] >= 0
    rows = [json.loads(x) for x in log.read_text().splitlines()]
    assert len(rows) == 3 and rows[0]["endpoint"] == "/translate"


# ----------------------------------------------------------------------------- from_english
def test_from_english_batches_into_one_call_and_keeps_order():
    m = install(lambda rec, n: ok(translated_text="उत्तर एक\nउत्तर दोन\nउत्तर तीन", source_language_code="en-IN"))
    out = run(T.from_english(["Reply one", "Reply two", "Reply three"], "mr"))
    assert out == ["उत्तर एक", "उत्तर दोन", "उत्तर तीन"]
    assert len(m.calls) == 1
    assert m.calls[0]["json"]["input"] == "Reply one\nReply two\nReply three"
    assert m.calls[0]["json"]["target_language_code"] == "mr-IN"


def test_from_english_line_count_mismatch_falls_back_to_individual_calls():
    def handler(rec, n):
        if n == 1:
            return ok(translated_text="सगळे एकत्र", source_language_code="en-IN")
        return ok(translated_text=f"t{n}", source_language_code="en-IN")

    m = install(handler)
    out = run(T.from_english(["A one", "B two"], "mr"))
    assert len(m.calls) == 3 and len(out) == 2 and all(out)


def test_from_english_fixed_templates_skip_the_api():
    m = install(lambda rec, n: pytest.fail("no API call expected"))
    out = run(T.from_english(["Which mandi do you want to check?"], "mr"))
    assert out == ["कोणत्या मंडीचा भाव पाहायचा आहे?"] and m.calls == []


def test_from_english_english_target_and_empty():
    m = install(lambda rec, n: pytest.fail("no API call expected"))
    assert run(T.from_english(["hello"], "en")) == ["hello"]
    assert run(T.from_english([], "mr")) == []


def test_from_english_mixes_templates_and_live_text():
    m = install(lambda rec, n: ok(translated_text="किंमत १८०० रुपये", source_language_code="en-IN"))
    out = run(T.from_english(["Which mandi do you want to check?", "Price is 1800 rupees"], "mr"))
    assert out[0].startswith("कोणत्या") and out[1] == "किंमत १८०० रुपये" and len(m.calls) == 1


def test_from_english_multiline_input_is_flattened():
    m = install(lambda rec, n: ok(translated_text="एक\nदोन", source_language_code="en-IN"))
    run(T.from_english(["line a\nline b", "second"], "mr"))
    assert m.calls[0]["json"]["input"] == "line a line b\nsecond"


def test_from_english_failure_raises():
    install(lambda rec, n: httpx.Response(500))
    with pytest.raises(T.TranslationUnavailable):
        run(T.from_english(["Price is 1800 rupees"], "mr"))


# ----------------------------------------------------------------------------- number check after translating back
def test_translate_back_checked_passes_when_numbers_survive():
    install(lambda rec, n: ok(translated_text="भाव १८०० रुपये आहे", source_language_code="en-IN"))
    out, good = run(T.translate_back_checked(["Price is 1800 rupees"], "mr"))
    assert good and out == ["भाव १८०० रुपये आहे"]


def test_translate_back_checked_retries_once_then_succeeds():
    def handler(rec, n):
        return ok(translated_text="भाव आहे" if n == 1 else "भाव 1800 रुपये आहे", source_language_code="en-IN")

    m = install(handler)
    out, good = run(T.translate_back_checked(["Price is 1800 rupees"], "mr"))
    assert good and "1800" in out[0] and len(m.calls) == 2


def test_translate_back_checked_gives_up_after_retry():
    m = install(lambda rec, n: ok(translated_text="भाव खूप आहे", source_language_code="en-IN"))
    out, good = run(T.translate_back_checked(["Price is 1800 rupees"], "mr"))
    assert not good and len(m.calls) == 2


# ----------------------------------------------------------------------------- numbers util
def test_extract_numbers_handles_devanagari_commas_decimals():
    assert extract_numbers("२० बोरी at ₹1,800 and 12.5%") == [20.0, 1800.0, 12.5]


def test_numbers_preserved_cases():
    assert numbers_preserved("Price 1800 for 20 bags", "भाव १८०० रुपये, २० बोरी")
    assert not numbers_preserved("Price 1800 for 20 bags", "भाव १८०० रुपये")
    assert not numbers_preserved("20 and 20", "20")  # multiplicity matters
    assert numbers_preserved("no numbers here", "काही नाही")


# ----------------------------------------------------------------------------- stub backend
def test_stub_backend_is_fixed_and_offline(monkeypatch):
    monkeypatch.setenv("TRANSLATE_BACKEND", "stub")
    r = run(T.to_english(text="काहीही मराठी"))
    assert r.english == T.STUB_ENGLISH and r.hints == T.STUB_HINTS and r.source_lang == "mr"
    r2 = run(T.to_english(audio=b"\x00", locale_hint="hi"))
    assert r2.source_lang == "hi" and r2.original == "<audio>"
    e = run(T.to_english(text="price of onion at Lasalgaon"))
    assert e.source_lang == "en" and e.hints["commodity"] == "cmd_onion"
    assert run(T.from_english(["Hello 20"], "mr")) == ["[mr] Hello 20"]
    assert run(T.from_english(["Which crop are you asking about?"], "hi"))[0].startswith("आप किस फसल")
