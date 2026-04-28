# IncidentOps — Build Plan

> **How to use this file.**
> Every module has a feature ID. When referencing a module in conversation, use its ID (e.g. "fix CORPUS-002", "refactor AGENT-003"). Status column tracks progress. Check off `[x]` as each module lands. Read the latest Session entry in `session-log.md` to pick up context after a break.

---

## Feature ID Scheme

| Prefix | Domain |
|---|---|
| INFRA-### | Environment, tooling, Makefile |
| CORPUS-### | Synthetic data (runbooks, tickets, incidents, telemetry, gold set) |
| EVAL-### | HHH graders and eval harness |
| AGENT-### | Agent pipeline stages |
| TOOL-### | Read-only tool layer |
| DASH-### | Next.js dashboard views and components |
| CI-### | GitHub Actions, branch protection |

---

## Phase 0 — Rename, Git Init, Spec Cleanup ✓ COMPLETE

| ID | Module | Status |
|---|---|---|
| INFRA-000 | git init, .gitignore, initial commit | ✓ Done |
| CORPUS-000 | Rename corpus folder, sweep references | ✓ Done |
| EVAL-000 | HHH metric table added to brief §7.0 | ✓ Done |
| CORPUS-001 | gold-set-spec.md written | ✓ Done |

---

## Phase 1 — Repo Scaffold + Corpus Expansion

**Goal:** Stand up the Python + Next.js skeleton and grow the corpus from seed to floor so every downstream phase has real material to work against.

**Acceptance criteria:**
- `make corpus` produces a manifest showing target counts met
- `make evals` scaffold runs (even if all graders are stubs)
- `make dash` starts Next.js dev server without error
- 30 gold incidents validate against `gold-set-spec.md`

### 1A — Environment & Tooling

| ID | Module | Description | Status |
|---|---|---|---|
| INFRA-001 | Python env | `pyproject.toml` with Python 3.12, uv lockfile, ruff, pytest | [ ] |
| INFRA-002 | Node env | `package.json` with Next.js 14, pnpm lockfile, Playwright | [ ] |
| INFRA-003 | Directory skeleton | `agent/`, `evals/helpful/ honest/ harmless/`, `dashboard/`, `ops/`, `data/gold/` | [ ] |
| INFRA-004 | Makefile | Targets: `corpus`, `evals`, `agent`, `dash`, `lint`, `test` | [ ] |
| INFRA-005 | Dependency wiring | Claude Agent SDK, Inspect AI, LanceDB pinned in `pyproject.toml` | [ ] |

### 1B — Corpus Expansion

Current state: 5 runbooks, 10 tickets, 2 incidents, seed telemetry.
Target: 15 runbooks, 80 tickets, 8 incidents, extended telemetry, 30 gold-labelled incidents.

| ID | Module | Description | Status |
|---|---|---|---|
| CORPUS-002 | Runbook expansion | Add RB006–RB015 (10 new runbooks covering new SaaS failure domains) | [ ] |
| CORPUS-003 | Ticket expansion | Grow tickets.jsonl from 10 → 80 tickets (varied categories, severities, tenants) | [ ] |
| CORPUS-004 | Incident expansion | Add INC003–INC008 (6 new postmortems with 5-whys) | [ ] |
| CORPUS-005 | Telemetry extension | Extend sample-logs.jsonl and sample-request-records.jsonl proportionally | [ ] |
| CORPUS-006 | Gold set seeding | 30 labelled incidents validated against gold-set-spec.md, stored in `data/gold/` | [ ] |
| CORPUS-007 | Corpus manifest | `make corpus` emits JSON manifest with counts + validation result | [ ] |

---

## Phase 2 — HHH Eval Harness

**Goal:** Build graders before the agent. Every grader has a pass bar. Harness exits non-zero on hard gate failure.

| ID | Module | Description | Status |
|---|---|---|---|
| EVAL-001 | Task scaffolding | Three task modules (helpful / honest / harmless) with runner CLI | [x] |
| EVAL-002 | Citation coverage | Every claim must have an evidence span | [x] |
| EVAL-003 | Hallucination | All RB / TKT / INC IDs must exist in corpus | [x] |
| EVAL-004 | Calibration (Brier) | Confidence claims tracked vs ground truth | [x] |
| EVAL-005 | Read-only invariant | Registry frozen at exactly 5 tools | [x] |
| EVAL-006 | PII filter | Email, phone, card, IPv4, SSN patterns | [x] |
| EVAL-007 | Tenant isolation | No foreign-tenant ticket evidence | [x] |
| EVAL-008 | Retrieval recall@3 | Gold runbook in top-3 retrieved | [x] |
| EVAL-009 | Citation precision | Cited text actually appears in source | [x] |
| EVAL-010 | Schema validity | Diagnosis output validates against Pydantic model | [x] |
| EVAL-011 | Injection refusal | Refusal rate ≥ 0.95 on adversarial set (10 cases) | [x] |
| EVAL-012 | Out-of-scope refusal | Refusal rate ≥ 0.95 on legal/financial/HR set (10 cases) | [x] |
| EVAL-013 | Abstention quality | Agent abstains when retrieval is empty | [x] |
| EVAL-014 | Grader self-tests | 34 pytest cases — positive and negative for every grader | [x] |
| EVAL-015 | Config + CLI runner | config.json pass bars; run_evals.py exits 1 on hard gate fail | [x] |

