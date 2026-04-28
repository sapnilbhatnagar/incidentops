"""Tests for the diagnosis stage — formatting, parsing, and mocked API call."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import os

import pytest

from incidentops.agent.chunker import Chunk
from incidentops.agent.diagnose import _format_user_message, _parse_tool_output, diagnose
from incidentops.evals.schema import Diagnosis


_TICKET = {
    "ticket_id": "TKT-2026-03-04-001",
    "tenant_id": "TEN-HELIO-2024",
    "title": "Users cannot sign in via SSO",
    "description": "SAML assertion rejected since 14:00 UTC.",
    "severity": "P2",
}

_CHUNK = Chunk(
    source_id="RB001",
    text="JWKS endpoint rotated without updating SDK cache.",
    span_start=0,
    span_end=48,
)


# ---------------------------------------------------------------------------
# _format_user_message
# ---------------------------------------------------------------------------

def test_format_includes_ticket_id():
    msg = _format_user_message(_TICKET, [_CHUNK])
    assert "TKT-2026-03-04-001" in msg


def test_format_includes_tenant():
    msg = _format_user_message(_TICKET, [_CHUNK])
    assert "TEN-HELIO-2024" in msg


def test_format_includes_chunk_source_id():
    msg = _format_user_message(_TICKET, [_CHUNK])
    assert "RB001" in msg


def test_format_includes_chunk_span():
    msg = _format_user_message(_TICKET, [_CHUNK])
    assert "0–48" in msg


def test_format_empty_chunks_signals_abstain():
    msg = _format_user_message(_TICKET, [])
    assert "abstain" in msg.lower()


def test_format_caps_at_eight_chunks():
    chunks = [
        Chunk(source_id=f"RB{i:03d}", text=f"text {i}", span_start=0, span_end=6)
        for i in range(1, 15)
    ]
    msg = _format_user_message(_TICKET, chunks)
    # Only [1] through [8] should appear
    assert "[8]" in msg
    assert "[9]" not in msg


# ---------------------------------------------------------------------------
# _parse_tool_output
# ---------------------------------------------------------------------------

def test_parse_normal_diagnosis():
    raw = {
        "root_cause_hypothesis": "JWKS cache is stale after cert rotation.",
        "confidence": "high",
        "evidence_spans": [
            {"source_id": "RB001", "text": "JWKS endpoint rotated", "span_start": 0, "span_end": 21}
        ],
        "next_action": "Flush SDK JWKS cache for tenant.",
    }
    d = _parse_tool_output(raw)
    assert d.confidence == "high"
    assert len(d.evidence_spans) == 1
    assert d.evidence_spans[0].source_id == "RB001"
    assert d.abstain_reason is None


def test_parse_abstaining_diagnosis():
    raw = {
        "root_cause_hypothesis": "",
        "confidence": "low",
        "evidence_spans": [],
        "next_action": "",
        "abstain_reason": "evidence insufficient",
    }
    d = _parse_tool_output(raw)
    assert d.abstain_reason == "evidence insufficient"
    assert d.root_cause_hypothesis == ""


def test_parse_empty_abstain_reason_becomes_none():
    raw = {
        "root_cause_hypothesis": "something",
        "confidence": "medium",
        "evidence_spans": [],
        "next_action": "do something",
        "abstain_reason": "",
    }
    d = _parse_tool_output(raw)
    assert d.abstain_reason is None


# ---------------------------------------------------------------------------
# diagnose() — mocked Anthropic client
# ---------------------------------------------------------------------------

def _mock_response(tool_input: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_diagnosis"
    block.input = tool_input
    response = MagicMock()
    response.content = [block]
    return response


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("incidentops.agent.diagnose.anthropic.Anthropic")
def test_diagnose_returns_diagnosis_object(mock_client_cls):
    mock_client_cls.return_value.messages.create.return_value = _mock_response({
        "root_cause_hypothesis": "Stale JWKS cache after cert rotation.",
        "confidence": "high",
        "evidence_spans": [
            {"source_id": "RB001", "text": "JWKS", "span_start": 0, "span_end": 4}
        ],
        "next_action": "Flush SDK JWKS cache.",
    })
    result = diagnose(_TICKET, [_CHUNK])
    assert isinstance(result, Diagnosis)
    assert result.confidence == "high"
    assert result.abstain_reason is None


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
@patch("incidentops.agent.diagnose.anthropic.Anthropic")
def test_diagnose_abstains_on_empty_chunks(mock_client_cls):
    mock_client_cls.return_value.messages.create.return_value = _mock_response({
        "root_cause_hypothesis": "",
        "confidence": "low",
        "evidence_spans": [],
        "next_action": "",
        "abstain_reason": "no evidence retrieved",
    })
    result = diagnose(_TICKET, [])
    assert result.abstain_reason is not None


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
@patch("incidentops.agent.diagnose.anthropic.Anthropic")
def test_diagnose_validates_schema(mock_client_cls):
    """Output must pass Pydantic validation — model_validate should not raise."""
    mock_client_cls.return_value.messages.create.return_value = _mock_response({
        "root_cause_hypothesis": "cert rotated",
        "confidence": "medium",
        "evidence_spans": [],
        "next_action": "check runbook",
    })
    result = diagnose(_TICKET, [_CHUNK])
    Diagnosis.model_validate(result.model_dump())  # raises on invalid
