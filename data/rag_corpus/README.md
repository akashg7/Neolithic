# RAG corpus

Four folders; the folder name is the retrieval `category`.

| Folder | What goes here | Status |
|---|---|---|
| `schemes_finance/` | KCC, PM-KISAN, crop insurance, MSP, warehouse-receipt loans, eligibility, documents | **empty - collect official sources** |
| `grading/` | Grade standards per crop (size, moisture, defects), how the platform's assay grade works | **empty - collect, ask Person A for the grading_engine rules** |
| `platform/` | How to list a lot, make/accept an offer, escrow, payouts, app screens | **empty - Members 1-3 write this** |
| `glossary/` | Units, commodity and mandi names | generated: `python scripts/build_glossary.py` |

Rules
- Markdown only. Convert PDFs first. **Scanned Marathi PDFs may need OCR (budget up to a day): test one early.**
- One topic per file, real headings (`#`, `##`). The chunker splits by heading, then to 350-450 tokens.
- Optional front matter: `title`, `language` (`en|mr|hi|bilingual`), `crops: [onion, wheat]`.
- Record the source (URL + date) at the bottom of every file. Do NOT paste facts from memory: an invented
  scheme rule that gets retrieved is a fabricated claim in front of a farmer.
- Never edit `glossary/` by hand; edit `app/nlp/data/*.json` and regenerate.
