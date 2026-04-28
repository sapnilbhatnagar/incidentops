"""AGENT-002 + AGENT-003: Dense (LanceDB) and sparse (BM25) indices over the chunked corpus."""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .chunker import Chunk, chunk_corpus

if TYPE_CHECKING:
    import lancedb

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_LANCE_URI = str(_PROJECT_ROOT / ".lancedb")
_CACHE_FILE = _PROJECT_ROOT / ".cache" / "chunks.pkl"
_EMBED_MODEL = "all-MiniLM-L6-v2"
_TABLE_NAME = "corpus"


class IndexStore:
    def __init__(
        self,
        model: SentenceTransformer,
        table,  # lancedb.Table
        bm25: BM25Okapi,
        chunks: list[Chunk],
    ) -> None:
        self._model = model
        self._table = table
        self._bm25 = bm25
        self._chunks = chunks

    @property
    def chunks(self) -> list[Chunk]:
        return self._chunks

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def dense_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """Returns (chunk_idx, score) pairs — score is 1/(1+distance)."""
        vec = self.embed(query)
        rows = self._table.search(vec).limit(top_k).to_list()
        return [(int(r["chunk_idx"]), 1.0 / (1.0 + r["_distance"])) for r in rows]

    def sparse_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """Returns (chunk_idx, BM25 score) pairs, positive scores only."""
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in top_indices if scores[i] > 0.0]


def build(chunks: list[Chunk] | None = None) -> IndexStore:
    """Build dense + sparse indices from scratch. Persists LanceDB table and chunk cache."""
    import lancedb

    if chunks is None:
        chunks = chunk_corpus()

    model = SentenceTransformer(_EMBED_MODEL)
    embeddings = model.encode([c.text for c in chunks], normalize_embeddings=True, show_progress_bar=True)

    records = [
        {
            "chunk_idx": i,
            "source_id": c.source_id,
            "text": c.text,
            "span_start": c.span_start,
            "span_end": c.span_end,
            "vector": embeddings[i].tolist(),
        }
        for i, c in enumerate(chunks)
    ]

    db = lancedb.connect(_LANCE_URI)
    table = db.create_table(_TABLE_NAME, data=records, mode="overwrite")

    bm25 = BM25Okapi([c.text.lower().split() for c in chunks])

    _CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(_CACHE_FILE, "wb") as f:
        pickle.dump(chunks, f)

    return IndexStore(model=model, table=table, bm25=bm25, chunks=chunks)


def load_or_build() -> IndexStore:
    """Load existing indices if present, otherwise build them."""
    import lancedb

    lance_path = Path(_LANCE_URI) / f"{_TABLE_NAME}.lance"
    if lance_path.exists() and _CACHE_FILE.exists():
        with open(_CACHE_FILE, "rb") as f:
            chunks: list[Chunk] = pickle.load(f)
        model = SentenceTransformer(_EMBED_MODEL)
        db = lancedb.connect(_LANCE_URI)
        table = db.open_table(_TABLE_NAME)
        bm25 = BM25Okapi([c.text.lower().split() for c in chunks])
        return IndexStore(model=model, table=table, bm25=bm25, chunks=chunks)

    return build()
