#!/usr/bin/env bash
# Day 7 (Person B): real-model evaluation, run on YOUR machine (needs Docker, model downloads, API keys).
#
#   bash scripts/run_day7.sh setup      # pull, venv deps, Qdrant up, BGE-M3 ingest (+ idempotence re-run)
#   bash scripts/run_day7.sh models     # resolve REPLACE_* model ids, run the bake-off  -> pick the model
#   bash scripts/run_day7.sh dev        # tune on the DEV split: RAG ablation, rerank decision, agent pivot on/off
#   bash scripts/run_day7.sh final      # ONE run on the held-out TEST split + translation + faithfulness
#   bash scripts/run_day7.sh latency    # needs the backend running (Person A's live check) -> turn_latency.json
#   bash scripts/run_day7.sh report     # eval/REPORT.md + eval/charts/*.png
#
# Required env (put in .env or export): GROQ_API_KEY / GEMINI_API_KEY / SARVAM_API_KEY as you have them.
#   AGENT_PROVIDER  provider that runs the agent in the eval         (default groq)
#   JUDGE_PROVIDER  a DIFFERENT provider that judges faithfulness    (default gemini)
# Results land in eval/results/. Do not run `final` until `dev` is tuned: the test split is for one look only.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
PY="${PY:-python}"
AGENT_PROVIDER="${AGENT_PROVIDER:-groq}"
JUDGE_PROVIDER="${JUDGE_PROVIDER:-gemini}"
R=eval/results; mkdir -p "$R"

# Only the agent's own provider answers during eval; the default fallback chain would silently mix models.
single_provider() { export LLM_PROVIDER="$AGENT_PROVIDER" LLM_FALLBACK_CHAIN="$AGENT_PROVIDER"; }

step_setup() {
  git pull --ff-only origin ai-agent
  $PY -m pip install -q -r requirements.txt FlagEmbedding qdrant-client matplotlib
  docker compose up -d qdrant
  until curl -sf http://localhost:6333/healthz >/dev/null; do sleep 1; done
  $PY scripts/ingest_rag.py --embedder bge-m3 --prune          # first run downloads BGE-M3 (~2 GB)
  echo "--- idempotence: second run must skip every file (unchanged sha256) ---"
  $PY scripts/ingest_rag.py --embedder bge-m3
}

step_models() {
  $PY scripts/resolve_bakeoff_models.py --write || echo "(some ids unresolved: those candidates are skipped)"
  $PY eval/bakeoff.py --loop --p95-budget-ms 1100               # writes eval/results/bakeoff_<stamp>.{json,md}
  echo ">> pick the winner in the .md, then set LLM_PROVIDER / the model env var in .env"
}

step_dev() {
  single_provider
  $PY eval/eval_rag.py --split dev --embedder bge-m3 --ablate --rerank --out "$R/rag_dev.json"
  $PY scripts/bench_rerank.py --split dev --out "$R/rerank_latency.json"   # KEEP/DROP at 300 ms
  # RERANK=on in .env only if the benchmark printed KEEP
  TRANSLATE_BACKEND=sarvam $PY eval/eval_agent.py --split dev --llm live --translate live --pivot both \
      --rag real --out "$R/agent_dev.json" --trace "$R/agent_dev_trace.jsonl"
}

step_final() {
  single_provider
  [ "${CONFIRM_TEST_SPLIT:-}" = "yes" ] || { echo "Set CONFIRM_TEST_SPLIT=yes: the test split should be run once, after dev tuning is finished."; exit 1; }
  $PY eval/eval_units.py --split test > "$R/units_test.json"
  $PY eval/eval_rag.py --split test --embedder bge-m3 --ablate $([ "${RERANK:-off}" = on ] && echo --rerank) --out "$R/rag_test.json"
  TRANSLATE_BACKEND=sarvam $PY eval/eval_agent.py --split test --llm live --translate live --pivot both \
      --rag real --out "$R/agent_test.json" --trace "$R/agent_test_trace.jsonl"
  TRANSLATE_BACKEND=sarvam $PY eval/eval_translation.py --split test --out "$R/translation_test.json"
  TRANSLATE_BACKEND=sarvam $PY eval/eval_translation.py --export-ratings "$R/naturalness_sheet.csv"
  echo ">> give naturalness_sheet.csv to a Marathi and a Hindi speaker: fill the 'natural' column with 1 or 0, then run:"
  echo "   python eval/eval_translation.py --ratings $R/naturalness_sheet.csv > $R/naturalness_summary.json"
  $PY eval/eval_faithfulness.py --trace "$R/agent_test_trace_pivot_on.jsonl" \
      --agent-provider "$AGENT_PROVIDER" --judge-provider "$JUDGE_PROVIDER" --out "$R/faithfulness_test.json"
}

step_latency() {
  $PY scripts/verify_day6_agent.py --mode live --strict-latency ${WAV:+--wav "$WAV"}
  $PY scripts/agent_turn_report.py --hours 2 > "$R/turn_latency.json"
}

step_report() { $PY eval/make_report.py; }

case "${1:-}" in
  setup) step_setup ;; models) step_models ;; dev) step_dev ;; final) step_final ;;
  latency) step_latency ;; report) step_report ;;
  *) sed -n 2,14p "$0"; exit 2 ;;
esac
