"""Generate the glossary corpus folder from the same data files the NLP code uses, so the retrieval
corpus and the unit parser can never disagree.

    python scripts/build_glossary.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app/nlp/data"
OUT = ROOT / "data/rag_corpus/glossary"


def units_md() -> str:
    d = json.loads((DATA / "units.json").read_text("utf-8"))["units"]
    lines = ["---", "title: Units of quantity", "language: bilingual", "---", "", "# Units of quantity", "",
             "How farmers' units convert to kilograms on this platform.", ""]
    for name, spec in d.items():
        names = ", ".join(spec["aliases"])
        lines += [f"## {name}", ""]
        if spec["kg"] is None:
            lines.append(f"The size of one {name} differs from place to place, so it has no fixed value on this "
                         f"platform. Ask the farmer for the quantity in kg, quintals or bags.")
        else:
            lines.append(f"1 {name} = {spec['kg']} kg.")
        lines += ["", f"Also written as: {names}.", ""]
    return "\n".join(lines)


def names_md(section: str, title: str, kind: str) -> str:
    d = json.loads((DATA / "lexicon.json").read_text("utf-8"))[section]
    lines = ["---", f"title: {title}", "language: bilingual", "---", "", f"# {title}", ""]
    for _id, spec in d.items():
        slug = _id.split("_", 1)[1].replace("_", " ")
        lines += [f"## {slug}", "", f"{kind} '{slug}' (id {_id}) is also called: {', '.join(spec['aliases'])}.", ""]
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "units.md").write_text(units_md(), "utf-8")
    (OUT / "commodity_names.md").write_text(names_md("commodities", "Commodity names", "Commodity"), "utf-8")
    (OUT / "mandi_names.md").write_text(names_md("mandis", "Mandi names", "Mandi"), "utf-8")
    print("wrote", *(p.name for p in sorted(OUT.glob("*.md"))))


if __name__ == "__main__":
    main()
