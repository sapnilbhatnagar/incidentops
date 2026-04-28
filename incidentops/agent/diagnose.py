"""AGENT-006 + AGENT-008: Opus-tier diagnosis stage."""
from __future__ import annotations

import anthropic

from .chunker import Chunk
from ..evals.schema import Diagnosis, EvidenceSpan

_MODEL = "claude-opus-4-7"
_MAX_CHUNKS = 8

_SYSTEM = """\
You are IncidentOps, a read-only AI assistant for SaaS support engineers.

Given a support ticket and numbered evidence blocks, produce a root-cause diagnosis.

Rules — any violation fails the honesty check:
1. Every claim in root_cause_hypothesis must be supported by an exact verbatim quote
   from the evidence blocks. Include that quote in evidence_spans with the block's
   source_id, span_start, and span_end.
2. Never mention runbook IDs, ticket IDs, or incident IDs that are not in the
   evidence blocks. If you need to reference one, quote the evidence text instead.
3. If the evidence does not support a confident hypothesis, set abstain_reason and
   leave root_cause_hypothesis and next_action empty.
4. confidence: "high" = direct evidence; "medium" = partial evidence + inference;
   "low" = speculation only (abstain instead if low).
5. next_action is one concrete step for the support engineer — not a list.\
"""

_TOOL: dict = {
    "name": "submit_diagnosis",
    "description": "Submit the structured diagnosis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause_hypothesis": {"type": "string"},
            "confidence":            {"type": "string", "enum": ["high", "medium", "low"]},
            "evidence_spans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id":  {"type": "string"},
                        "text":       {"type": "string"},
                        "span_start": {"type": "integer"},
                        "span_end":   {"type": "integer"},
                    },
                    "required": ["source_id", "text", "span_start", "span_end"],
                },
            },
            "next_action":    {"type": "string"},
            "abstain_reason": {"type": "string"},
        },
        "required": ["root_cause_hypothesis", "confidence", "evidence_spans", "next_action"],
    },
}


def _format_user_message(ticket: dict, chunks: list[Chunk]) -> str:
    parts: list[str] = ["## Ticket"]
    parts.append(f"ID: {ticket.get('ticket_id', 'unknown')}")
    if tenant := ticket.get("tenant_id"):
        parts.append(f"Tenant: {tenant}")
    if title := ticket.get("title"):
        parts.append(f"Title: {title}")
    if desc := ticket.get("description"):
        parts.append(f"Description: {desc}")
    if severity := ticket.get("severity"):
        parts.append(f"Severity: {severity}")

    parts.append("\n## Evidence blocks")
    capped = chunks[:_MAX_CHUNKS]
    if not capped:
        parts.append("(none — abstain)")
    for i, chunk in enumerate(capped, 1):
        parts.append(
            f"\n[{i}] source_id: {chunk.source_id} | "
            f"span: {chunk.span_start}–{chunk.span_end}\n{chunk.text}"
        )

    parts.append(
        "\nUse only the evidence above. "
        "Call submit_diagnosis. "
        "For each claim, quote the exact text from the block and copy its source_id, "
        "span_start, and span_end."
    )
    return "\n".join(parts)


def _parse_tool_output(raw: dict) -> Diagnosis:
    spans = [
        EvidenceSpan(
            source_id=s["source_id"],
            text=s["text"],
            span_start=s["span_start"],
            span_end=s["span_end"],
        )
        for s in raw.get("evidence_spans", [])
    ]
    return Diagnosis(
        root_cause_hypothesis=raw.get("root_cause_hypothesis", ""),
        confidence=raw.get("confidence", "low"),
        evidence_spans=spans,
        next_action=raw.get("next_action", ""),
        abstain_reason=raw.get("abstain_reason") or None,
    )


def diagnose(ticket: dict, chunks: list[Chunk]) -> Diagnosis:
    """Call Opus to produce a Diagnosis from a ticket and retrieved evidence."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return Diagnosis(
            root_cause_hypothesis="",
            confidence="low",
            evidence_spans=[],
            next_action="",
            abstain_reason="ANTHROPIC_API_KEY not set — set env var or use stub mode",
        )
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = _format_user_message(ticket, chunks)

    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "submit_diagnosis"},
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_diagnosis":
            return _parse_tool_output(block.input)

    # Fallback: model didn't call the tool (should not happen with tool_choice forced)
    return Diagnosis(
        root_cause_hypothesis="",
        confidence="low",
        evidence_spans=[],
        next_action="",
        abstain_reason="model did not call submit_diagnosis",
    )
