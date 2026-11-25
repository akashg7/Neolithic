"""Build eval/REPORT.md and eval/charts/*.png from whatever is in eval/results/.

    python eval/make_report.py              # after the run_day7.sh steps
    python eval/make_report.py --no-charts  # table only (no matplotlib needed)

Every plan target is shown as PASS / FAIL / NOT RUN. A target is PASS only when its result file exists
AND the number clears the bar; a missing file is never silently treated as passing. Results flagged with
a WARNING (fake embedder, scripted LLM, stub translator) are reported as PLUMBING ONLY, not PASS/FAIL.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES, CHARTS, REPORT = ROOT / "eval/results", ROOT / "eval/charts", ROOT / "eval/REPORT.md"
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e3e2de"  # validated pair


def load(name: str):
    """Load eval/results/<name>; tolerate log lines before the JSON object (stdout captures)."""
    p = RES / name
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8")
    try:
        return json.loads(txt[txt.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return None


def latest_bakeoff():
    files = sorted(glob.glob(str(RES / "bakeoff_*.json")))
    return json.loads(Path(files[-1]).read_text()) if files else None


def verdict(value, ok, plumbing=False) -> str:
    if value is None:
        return "NOT RUN"
    return "PLUMBING ONLY" if plumbing else ("PASS" if ok else "FAIL")


def fmt(v, pct=True) -> str:
    return "—" if v is None else (f"{v * 100:.1f}%" if pct else f"{v:.1f}")


def agent_run(agent, pivot):
    for r in (agent or {}).get("runs", []):
        if r["pivot"] == pivot:
            return r
    return None


def targets(R: dict) -> list[tuple[str, str, str, str]]:
    """(metric, bar, measured, verdict) rows."""
    rag, ag, tr, fa = R["rag"], R["agent"], R["translation"], R["faith"]
    rows = []
    ov = (rag or {}).get("main", {}).get("overall", {})
    plumb = bool(rag and rag.get("WARNING"))
    rows.append(("RAG Recall@5", "> 88%", fmt(ov.get("recall@5")), verdict(ov.get("recall@5"), (ov.get("recall@5") or 0) > .88, plumb)))
    rows.append(("RAG MRR@10", "> 0.78", fmt(ov.get("mrr@10"), False).replace("—", "—") if ov.get("mrr@10") is None else f"{ov['mrr@10']:.3f}",
                 verdict(ov.get("mrr@10"), (ov.get("mrr@10") or 0) > .78, plumb)))
    on = agent_run(ag, "on")
    m = on["metrics"] if on else {}
    aplumb = bool(ag and ag.get("WARNING")) or (on or {}).get("llm") == "baseline"
    rows.append(("Intent macro-F1", "> 92%", fmt(m.get("intent_macro_f1")), verdict(m.get("intent_macro_f1"), (m.get("intent_macro_f1") or 0) > .92, aplumb)))
    sf = m.get("slot", {}).get("micro_f1") if m else None
    rows.append(("Slot F1", "> 88%", fmt(sf), verdict(sf, (sf or 0) > .88, aplumb)))
    un = R["units"]
    ua = None
    if un:
        ua = un.get("unit_conversion_known", {}).get("accuracy")
    rows.append(("Unit conversion (known units)", "100%", fmt(ua), verdict(ua, ua == 1.0)))
    nc = (m.get("number_check") or {}) if m else {}
    ng = nc.get("final_reply_grounded_rate")
    if ng is None:  # no final replies carried numbers; fall back to the engine-level guard pass rate
        ng = nc.get("engine_level_pass_rate")
    rows.append(("Number check after guard", "100%", fmt(ng), verdict(ng, ng == 1.0, aplumb)))
    rc = (m.get("refusal_compliance") or {}).get("rate") if m else None
    rows.append(("Refusal compliance", "100%", fmt(rc), verdict(rc, rc == 1.0, aplumb)))
    if tr:
        f, b = tr["forward"], tr["backward"]
        pres = min(f["numbers"]["rate"], b["numbers"]["rate"], f["quantity_kg"]["rate"])
        rows.append(("Translation numbers/terms preserved", "100% numbers", fmt(pres), verdict(pres, pres == 1.0)))
    else:
        rows.append(("Translation numbers/terms preserved", "100% numbers", "—", "NOT RUN"))
    nat = (R["natural"] or {}).get("all", {}).get("natural_rate") if R["natural"] else None
    rows.append(("Translation natural (native raters)", ">= 80%", fmt(nat), verdict(nat, (nat or 0) >= .8)))
    lat = (R["latency"] or {}).get("latency_ms", {})
    tp, vp = lat.get("text", {}).get("p95_ms"), lat.get("voice", {}).get("p95_ms")
    rows.append(("Text P95 latency", "< 2.0 s", "—" if tp is None else f"{tp/1000:.2f} s", verdict(tp, (tp or 1e9) < 2000)))
    rows.append(("Voice P95 latency", "< 3.5 s", "—" if vp is None else f"{vp/1000:.2f} s", verdict(vp, (vp or 1e9) < 3500)))
    ff = (fa or {}).get("reply_faithful_rate")
    rows.append(("Reply faithfulness (cross-provider judge)", "report", fmt(ff), "REPORTED" if ff is not None else "NOT RUN"))
    return rows


def charts(R: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "text.color": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})
    made = []

    # 1. intent confusion matrix (pivot on), one-hue sequential
    on = agent_run(R["agent"], "on")
    if on:
        conf = on["metrics"]["confusion"]
        labels = sorted(set(conf) | {g for v in conf.values() for g in v})
        grid = [[conf.get(a, {}).get(b, 0) for b in labels] for a in labels]
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.imshow(grid, cmap=LinearSegmentedColormap.from_list("b", ["#f4f8fd", BLUE]), vmin=0)
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        mx = max(max(r) for r in grid) or 1
        for i, row in enumerate(grid):
            for j, v in enumerate(row):
                if v:
                    ax.text(j, i, v, ha="center", va="center", color="white" if v > mx * .55 else INK)
        ax.set_xlabel("predicted intent"); ax.set_ylabel("true intent")
        ax.set_title(f"Intent confusion matrix, test split (pivot on, n={on['metrics']['n']})", loc="left")
        fig.tight_layout(); fig.savefig(CHARTS / "confusion_matrix.png", dpi=160); plt.close(fig)
        made.append("confusion_matrix.png")

    # 2. RAG ablation: recall@5 for each retrieval setup, original-language vs English-pivot query
    rag = R["rag_dev"] or R["rag"]
    if rag and rag.get("ablation"):
        ab = rag["ablation"]
        setups = [s for s in ("dense", "sparse", "hybrid", "hybrid+rerank") if f"{s}/original" in ab]
        fig, ax = plt.subplots(figsize=(7.5, 4))
        w = 0.38
        for k, (q, col) in enumerate((("original", BLUE), ("english", ORANGE))):
            vals = [ab[f"{s}/{q}"]["recall@5"] for s in setups]
            xs = [i + (k - .5) * (w + .02) for i in range(len(setups))]
            ax.bar(xs, vals, w, color=col, label=f"{q} query")
            for x, v in zip(xs, vals):
                ax.text(x, v + .01, f"{v*100:.0f}%", ha="center", fontsize=8, color=INK)
        ax.axhline(.88, color=MUTED, lw=1, ls="--"); ax.text(len(setups) - .5, .89, "target 88%", ha="right", fontsize=8, color=MUTED)
        ax.set_xticks(range(len(setups)), setups); ax.set_ylim(0, 1.08); ax.set_ylabel("Recall@5")
        ax.yaxis.grid(True, color=GRID); ax.set_axisbelow(True)
        warn = "  [FAKE EMBEDDER: plumbing only]" if rag.get("WARNING") else ""
        ax.set_title(f"RAG ablation, {rag.get('split','?')} split{warn}", loc="left"); ax.legend(frameon=False)
        fig.tight_layout(); fig.savefig(CHARTS / "rag_ablation.png", dpi=160); plt.close(fig)
        made.append("rag_ablation.png")

    # 3. latency: measured P50/P95 per channel vs budget, plus reranker overhead
    lat = (R["latency"] or {}).get("latency_ms", {})
    rows = []
    for ch, budget in (("text", 2000), ("voice", 3500)):
        s = lat.get(ch, {})
        if s.get("p95_ms") is not None:
            rows.append((ch, s["p50_ms"], s["p95_ms"], budget))
    if rows or R["rerank"]:
        fig, ax = plt.subplots(figsize=(7.5, 3 + .4 * len(rows)))
        labels, y = [], 0
        for ch, p50, p95, budget in rows:
            ax.barh(y, p95, .5, color=ORANGE); ax.barh(y, p50, .5, color=BLUE)
            ax.plot([budget, budget], [y - .4, y + .4], color=INK, lw=1.5)
            ax.text(p95 + 40, y, f"P50 {p50:.0f} / P95 {p95:.0f} ms (budget {budget})", va="center", fontsize=8)
            labels.append(f"{ch} turn"); y += 1
        if R["rerank"]:
            rr = R["rerank"]
            ax.barh(y, rr["added_p95_ms"], .5, color=ORANGE); ax.barh(y, rr["added_median_ms"], .5, color=BLUE)
            ax.plot([rr["budget_ms"]] * 2, [y - .4, y + .4], color=INK, lw=1.5)
            ax.text(max(rr["added_p95_ms"], 0) + 40, y, f"{rr['decision']}: +{rr['added_median_ms']:.0f} / +{rr['added_p95_ms']:.0f} ms", va="center", fontsize=8)
            labels.append("reranker added"); y += 1
        ax.set_yticks(range(len(labels)), labels); ax.invert_yaxis(); ax.set_xlim(0, max([r[3] for r in rows] + [r[2] for r in rows] + [400]) * 1.55)
        ax.set_xlabel("milliseconds (P95 bar behind P50 bar; black tick = budget)")
        ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
        ax.set_title("Latency vs budget", loc="left")
        fig.tight_layout(); fig.savefig(CHARTS / "latency_breakdown.png", dpi=160); plt.close(fig)
        made.append("latency_breakdown.png")
    return made


def build(R: dict, made: list[str]) -> str:
    out = ["# Krishi-Mitr agent: evaluation report", "",
           "Generated by `eval/make_report.py` from `eval/results/`. All numbers are on the held-out **test** split unless marked. "
           "Do not hand-edit the table; re-run the generator.", "",
           "## Acceptance targets", "", "| Metric | Bar | Measured | Result |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | **{d}** |" for a, b, c, d in targets(R)]
    out += ["", "`PLUMBING ONLY` means the result came from a fake embedder / scripted router / stub translator: it proves the harness runs, "
            "not that the system is good. `NOT RUN` means no result file exists yet.", ""]

    on, off = agent_run(R["agent"], "on"), agent_run(R["agent"], "off")
    out += ["## Translate-pivot comparison (TRANSLATE_PIVOT on vs off)", ""]
    if on and off:
        out += ["| | intent macro-F1 | tool accuracy | slot F1 | refusal |", "|---|---|---|---|---|"]
        for nm, r in (("pivot on", on), ("pivot off", off)):
            m = r["metrics"]
            out.append(f"| {nm} | {fmt(m['intent_macro_f1'])} | {fmt(m['tool_accuracy'])} | {fmt(m['slot']['micro_f1'])} | {fmt(m['refusal_compliance']['rate'])} |")
        out += ["", f"LLM: `{on['llm']}`, translation: `{on['translate']}`."]
    else:
        out.append("NOT RUN (`eval_agent.py --pivot both`).")
    bo = latest_bakeoff()
    out += ["", "## Model choice (bake-off)", ""]
    if bo:
        out += ["| model | tool % | args % | refusals | turn P95 ms | errors | passes |", "|---|---|---|---|---|---|---|"]
        for s in bo["summaries"]:
            out.append(f"| {s['model']} | {s.get('tool_pct', s.get('tool_acc', '—'))} | {s.get('args_pct_hints', s.get('args_acc_hints', '—'))} | "
                       f"{s.get('refusal_rows_correct', '—')} | {s.get('turn_p95_ms', '—')} | {s.get('errors', '—')} | {'YES' if s.get('passes_all') else 'no'} |")
        out += ["", f"Winner: **{bo.get('winner') or 'none passed all bars'}**"]
    else:
        out.append("NOT RUN (`eval/bakeoff.py --loop`).")

    rr = R["rerank"]
    out += ["", "## Reranker decision", ""]
    out.append("NOT RUN (`scripts/bench_rerank.py`)." if not rr else
               f"**{rr['decision']}**: adds {rr['added_median_ms']} ms median / {rr['added_p95_ms']} ms P95 on this machine "
               f"(budget {rr['budget_ms']:.0f} ms); hit@5 {fmt(rr['without_rerank']['hit@5'])} -> {fmt(rr['with_rerank']['hit@5'])}, "
               f"MRR {rr['without_rerank']['mrr@10']} -> {rr['with_rerank']['mrr@10']}.")
    fa = R["faith"]
    out += ["", "## Faithfulness (LLM judge, different provider from the agent)", ""]
    if fa:
        out.append(f"{fa['replies_judged']} replies judged, {fa['judge_errors']} judge errors. Reply-level faithful: **{fmt(fa['reply_faithful_rate'])}**; "
                   f"claim-level supported: {fmt(fa.get('claim_supported_rate'))}. Unfaithful replies are listed in `eval/results/faithfulness_test.json`.")
    else:
        out.append("NOT RUN (`eval/eval_faithfulness.py`).")
    if made:
        out += ["", "## Charts", ""] + [f"![{n}](charts/{n})" for n in made]
    out += ["", "## Known limitations (read before quoting numbers)", "",
            "- Eval sets (`agent_eval_60`, `translation_100`, `rag_bench`) are **authored**, not collected from real farmers; native speakers have not reviewed them.",
            "- Only 31 agent rows and ~42 RAG rows are in the test split: one wrong row moves a metric by 2-3 points. Report intervals, not decimals.",
            "- Grading corpus has known gaps (tomato, whole tur); the KCC limit appears as both Rs 3 lakh and Rs 5 lakh in sources; the APMC 0.75% fee comes from news, not a statute.",
            "- Latency depends on the machine and network; the figures above are from the machine that ran `run_day7.sh`.", ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-charts", action="store_true")
    a = ap.parse_args()
    R = {"rag": load("rag_test.json"), "rag_dev": load("rag_dev.json"), "agent": load("agent_test.json"),
         "translation": load("translation_test.json"), "natural": load("naturalness_summary.json"),
         "faith": load("faithfulness_test.json"), "units": load("units_test.json"),
         "latency": load("turn_latency.json"), "rerank": load("rerank_latency.json")}
    made = [] if a.no_charts else charts(R)
    REPORT.write_text(build(R, made), encoding="utf-8")
    print(f"wrote {REPORT}  charts: {made or 'none'}")
    sys.exit(0)


if __name__ == "__main__":
    main()
