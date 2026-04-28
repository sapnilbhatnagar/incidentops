"""AGENT-001: Sliding-window chunker over runbooks, incidents, and tickets."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_DATA = Path(__file__).parent.parent / "data"
_CHUNK_CHARS = 2000
_OVERLAP_CHARS = 200


@dataclass(frozen=True)
class Chunk:
    source_id: str
    text: str
    span_start: int
    span_end: int


def _windows(source_id: str, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + _CHUNK_CHARS, len(text))
        chunks.append(Chunk(source_id=source_id, text=text[start:end], span_start=start, span_end=end))
        if end == len(text):
            break
        start = end - _OVERLAP_CHARS
    return chunks


def chunk_corpus() -> list[Chunk]:
    """Load and chunk all runbooks, incidents, and tickets from the corpus."""
    chunks: list[Chunk] = []

    for path in sorted((_DATA / "runbooks").glob("*.md")):
        source_id = path.stem.split("-")[0]
        chunks.extend(_windows(source_id, path.read_text()))

    for path in sorted((_DATA / "incidents").glob("*.md")):
        source_id = path.stem.split("-")[0]
        chunks.extend(_windows(source_id, path.read_text()))

    tickets_path = _DATA / "tickets" / "tickets.jsonl"
    if tickets_path.exists():
        for line in tickets_path.read_text().splitlines():
            if not line.strip():
                continue
            t = json.loads(line)
            parts = [t.get("title", ""), t.get("description", ""), t.get("resolution_notes", "")]
            text = " ".join(p for p in parts if p).strip()
            if text:
                chunks.extend(_windows(t["ticket_id"], text))

    return chunks
