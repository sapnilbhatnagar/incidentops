"""Tests for the remediation and handoff stages."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import os

from incidentops.agent.chunker import Chunk
from incidentops.agent.handoff import handoff
from incidentops.agent.remediate import remediate
from incidentops.evals.schema import Diagnosis, EvidenceSpan, RemediationDraft


_TICKET = {"ticket_id": "TKT-2026-03-04-001", "title": "SSO login failure"}

_DIAGNOSIS = Diagnosis(
    root_cause_hypothesis="Stale JWKS cache after IdP cert rotation.",
    confidence="high",
    evidence_spans=[EvidenceSpan(source_id="RB001", text="JWKS", span_start=0, span_end=4)],
    next_action="Flush SDK JWKS cache for tenant.",
)

_ABSTAINING = Diagnosis(
    root_cause_hypothesis="",
    confidence="low",
    evidence_spans=[],
    next_action="",
    abstain_reason="evidence insufficient",
)


# ---------------------------------------------------------------------------
# remediate()
# ---------------------------------------------------------------------------

def _mock_remediation_response(raw: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_remediation"
    block.input = raw
    response = MagicMock()
    response.content = [block]
    return response


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
@patch("incidentops.agent.remediate.anthropic.Anthropic")
def test_remediate_returns_draft(mock_cls):
    mock_cls.return_value.messages.create.return_value = _mock_remediation_response({
        "steps": ["Ask customer to flush SDK cache.", "Confirm tokens accepted."],
        "expected_effect": "SSO logins resume within 5 minutes.",
        "rollback_note": None,
        "required_human_approver": "Customer admin",
    })
    draft = remediate(_DIAGNOSIS, _TICKET)
    assert isinstance(draft, RemediationDraft)
    assert len(draft.steps) == 2
    assert draft.required_human_approver == "Customer admin"


@patch("incidentops.agent.remediate.anthropic.Anthropic")
def test_remediate_abstaining_diagnosis_returns_escalation_draft(mock_cls):
    draft = remediate(_ABSTAINING, _TICKET)
    assert len(draft.steps) == 1
    assert "escalate" in draft.steps[0].lower()
    mock_cls.assert_not_called()


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
@patch("incidentops.agent.remediate.anthropic.Anthropic")
def test_remediate_null_rollback_becomes_none(mock_cls):
    mock_cls.return_value.messages.create.return_value = _mock_remediation_response({
        "steps": ["Do something."],
        "expected_effect": "It works.",
        "rollback_note": "",
        "required_human_approver": "",
    })
    draft = remediate(_DIAGNOSIS, _TICKET)
    assert draft.rollback_note is None
    assert draft.required_human_approver is None


# ---------------------------------------------------------------------------
# handoff()
# ---------------------------------------------------------------------------

_CHUNKS = [
    Chunk(source_id="RB001", text="JWKS", span_start=0, span_end=4),
    Chunk(source_id="RB005", text="tenant isolation", span_start=100, span_end=116),
]


def test_handoff_builds_packet():
    from incidentops.evals.schema import HandoffPacket
    packet = handoff("TKT-2026-03-04-001", _DIAGNOSIS, _CHUNKS, None, mode="shadow")
    assert isinstance(packet, HandoffPacket)
    assert packet.ticket_id == "TKT-2026-03-04-001"
    assert packet.mode == "shadow"
    assert packet.remediation is None


def test_handoff_extracted_source_ids():
    packet = handoff("TKT-2026-03-04-001", _DIAGNOSIS, _CHUNKS, None)
    assert packet.retrieved_source_ids == ["RB001", "RB005"]


def test_handoff_with_remediation():
    draft = RemediationDraft(
        steps=["Step 1."],
        expected_effect="Fixed.",
        rollback_note=None,
        required_human_approver=None,
    )
    packet = handoff("TKT-2026-03-04-001", _DIAGNOSIS, _CHUNKS, draft, mode="assist")
    assert packet.remediation is not None
    assert packet.mode == "assist"


def test_handoff_schema_validates():
    from incidentops.evals.schema import HandoffPacket
    packet = handoff("TKT-2026-03-04-001", _DIAGNOSIS, _CHUNKS, None)
    HandoffPacket.model_validate(packet.model_dump())
