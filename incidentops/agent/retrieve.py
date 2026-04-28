"""AGENT-004 + AGENT-005: RRF fusion, cross-encoder rerank, and public retrieve() API."""
from __future__ import annotations

from functools import lru_cache

from .chunker import Chunk
from .index import IndexStore, load_or_build

_DENSE_CANDIDATES = 20
_SPARSE_CANDIDATES = 20
_RRF_K = 60
_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _rrf_fuse(
    dense: list[tuple[int, float]],
    sparse: list[tuple[int, float]],
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion over two ranked lists, returns (chunk_idx, rrf_score)."""
    scores: dict[int, float] = {}
    for rank, (idx, _) in enumerate(dense):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)
    for rank, (idx, _) in enumerate(sparse):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _rerank(query: str, candidates: list[Chunk]) -> list[Chunk]:
    """Cross-encoder rerank. Falls back to original order if model unavailable."""
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(_CROSS_ENCODER_MODEL)
        pairs = [(query, c.text) for c in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        return [c for _, c in ranked]
    except Exception:
        return candidates


@lru_cache(maxsize=1)
def _index() -> IndexStore:
    return load_or_build()


def retrieve(query: str, top_k: int = 5) -> list[Chunk]:
    """Hybrid retrieve: dense + BM25 → RRF → cross-encoder rerank → top_k Chunks."""
    store = _index()
    dense = store.dense_search(query, _DENSE_CANDIDATES)
    sparse = store.sparse_search(query, _SPARSE_CANDIDATES)
    fused = _rrf_fuse(dense, sparse)

    rerank_pool = min(top_k * 4, len(fused))
    candidates = [store.chunks[idx] for idx, _ in fused[:rerank_pool]]
    reranked = _rerank(query, candidates)
    return reranked[:top_k]
