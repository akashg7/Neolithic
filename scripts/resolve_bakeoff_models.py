"""Fill the REPLACE_* model ids in eval/bakeoff_models.json from each provider's live /models list.

Provider model ids change faster than docs do (Groq retires models; Gemini renames Flash versions), so
nothing is hardcoded: this lists what your keys can actually call and picks the newest match.

    python scripts/resolve_bakeoff_models.py            # dry run: prints what it would pick
    python scripts/resolve_bakeoff_models.py --write    # rewrites eval/bakeoff_models.json in place
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "eval/bakeoff_models.json"
# candidate name -> (must-match regex, reject regex)
RULES = {
    "groq-qwen-27b": (r"qwen.*27b", r"guard|whisper|tts"),
    "gemini-flash": (r"gemini-[\d.]+-flash", r"lite|image|tts|live|audio|embed|thinking-exp|preview-\d{2}-\d{2}"),
}


def _version(model_id: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", model_id.split("/")[-1].replace("27b", "")))


def pick_model(ids: list[str], name: str) -> str | None:
    """Newest id matching the rule for this candidate (None if nothing matches)."""
    want, reject = RULES[name]
    ids = [i.removeprefix("models/") for i in ids]
    ok = [i for i in ids if re.search(want, i, re.I) and not re.search(reject, i, re.I)]
    return max(ok, key=lambda i: (_version(i), i)) if ok else None


def list_models(base_url: str, key: str) -> list[str]:
    r = httpx.get(base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
    r.raise_for_status()
    return [m["id"] for m in r.json().get("data", [])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--path", type=Path, default=MODELS)
    args = ap.parse_args()
    cfg = json.loads(args.path.read_text())
    unresolved = 0
    for c in cfg["candidates"]:
        if not str(c["model"]).startswith("REPLACE_"):
            continue
        key = os.getenv(c["api_key_env"], "")
        if not key:
            print(f"SKIP  {c['name']}: {c['api_key_env']} not set"); unresolved += 1; continue
        try:
            chosen = pick_model(list_models(c["base_url"], key), c["name"])
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"FAIL  {c['name']}: {type(exc).__name__}: {exc}"); unresolved += 1; continue
        if not chosen:
            print(f"NONE  {c['name']}: no /models entry matched {RULES[c['name']][0]!r}"); unresolved += 1; continue
        print(f"PICK  {c['name']}: {chosen}")
        c["model"] = chosen
    if args.write:
        args.path.write_text(json.dumps(cfg, indent=2) + "\n")
        print(f"wrote {args.path}")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
