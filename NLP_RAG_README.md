# Krishi-Mitr: NLP, RAG & evaluation layer (Person B, Days 0-2)

Run the NLP/RAG/eval tests (offline, no Postgres needed): `pip install -r requirements.txt && pytest tests/nlp_rag` (208 tests, ~2 s).

> Integrated into the main repo layout: code in `app/nlp`, `app/rag`, `app/contracts.py`; scripts in `scripts/`; eval in `eval/`; corpus in `data/rag_corpus/`; tests in `tests/nlp_rag/`. Env vars are documented in `.env.example` (NLP / RAG section).

## What is here, by plan day

| Day | Deliverable | Where |
|---|---|---|
| 0 | Frozen contracts: `RetrievedChunk`, `Translated`, `ToolResult`, `Intent` labels, `EvalRow` | `app/contracts.py` |
| 1 | Normalizer, unit parser (`to_kg`, `parse_quantities`), name lexicon (`resolve_commodity`, `resolve_mandi`), hints | `app/nlp/{normalize,units,lexicon,hints}.py`, data in `app/nlp/data/*.json` |
| 1 | Translation layer: stub + real Sarvam backend, timing log, number check after translating back | `app/nlp/translate.py`, `app/nlp/numbers.py` |
| 1 | Pre-translated safety/fallback messages (**mr/hi drafts, need native review**) | `app/nlp/messages.py` |
| 1 | Retriever stub (fixed chunks) | `app/rag/retriever.py` |
| 1 | 40 bake-off prompts (authored, not recorded) | `eval/data/bakeoff_40.jsonl`, `scripts/build_bakeoff.py` |
| 1 | Unit-and-slot set (200, dev/test split) + slot-F1 eval | `scripts/gen_unit_set.py`, `eval/eval_units.py` |
| 2 | Model bake-off harness and decision rule | `eval/bakeoff.py`, `eval/bakeoff_models.json` |
| 2 | Section-aware chunker, BGE-M3 dense+sparse + Qdrant hybrid (RRF), optional reranker, idempotent `ingest_rag.py` | `app/rag/*`, `scripts/ingest_rag.py` |

## For Person A: how to call my side

```python
from app.nlp.translate import to_english, from_english, translate_back_checked, TranslationUnavailable, EmptyTranscript
from app.nlp.units import to_kg, UnknownUnitError        # tool wrappers
from app.nlp.lexicon import resolve_commodity, resolve_mandi, commodity_candidates, mandi_candidates
from app.nlp.numbers import extract_numbers, numbers_preserved   # for your number-check guard
from app.nlp.messages import get_message                  # NO_ADVICE, FALLBACK, ASK_QUANTITY, ASK_MANDI, ASK_COMMODITY, ASK_UNIT, CHEMICAL_REFERRAL
from app.rag.retriever import search                      # RETRIEVER=stub (default) | real
```

- `TRANSLATE_BACKEND=stub` (default) returns a fixed English sentence + fixed hints for non-English text, so you can build the loop offline. `=sarvam` calls the real APIs (`SARVAM_API_KEY`).
- Catch `TranslationUnavailable` (translation failed after one retry) and send `get_message("FALLBACK", lang)`. Catch `EmptyTranscript` and ask the farmer to repeat.
- `translate_back_checked(texts, lang)` returns `(texts, ok)`; `ok=False` means a number was lost twice, so send the fallback built from card data.
- Hints (`Translated.hints`): `quantity_kg`, `commodity`, `mandi` are set only when unambiguous. Extra keys: `unit_unknown` (khandi/goni: ask, don't guess), `commodity_candidates`/`mandi_candidates`, `quantities`.
- `to_kg` raises `UnknownUnitError` (`.reason` = `unknown` | `variable_size`). `resolve_*` return `None` when unknown OR ambiguous; use `*_candidates` to tell which (0 = unknown, 2+ = ask which one).

## Things that need a human (nothing here can fake these)

1. **Native-speaker review** of `messages.py` (mr, hi). `python -m app.nlp.messages` lists what is unreviewed.
2. **Sarvam key**: run `python scripts/build_bakeoff.py --translate` and look at `timing_summary()` (or set `SARVAM_TIMING_LOG`) to get real latency. Nothing in this repo has touched the real Sarvam API; request/response shapes were checked against their docs only.
3. **LLM keys + model IDs** for the bake-off: edit `eval/bakeoff_models.json` (two ids are placeholders; Groq retires models; Sarvam-30B is retired, only 105B remains).
4. **IDs**: `cmd_*` / `mkt_*` slugs and the 27-mandi list are a seed. Reconcile with Member 2's `id_resolver.py` / DB before Day 3.
5. **Unit sizes**: `bori = 50 kg` comes from the plan; khandi/goni/maund are deliberately unset.
6. **Corpus**: `schemes_finance/`, `grading/`, `platform/` are empty. Collect official sources (see `data/rag_corpus/README.md`); test one scanned Marathi PDF for OCR early.
7. **Real BGE-M3 / reranker**: needs `FlagEmbedding`, `transformers` and ~2 GB download. Chunk sizes use the real tokenizer when available; otherwise an approximation (logged).
8. **Prompts**: the 40 bake-off and 200 unit prompts are authored. Swap in real farmer questions before calling the numbers "real farmer data".
