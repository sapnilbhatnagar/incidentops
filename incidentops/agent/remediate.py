"""AGENT-010: Opus-tier remediation draft — text only, no actions taken."""
from __future__ import annotations

import anthropic

from ..evals.schema import Diagnosis, RemediationDraft

_MODEL = "claude-opus-4-7"

_SYSTEM = """\
You are IncidentOps, a read-only SaaS support AI.

Given a confirmed diagnosis, produce a remediation draft for a human engineer to review and action.

Rules:
1. Steps must be actionable by a human — you cannot take any actions yourself.
2. Each step must be specific and ordered. No vague "investigate X".
3. Include a rollback step if the action could degrade service.
4. required_human_approver: name the role (e.g. "Customer admin", "Platform oncall") who must action each step.
5. Produce text only. Do not fabricate data, ticket IDs, or runbook IDs not present in the diagnosis.\
"""

_TOOL: dict = {
    "name": "submit_remediation",
    "description": "Submit the structured remediation draft.",
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered remediation steps for the human engineer.",
            },
            "expected_effect": {
                "type": "string",
                "description": "What should improve or resolve after steps are completed.",
            },
            "rollback_note": {
                "type": "string",
                "description": "How to reverse the change if it causes further degradation. Null if N/A.",
            },
            "required_human_approver": {
                "type": "string",
                "description": "Role that must review and execute the steps.",
            },
        },
        "required": ["steps", "expected_effect"],
    },
}


def _format_user_message(diagnosis: Diagnosis, ticket: dict) -> str:
    parts = [
        f"## Ticket\nID: {ticket.get('ticket_id', 'unknown')}",
        f"Title: {ticket.get('title', '')}",
        "",
        "## Confirmed diagnosis",
        f"Root cause: {diagnosis.root_cause_hypothesis}",
        f"Confidence: {diagnosis.confidence}",
        f"Next action: {diagnosis.next_action}",
        "",
        "## Evidence cited",
    ]
    for span in diagnosis.evidence_spans:
        parts.append(f"- [{span.source_id}] {span.text[:120]}")
    parts.append("\nDraft a remediation plan. Call submit_remediation.")
    return "\n".join(parts)


def remediate(diagnosis: Diagnosis, ticket: dict) -> RemediationDraft:
    """Produce a RemediationDraft for an already-confirmed Diagnosis."""
    if diagnosis.abstain_reason:
        return RemediationDraft(
            steps=["Escalate to senior support — diagnosis was not possible with available evidence."],
            expected_effect="Manual investigation by a human expert.",
            rollback_note=None,
            required_human_approver="Senior support engineer",
        )

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return RemediationDraft(
            steps=["ANTHROPIC_API_KEY not set — set env var to generate remediation."],
            expected_effect="",
            rollback_note=None,
            required_human_approver=None,
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "submit_remediation"},
        messages=[{"role": "user", "content": _format_user_message(diagnosis, ticket)}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_remediation":
            raw = block.input
            return RemediationDraft(
                steps=raw.get("steps", []),
                expected_effect=raw.get("expected_effect", ""),
                rollback_note=raw.get("rollback_note") or None,
                required_human_approver=raw.get("required_human_approver") or None,
            )

    return RemediationDraft(
        steps=["Model did not return a remediation plan — manual review required."],
        expected_effect="Unknown.",
        rollback_note=None,
        required_human_approver="Senior support engineer",
    )
