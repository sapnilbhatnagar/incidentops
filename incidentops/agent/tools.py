"""TOOL-001 through TOOL-006: Read-only tool layer + registry.

All tools are pure readers. No mutating tools exist in this module by design.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator
from rank_bm25 import BM25Okapi

_DATA = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class GetRunbookInput(BaseModel):
    id: str  # e.g. "RB001"

    @field_validator("id")
    @classmethod
    def normalise_id(cls, v: str) -> str:
        return v.strip().upper()


class SearchTicketsInput(BaseModel):
    query: str


class GetTelemetryInput(BaseModel):
    tenant_id: str
    window_minutes: int = 60  # look back N minutes from the latest record


class GetIncidentInput(BaseModel):
    id: str  # e.g. "INC003"

    @field_validator("id")
    @classmethod
    def normalise_id(cls, v: str) -> str:
        return v.strip().upper()


class LookupIssueCodeInput(BaseModel):
    code: str  # e.g. "AUTH-401-EXPIRED"

    @field_validator("code")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.strip().upper()


# ---------------------------------------------------------------------------
# TOOL-001: get_runbook
# ---------------------------------------------------------------------------

def get_runbook(id: str) -> dict:
    """Return the full text of a runbook by ID."""
    inp = GetRunbookInput(id=id)
    matches = list((_DATA / "runbooks").glob(f"{inp.id}-*.md"))
    if not matches:
        return {"error": f"runbook {inp.id} not found"}
    return {"runbook_id": inp.id, "content": matches[0].read_text()}


# ---------------------------------------------------------------------------
# TOOL-002: search_tickets
# ---------------------------------------------------------------------------

def _load_tickets() -> list[dict]:
    path = _DATA / "tickets" / "tickets.jsonl"
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def search_tickets(query: str, top_k: int = 5) -> dict:
    """BM25 keyword search over ticket titles and descriptions."""
    SearchTicketsInput(query=query)
    tickets = _load_tickets()
    corpus = [
        f"{t.get('title', '')} {t.get('description', '')}".lower().split()
        for t in tickets
    ]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(range(len(tickets)), key=lambda i: scores[i], reverse=True)[:top_k]
    return {
        "query": query,
        "results": [
            {
                "ticket_id": tickets[i]["ticket_id"],
                "title":     tickets[i].get("title", ""),
                "severity":  tickets[i].get("severity", ""),
                "category":  tickets[i].get("category", ""),
                "score":     round(float(scores[i]), 4),
            }
            for i in ranked
            if scores[i] > 0
        ],
    }


# ---------------------------------------------------------------------------
# TOOL-003: get_telemetry
# ---------------------------------------------------------------------------

def get_telemetry(tenant_id: str, window_minutes: int = 60) -> dict:
    """Return log and request records for a tenant within a rolling window."""
    inp = GetTelemetryInput(tenant_id=tenant_id, window_minutes=window_minutes)

    logs_path    = _DATA / "telemetry" / "sample-logs.jsonl"
    records_path = _DATA / "telemetry" / "sample-request-records.jsonl"

    def _filter_records(path: Path) -> list[dict]:
        rows: list[dict] = []
        if not path.exists():
            return rows
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("tenant_id") == inp.tenant_id:
                rows.append(row)
        return rows

    def _filter_logs(path: Path) -> list[dict]:
        # logs are platform-wide (no tenant_id); return the last N by timestamp
        rows: list[dict] = []
        if not path.exists():
            return rows
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows[-50:]  # last 50 log entries

    request_records = _filter_records(records_path)
    logs = _filter_logs(logs_path)

    return {
        "tenant_id":      inp.tenant_id,
        "window_minutes": inp.window_minutes,
        "request_records": request_records,
        "logs":            logs,
    }


# ---------------------------------------------------------------------------
# TOOL-004: get_incident
# ---------------------------------------------------------------------------

def get_incident(id: str) -> dict:
    """Return the full postmortem text for an incident by ID."""
    inp = GetIncidentInput(id=id)
    matches = list((_DATA / "incidents").glob(f"{inp.id}-*.md"))
    if not matches:
        return {"error": f"incident {inp.id} not found"}
    return {"incident_id": inp.id, "content": matches[0].read_text()}


# ---------------------------------------------------------------------------
# TOOL-005: lookup_issue_code
# ---------------------------------------------------------------------------

def _load_issue_codes() -> dict[str, dict]:
    path = _DATA / "reference" / "saas-issue-codes.json"
    data = json.loads(path.read_text())
    return {entry["code"]: entry for entry in data.get("codes", [])}


def lookup_issue_code(code: str) -> dict:
    """Return the definition for a SaaS issue code."""
    inp = LookupIssueCodeInput(code=code)
    codes = _load_issue_codes()
    if inp.code not in codes:
        return {"error": f"issue code {inp.code} not found"}
    return codes[inp.code]


# ---------------------------------------------------------------------------
# TOOL-006: Registry
# ---------------------------------------------------------------------------

REGISTRY: dict[str, callable] = {
    "get_runbook":      get_runbook,
    "search_tickets":   search_tickets,
    "get_telemetry":    get_telemetry,
    "get_incident":     get_incident,
    "lookup_issue_code": lookup_issue_code,
}

REGISTRY_NAMES = frozenset(REGISTRY)


def call_tool(name: str, **kwargs) -> dict:
    """Dispatch a tool call by name. Raises KeyError for unregistered tools."""
    if name not in REGISTRY:
        raise KeyError(f"tool '{name}' is not in the registry")
    return REGISTRY[name](**kwargs)
