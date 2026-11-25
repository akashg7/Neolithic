"""Section-aware chunker.

Pipeline (plan): split Markdown by heading -> sections up to ~450 tokens stay whole -> longer
sections are cut into ~350-450-token windows at sentence boundaries with ~15% overlap ->
each chunk is embedded with a context prefix (document title + heading path).

Token counts use a pluggable counter. Production passes the BGE-M3 tokenizer
(`bge_m3_token_counter()`); tests use a word counter. The fallback approximate counter is only
for dry runs and logs a warning, because chunk sizes then differ from what the embedder sees.
"""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.contracts import RAG_CATEGORIES
from app.nlp.lexicon import resolve_commodity
from app.nlp.normalize import normalize_text

log = logging.getLogger("krishi.chunker")

TokenCounter = Callable[[str], int]
TARGET_MIN, TARGET_MAX, OVERLAP_FRAC = 350, 450, 0.15
_NS = uuid.UUID("6f1c2b8e-4f0a-4c53-9d0e-5b7a1d6c9a11")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SENT = re.compile(r"(?<=[.!?।])\s+|\n{2,}")
_DEVA = re.compile(r"[ऀ-ॿ]")


@dataclass
class Chunk:
    chunk_id: str  # stable: "<source_doc>::<section-slug>::<n>"
    text: str  # raw text shown to the model
    embed_text: str  # context prefix + text, what gets embedded
    source_doc: str  # corpus-relative path, e.g. "grading/onion.md"
    section_title: str  # heading path, "A > B"
    category: str
    language: str  # en | mr | hi | bilingual
    crops: list[str] = field(default_factory=list)  # resolved ids; [] = applies to all crops
    tokens: int = 0
    doc_hash: str = ""

    @property
    def point_id(self) -> str:
        return str(uuid.uuid5(_NS, self.chunk_id))


# --------------------------------------------------------------------------- token counters
def word_counter(text: str) -> int:
    return len(text.split())


def approx_token_counter(text: str) -> int:
    """Rough BGE-M3-ish estimate (~1.4 sub-word tokens per word, more for Devanagari). Dry-run only."""
    n = 0
    for w in text.split():
        n += max(1, round(len(w) / (2.2 if _DEVA.search(w) else 4.0)))
    return n


def bge_m3_token_counter(model_name: str = "BAAI/bge-m3") -> TokenCounter:
    """Real tokenizer. Falls back (loudly) to the approximation if it cannot be loaded."""
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(model_name)
        return lambda t: len(tok.encode(t, add_special_tokens=False))
    except Exception as e:  # offline, not installed, ...
        log.warning("BGE-M3 tokenizer unavailable (%s); using the APPROXIMATE counter. "
                    "Re-run ingestion with the real tokenizer before reporting numbers.", e)
        return approx_token_counter


