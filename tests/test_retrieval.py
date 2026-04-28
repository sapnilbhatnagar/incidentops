"""Tests for the chunker and RRF fusion logic — no model downloads."""
from __future__ import annotations

import pytest

from incidentops.agent.chunker import Chunk, chunk_corpus, _windows
from incidentops.agent.retrieve import _rrf_fuse


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def test_windows_single_chunk_for_short_text():
    chunks = _windows("RB001", "short text")
    assert len(chunks) == 1
    assert chunks[0].source_id == "RB001"
    assert chunks[0].text == "short text"
    assert chunks[0].span_start == 0
    assert chunks[0].span_end == len("short text")


def test_windows_overlap_is_correct():
    text = "x" * 2500
    chunks = _windows("RB001", text)
    assert len(chunks) == 2
    assert chunks[0].span_end == 2000
    assert chunks[1].span_start == 1800  # 2000 - 200 overlap
    assert chunks[1].span_end == 2500


def test_windows_span_covers_full_text():
    text = "a" * 5000
    chunks = _windows("SRC", text)
    assert chunks[0].span_start == 0
    assert chunks[-1].span_end == 5000


def test_chunk_corpus_covers_all_runbooks():
    chunks = chunk_corpus()
    source_ids = {c.source_id for c in chunks}
    for i in range(1, 16):
        assert f"RB{i:03d}" in source_ids, f"RB{i:03d} missing from chunked corpus"


def test_chunk_corpus_covers_all_incidents():
    chunks = chunk_corpus()
    source_ids = {c.source_id for c in chunks}
    for i in range(1, 9):
        assert f"INC{i:03d}" in source_ids, f"INC{i:03d} missing from chunked corpus"


def test_chunk_corpus_includes_tickets():
    chunks = chunk_corpus()
    ticket_chunks = [c for c in chunks if c.source_id.startswith("TKT")]
    assert len(ticket_chunks) > 0


def test_chunks_have_non_empty_text():
    chunks = chunk_corpus()
    assert all(c.text.strip() for c in chunks)


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------

def test_rrf_fuse_combines_both_lists():
    dense = [(0, 0.9), (1, 0.8), (2, 0.7)]
    sparse = [(2, 5.0), (0, 4.0), (3, 3.0)]
    fused = _rrf_fuse(dense, sparse)
    # chunk 0 appears in both → should rank highest
    top_idx = fused[0][0]
    assert top_idx == 0


def test_rrf_fuse_scores_are_positive():
    dense = [(0, 0.9), (1, 0.5)]
    sparse = [(1, 3.0), (2, 1.0)]
    fused = _rrf_fuse(dense, sparse)
    assert all(score > 0 for _, score in fused)


def test_rrf_fuse_deduplicates():
    dense = [(0, 0.9), (0, 0.8)]  # duplicate idx (shouldn't happen in practice, but defensive)
    sparse = [(0, 1.0)]
    fused = _rrf_fuse(dense, sparse)
    indices = [idx for idx, _ in fused]
    assert len(indices) == len(set(indices))


def test_rrf_fuse_empty_lists():
    assert _rrf_fuse([], []) == []
    assert _rrf_fuse([(0, 1.0)], []) == [(0, pytest.approx(1 / 61, rel=1e-3))]
