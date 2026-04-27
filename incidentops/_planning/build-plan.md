# IncidentOps — Phased Build Plan

> **Status note (2026-04-27).** Phase 0 complete. Currently entering Phase 1. See `session-log.md` Session 5 entry for the latest state.

## Context

This plan turns the IncidentOps brief (`incidentops-brief.md`) into a working portfolio piece for the Tomoro.ai application (AI Delivery Lead, secondary: PM). The product — **IncidentOps** — is a grounded, action-aware agent for enterprise SaaS support that diagnoses incidents using runbooks, tickets, and telemetry. The brief locks the architecture (six-stage pipeline, read-only by registry, two-tier model routing, hybrid retrieval, HHH evals). What is missing is the build sequence: how a solo builder gets from "brief on disk" to "working product" without sprawling.

**Intended outcome.** A small, opinionated repo with a working agent over a credible synthetic corpus, an HHH-graded eval suite gated in CI, and a dashboard. Application packaging (proposal, Loom, outreach) is a separate workstream that runs after Phase 8 lands.

## Operating Constraints

- Solo builder, target window 3–4 weekends. Scope is portfolio not production.
- Read-only by architecture: mutating tools physically not in the registry. No exceptions.
- Provenance-first: every claim the agent surfaces must carry a source span pointer; without it the response fails the Honest grader.
- Two-tier routing: Haiku/Sonnet for triage and tool shaping, Opus for diagnosis and remediation drafting.
- HHH gates (per brief section 7): Honest gates block merges from Phase 2 onward; Harmless gates block from Phase 5 onward; Helpful is tracked but does not block until Phase 7.
- Keep the brief authoritative. If the build forces a brief change, change the brief in the same PR — never let code drift from spec.

## Phase Breakdown

### Phase 0 — Rename, Git Init, Contradiction Cleanup ✓ COMPLETE

Goal: rename the product, put the work under version control, get the spec, corpus, and supporting docs into one consistent voice before any code lands.

**Done in commit `255787b` (2026-04-27):**
- Renamed `ops-resilience-copilot-brief.md` → `incidentops-brief.md` and `ops-resilience-copilot/` → `incidentops/`. Sweep of in-content references complete.
- `git init` at repo root with `.gitignore` covering Python, Node, env, LanceDB, Inspect AI artefacts, Obsidian metadata.
- Brief §7.0 added: 20-row consolidated HHH metric table (single source of truth for the eval harness).
- `incidentops/data/gold-set-spec.md` written: schema for labelled incidents.
- Session log: top-of-file banner clarifying historical entries describe pre-rename / pre-pivot state; Session 5 entry recording the work.

### Phase 1 — Repo Scaffold + Corpus Expansion (1 day)

Goal: stand up the Python + Next.js skeleton and grow the corpus from seed to floor.

- Repo layout under `incidentops/`: `agent/`, `evals/`, `dashboard/`, `ops/`, `data/`. Pin Python 3.12 + uv, Next.js 14 + pnpm.
- Wire Claude Agent SDK, Inspect AI, LanceDB, ruff, pytest, Playwright (dashboard). One `Makefile` target each: `make corpus`, `make evals`, `make agent`, `make dash`.
- Corpus expansion targets: 5 → 15 runbooks, 10 → 80 tickets, 2 → 8 incidents. Telemetry samples extended proportionally. Gold set seeded with 30 labelled incidents validating against `gold-set-spec.md`.
- Synthetic-but-credible bar: every runbook needs symptoms / triage / investigation / common causes / remediation / escalation; every gold-labelled ticket needs a referenced runbook and a remediation paragraph an SRE would not laugh at.

Acceptance: `make corpus` produces a manifest with counts matching targets. 30 gold incidents validate against `gold-set-spec.md`.

### Phase 2 — HHH Eval Harness (1 day)

Goal: build the graders before the agent, so the agent has something to optimise against from day one.

- Inspect AI tasks for Helpful (task-completion), Honest (provenance + abstention), Harmless (tool-scope + escalation) — one task per dimension.
- Custom Python deterministic graders for: provenance-span match (Honest), runbook-citation precision (Honest), abstention on insufficient evidence (Honest), tool-call read-only invariant (Harmless), escalation-when-uncertain (Harmless), TAT proxy (Helpful).
- Pass bars from brief §7.0 codified as JSON config; harness prints pass/fail per dimension and an aggregate gate signal CI can read.
- Run all graders against the 30-incident gold set with a stub agent that always abstains. Confirm Honest passes (correctly abstains), Helpful fails (does nothing useful) — proves the harness works before the agent exists.

Acceptance: `make evals` runs end-to-end, produces a report, exits non-zero when any blocking grader fails. README documents how to add a new grader.

### Phase 3 — Retrieval Pipeline (1 day)

Goal: hybrid retrieval over the corpus with rerank, exposed as `retrieve(query, top_k)`.

- LanceDB index over chunked runbooks + incidents + ticket descriptions + telemetry summaries. Chunk size tuned for runbook section granularity.
- Hybrid: dense (Voyage or OpenAI embeddings) + BM25 + cross-encoder reranker. Each result carries `source_id`, `span_start`, `span_end`, `score`.
- Retrieval-only eval: top-k recall against gold-runbook field on the 30-incident set. Target: recall@5 ≥ 0.85.
- Provenance spans must round-trip cleanly — the Honest grader in Phase 2 will fail otherwise.

Acceptance: retrieval eval passes recall@5 target. Provenance spans validate against source files.

### Phase 4 — Diagnosis Stage (1 day)