---

## Phase 3 — Retrieval Pipeline

**Goal:** `retrieve(query, top_k)` over the full corpus. Every result carries provenance spans.

| ID | Module | Description | Status |
|---|---|---|---|
| AGENT-001 | Corpus chunker | Chunk runbooks + incidents + tickets at ~500 tokens, 50-token overlap | [x] |
| AGENT-002 | LanceDB indexer | Dense embedding index over chunks | [x] |
| AGENT-003 | BM25 index | Sparse keyword index alongside dense | [x] |
| AGENT-004 | Cross-encoder reranker | Rerank fused results, return top-K with source_id + span | [x] |
| AGENT-005 | `retrieve()` API | Public interface: `retrieve(query, top_k) -> List[Chunk]` | [x] |
| EVAL-011 | Retrieval eval | recall@5 ≥ 0.85 on 30-incident gold set | [ ] |

---

## Phase 4 — Diagnosis Stage

**Goal:** `diagnose(ticket, chunks) -> Diagnosis` with explicit confidence, citations, abstention.

| ID | Module | Description | Status |
|---|---|---|---|
| AGENT-006 | Diagnosis prompt | Opus-tier prompt: forbids fabrication, requires per-claim span citation, abstains below threshold | [ ] |
| AGENT-007 | `Diagnosis` schema | Pydantic: root_cause_hypothesis, confidence, evidence_spans, next_action, abstain_reason | [ ] |
| AGENT-008 | `diagnose()` API | Public interface wired to retrieval output | [ ] |
| EVAL-012 | Diagnosis eval | Honest grader pass on 30/30 gold; schema validates 100% | [ ] |

---

## Phase 5 — Read-Only Tool Layer

**Goal:** Five read-only tools registered. Mutating tools absent by architecture.

| ID | Module | Description | Status |
|---|---|---|---|
| TOOL-001 | `get_runbook(id)` | Returns runbook content by ID from corpus | [ ] |
| TOOL-002 | `search_tickets(query)` | Keyword + semantic search over tickets.jsonl | [ ] |
| TOOL-003 | `get_telemetry(tenant_id, window)` | Returns request + log records for a tenant | [ ] |
| TOOL-004 | `get_incident(id)` | Returns postmortem by ID | [ ] |
| TOOL-005 | `lookup_issue_code(code)` | Returns issue code definition from saas-issue-codes.json | [ ] |
| TOOL-006 | Tool registry | Pydantic-validated schemas; registry snapshot test | [ ] |
| EVAL-013 | Harmless tool invariant | Registry = exactly TOOL-001 through TOOL-005; 0 unregistered calls | [ ] |

---

## Phase 6 — Remediation Draft + Handoff

**Goal:** Full pipeline end-to-end. Agent drafts remediation and packages handoff for human reviewer.

| ID | Module | Description | Status |
|---|---|---|---|
| AGENT-009 | `RemediationDraft` schema | Steps, expected effect, rollback note, required human approver | [ ] |
| AGENT-010 | `remediate()` API | Opus-tier; produces text only, no actions | [ ] |
| AGENT-011 | `HandoffPacket` schema | Ticket + diagnosis + retrieved spans + draft + confidence trace | [ ] |
| AGENT-012 | `handoff()` API | Emits structured payload; mode flag: shadow / assist / guided | [ ] |
| AGENT-013 | Pipeline runner | Wires all 6 stages: triage → retrieve → diagnose → tools → remediate → handoff | [ ] |
| EVAL-014 | End-to-end eval | All 3 HHH gates pass on 30 gold incidents; Helpful beats always-abstain baseline | [ ] |

---

## Phase 7 — CI Integration

**Goal:** Every push runs evals. Merges blocked on Honest + Harmless red.

| ID | Module | Description | Status |
|---|---|---|---|
| CI-001 | GitHub Actions workflow | lint → unit → retrieval eval → HHH eval suite → dashboard build | [ ] |
| CI-002 | PR comment reporter | Eval results summarised as PR comment | [ ] |
| CI-003 | Branch protection | main requires green Honest + Harmless; Helpful advisory | [ ] |
| CI-004 | Read-only invariant gate | Test PR that breaks read-only invariant is correctly blocked | [ ] |

---

## Phase 8 — Dashboard

**Goal:** Visual surface — ticket in, diagnosis + draft + provenance out. Deployed on Vercel.

| ID | Module | Description | Status |
|---|---|---|---|
| DASH-001 | Ticket queue view | List of gold incidents with status and category | [ ] |
| DASH-002 | Single-ticket workspace | Diagnosis panel + evidence panel with clickable provenance | [ ] |
| DASH-003 | Eval scoreboard | Latest HHH numbers from CI artefact | [ ] |
| DASH-004 | Vercel deploy | Auto-deploy wired; public URL reachable | [ ] |
| DASH-005 | Playwright smoke test | Single-ticket workspace works on 3 random gold incidents | [ ] |

---

## Out of Scope

- Application packaging (proposal, Loom, outreach)
- Write actions of any kind in the tool registry
- Full autonomy mode — adoption ladder stops at "guided"
- Multilingual scope
- Custom model training