# --------------------------------------------------------------------------- parsing
def parse_front_matter(text: str) -> tuple[dict, str]:
    """Tiny YAML subset: `key: value` and `key: [a, b]`. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta: dict = {}
    for line in text[3:end].strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            meta[k.strip()] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        else:
            meta[k.strip()] = v.strip("'\"")
    return meta, text[end + 4:].lstrip("\n")


@dataclass
class Section:
    path: list[str]
    text: str


def split_sections(body: str) -> list[Section]:
    """Split by Markdown headings, tracking the heading path. Headings inside code fences are text."""
    sections: list[Section] = []
    path: list[tuple[int, str]] = []
    buf: list[str] = []
    in_fence = False

    def flush() -> None:
        text = "\n".join(buf).strip()
        if text:
            sections.append(Section([t for _, t in path], text))
        buf.clear()

    for line in body.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, m.group(2).strip()))
        else:
            buf.append(line)
    flush()
    return sections


def _slug(s: str) -> str:
    s = re.sub(r"[^\wऀ-ॿ]+", "-", normalize_text(s).lower()).strip("-")
    return s[:48] or "section"


def detect_doc_language(text: str, declared: Optional[str]) -> str:
    if declared in ("en", "mr", "hi", "bilingual"):
        return declared
    deva = len(_DEVA.findall(text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = deva + latin
    if total == 0 or deva / total < 0.05:
        return "en"
    if latin / total > 0.15:
        return "bilingual"
    log.warning("Devanagari document without a `language:` front-matter field; marking bilingual. "
                "Declare mr or hi to enable language filtering.")
    return "bilingual"


# --------------------------------------------------------------------------- windows
def _split_long_sentence(s: str, count: TokenCounter, limit: int) -> list[str]:
    words = s.split()
    out, cur = [], []
    for w in words:
        cur.append(w)
        if count(" ".join(cur)) > limit and len(cur) > 1:
            cur.pop()
            out.append(" ".join(cur))
            cur = [w]
    if cur:
        out.append(" ".join(cur))
    return out


def window_section(text: str, count: TokenCounter, lo: int = TARGET_MIN, hi: int = TARGET_MAX,
                   overlap: float = OVERLAP_FRAC) -> list[str]:
    """Cut text into windows of ~lo..hi tokens at sentence boundaries, ~overlap fraction shared."""
    if count(text) <= hi:
        return [text]
    sents: list[str] = []
    for s in (x.strip() for x in _SENT.split(text) if x and x.strip()):
        sents.extend([s] if count(s) <= hi else _split_long_sentence(s, count, hi))
    sizes = [count(s) for s in sents]
    keep = max(1, int(hi * overlap))  # tokens of overlap carried into the next window
    windows: list[str] = []
    i = 0
    while i < len(sents):
        j, total = i, 0
        while j < len(sents) and total + sizes[j] <= hi:
            total += sizes[j]
            j += 1
        if j == i:  # defensive: one sentence larger than hi
            j = i + 1
        windows.append(" ".join(sents[i:j]))
        if j >= len(sents):
            break
        # next window starts so that ~`keep` tokens overlap, but always makes progress
        back, acc = j, 0
        while back > i + 1 and acc + sizes[back - 1] <= keep:
            back -= 1
            acc += sizes[back]
        i = max(back, i + 1)
    # a short tail merges into the previous window (as long as the result is not far over hi)
    if len(windows) > 1 and count(windows[-1]) < lo * 0.3:
        merged = windows[-2] + " " + windows[-1]
        if count(merged) <= hi * 1.15:
            windows[-2:] = [merged]
    return windows


# --------------------------------------------------------------------------- documents
def chunk_document(rel_path: str, raw: str, count: TokenCounter = word_counter) -> list[Chunk]:
    """`rel_path` is corpus-relative, e.g. 'grading/onion.md'; its first folder is the category."""
    category = Path(rel_path).parts[0]
    if category not in RAG_CATEGORIES:
        raise ValueError(f"{rel_path}: first folder must be one of {RAG_CATEGORIES}")
    doc_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    meta, body = parse_front_matter(raw)
    body = normalize_text_keep_lines(body)
    title = meta.get("title") or next((s.path[0] for s in split_sections(body) if s.path), Path(rel_path).stem)
    lang = detect_doc_language(body, meta.get("language"))
    crops = sorted({resolve_commodity(c) or c.lower() for c in meta.get("crops", [])})
    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    for sec in split_sections(body):
        heading = " > ".join(sec.path) if sec.path else title
        base = f"{rel_path}::{_slug(heading)}"
        for w in window_section(sec.text, count):
            n = seen.get(base, 0)
            seen[base] = n + 1
            prefix = f"{title} | {heading}" if heading != title else title
            chunks.append(Chunk(
                chunk_id=f"{base}::{n}", text=w, embed_text=f"{prefix}\n{w}", source_doc=rel_path,
                section_title=heading, category=category, language=lang, crops=crops,
                tokens=count(w), doc_hash=doc_hash))
    return chunks


def normalize_text_keep_lines(s: str) -> str:
    """normalize_text collapses newlines; the chunker needs them (headings, paragraphs)."""
    return "\n".join(normalize_text(line) for line in s.splitlines())


def iter_corpus(root: Path) -> list[tuple[str, str]]:
    """[(corpus-relative path, text)] for every .md under the four category folders."""
    out = []
    for cat in RAG_CATEGORIES:
        for p in sorted((root / cat).glob("**/*.md")):
            out.append((p.relative_to(root).as_posix(), p.read_text("utf-8")))
    return out
