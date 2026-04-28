"""Tests for the read-only tool layer."""
from __future__ import annotations

import pytest

from incidentops.agent.tools import (
    REGISTRY_NAMES,
    call_tool,
    get_incident,
    get_runbook,
    get_telemetry,
    lookup_issue_code,
    search_tickets,
)
from incidentops.evals.graders import ALLOWED_TOOLS


# ---------------------------------------------------------------------------
# TOOL-006: Registry snapshot
# ---------------------------------------------------------------------------

def test_registry_names_match_allowed_tools():
    """REGISTRY must be exactly the 5 tools in ALLOWED_TOOLS — no more, no less."""
    assert REGISTRY_NAMES == ALLOWED_TOOLS


def test_registry_has_exactly_five_tools():
    assert len(REGISTRY_NAMES) == 5


def test_call_tool_raises_for_unregistered():
    with pytest.raises(KeyError, match="not in the registry"):
        call_tool("delete_tenant")


# ---------------------------------------------------------------------------
# TOOL-001: get_runbook
# ---------------------------------------------------------------------------

def test_get_runbook_returns_content_for_existing_id():
    result = get_runbook("RB001")
    assert "error" not in result
    assert "JWKS" in result["content"] or "Auth" in result["content"]


def test_get_runbook_normalises_lowercase_id():
    result = get_runbook("rb001")
    assert "error" not in result


def test_get_runbook_returns_error_for_missing_id():
    result = get_runbook("RB999")
    assert "error" in result


# ---------------------------------------------------------------------------
# TOOL-002: search_tickets
# ---------------------------------------------------------------------------

def test_search_tickets_returns_results_for_auth_query():
    result = search_tickets("SSO login failure SAML")
    assert "results" in result
    assert len(result["results"]) > 0


def test_search_tickets_results_have_required_fields():
    result = search_tickets("webhook delivery")
    for r in result["results"]:
        assert "ticket_id" in r
        assert "score" in r


def test_search_tickets_returns_empty_for_nonsense_query():
    result = search_tickets("xyzzy frobnicator quux")
    assert result["results"] == []


def test_search_tickets_returns_at_most_top_k():
    result = search_tickets("error", top_k=3)
    assert len(result["results"]) <= 3


# ---------------------------------------------------------------------------
# TOOL-003: get_telemetry
# ---------------------------------------------------------------------------

def test_get_telemetry_returns_records_for_known_tenant():
    result = get_telemetry("TEN-HELIO-2024")
    assert "request_records" in result
    assert "logs" in result
    assert all(r["tenant_id"] == "TEN-HELIO-2024" for r in result["request_records"])


def test_get_telemetry_returns_empty_records_for_unknown_tenant():
    result = get_telemetry("TEN-NONEXISTENT-9999")
    assert result["request_records"] == []


def test_get_telemetry_includes_logs():
    result = get_telemetry("TEN-HELIO-2024")
    assert len(result["logs"]) > 0


# ---------------------------------------------------------------------------
# TOOL-004: get_incident
# ---------------------------------------------------------------------------

def test_get_incident_returns_content_for_existing_id():
    result = get_incident("INC001")
    assert "error" not in result
    assert len(result["content"]) > 100


def test_get_incident_normalises_lowercase():
    result = get_incident("inc001")
    assert "error" not in result


def test_get_incident_returns_error_for_missing_id():
    result = get_incident("INC999")
    assert "error" in result


# ---------------------------------------------------------------------------
# TOOL-005: lookup_issue_code
# ---------------------------------------------------------------------------

def test_lookup_issue_code_finds_known_code():
    result = lookup_issue_code("AUTH-401-EXPIRED")
    assert "error" not in result
    assert result["code"] == "AUTH-401-EXPIRED"


def test_lookup_issue_code_normalises_case():
    result = lookup_issue_code("auth-401-expired")
    assert "error" not in result


def test_lookup_issue_code_returns_error_for_unknown_code():
    result = lookup_issue_code("FAKE-999-INVENTED")
    assert "error" in result


def test_lookup_issue_code_result_has_description():
    result = lookup_issue_code("RATE-429-TENANT")
    assert "description" in result
    assert "typical_action" in result