Goal: the most-leveraged stage of the pipeline (per brief: 50–80% of resolution quality lives here).

- `diagnose(ticket, chunks) -> Diagnosis` returning structured: `root_cause_hypothesis`, `confidence`, `evidence_spans`, `next_action`, `abstain_reason | null`.
- Opus tier. Prompt explicitly forbids fabrication, requires per-claim span citation, requires abstention if confidence below threshold or evidence missing.
- Wired through Phase 2 eval suite; Honest gate enforced. Helpful gate tracked.
- Run against full 30-incident gold set. Iterate prompt until Honest passes; do not optimise Helpful past Honest.

Acceptance: Honest grader passes on 30/30. Diagnosis output schema validates 100%. No mutating language ("I will restart the worker") leaks through.

### Phase 5 — Tool Layer (read-only) (½ day)

Goal: five read-only tools the agent can compose during diagnosis and remediation drafting.

- `get_runbook(id)`, `search_tickets(query)`, `get_telemetry(tenant_id, window)`, `get_incident(id)`, `lookup_issue_code(code)`. Mutating tools are physically absent from the registry — there is no `restart_worker` to misuse.
- Haiku/Sonnet tier for tool-arg shaping. Tool schemas Pydantic-validated.
- Harmless graders activated: any attempt to invoke an unregistered tool is a hard fail; any tool call outside the read scope is a hard fail.

Acceptance: Harmless invariant grader passes 100%. Tool registry snapshot test: registered tools = exactly the five above.

### Phase 6 — Remediation Draft + Handoff (1 day)

Goal: the agent drafts the remediation an engineer would execute, and hands off cleanly when uncertain.

- `remediate(ticket, diagnosis, chunks) -> RemediationDraft` (steps, expected effect, rollback note, required human approver). Always read-only — produces text, not actions.
- `handoff(reason, package) -> HandoffPacket` (everything the next human needs: ticket, diagnosis, retrieved spans, draft, confidence trace).
- Adoption-ladder mode flag: `shadow | assist | guided`. Default `assist`. No `autonomous`.
- Helpful grader graduated to blocking. TAT proxy on gold set must beat the always-abstain stub by a defined margin.

Acceptance: full pipeline runs on 30 gold incidents end-to-end. All three HHH gates pass.

### Phase 7 — CI Integration (½ day)

Goal: every push runs the eval suite; merges blocked on Honest + Harmless red.

- GitHub Actions workflow: lint → unit → retrieval eval → HHH eval suite → dashboard build.
- Eval results uploaded as a workflow artefact and summarised in PR comment.
- Branch protection: main requires green Honest + Harmless. Helpful surfaced but advisory.

Acceptance: green CI on main. A test PR that breaks the read-only invariant is correctly blocked.

### Phase 8 — Dashboard (1 day)

Goal: the surface a buyer sees — incident in, diagnosis + draft + provenance out.

- Next.js 14 on Vercel. Three views: ticket queue, single-ticket workspace (diagnosis, evidence panel with clickable provenance), eval scoreboard (latest HHH numbers from CI artefact).
- No auth, no DB writes — reads from JSON artefacts produced by the eval run. Static-feeling demo, real data underneath.
- Playwright smoke test for the single-ticket workspace.

Acceptance: deployed Vercel URL. Demo flow works on three random gold incidents.

## Out of Scope (For Now)

Application packaging — proposal PDF, Loom, outreach email — is **not** in this build plan. The goal is the working product: agent, graded evals, dashboard, CI green.

## Critical Files

All paths relative to repo root (`incidentops/` GitHub repo).

**Already on disk:**
- `incidentops-brief.md` — authoritative spec
- `session-log.md` — decision audit trail; append after every phase
- `incidentops/data/` — corpus root (5 runbooks, 10 tickets, 2 incidents, 30 issue codes, telemetry samples)
- `incidentops/data/gold-set-spec.md` — gold-incident schema (Phase 0 ✓)
- `.gitignore` (Phase 0 ✓)

**To be created (key entry points):**
- `incidentops/agent/retrieval.py` — `retrieve(query, top_k)`
- `incidentops/agent/diagnosis.py` — `diagnose(ticket, chunks)`
- `incidentops/agent/tools.py` — five read-only tools, registry
- `incidentops/agent/remediation.py` — `remediate(...)`, `handoff(...)`
- `incidentops/evals/helpful/`, `evals/honest/`, `evals/harmless/` — Inspect AI tasks + custom graders
- `incidentops/dashboard/app/` — Next.js 14 surfaces
- `incidentops/ops/ci.yml` — GitHub Actions

## Risk Register

- **Gold-set quality cap.** If the 30-incident gold set has shallow ground truth, every grader downstream is overfit to fiction. Mitigation: spend disproportionate care on the first 10 — they set the bar for the rest.
- **Honest-vs-Helpful tradeoff.** Tightening Honest (citations, abstention) will tank Helpful before Phase 6. Don't chase Helpful early; brief explicitly orders the tradeoff.
- **Scope creep into autonomy.** Adoption ladder stops at `guided`. Any "let it act" suggestion gets routed back to the brief, not the code.

## Verification

End-to-end check that the product actually works:
1. Clone repo fresh, `make corpus && make evals && make agent` all green.
2. CI on main green; test PR violating read-only invariant correctly blocked.
3. Deployed dashboard reachable; ticket → diagnosis → provenance flow works on three random gold incidents.
4. HHH eval suite: Honest and Harmless gates pass 100% on the 30-incident gold set; Helpful beats the always-abstain baseline by the defined margin.
5. Session log updated with final state of each phase as it completes.
