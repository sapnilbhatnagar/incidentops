---
name: Tomoro.ai application work product
description: Active project to build an unsolicited work product for AI Delivery Lead and PM roles at Tomoro.ai
type: project
---
User is building an unsolicited application work product for **Tomoro.ai**, targeting both the **AI Delivery Lead** role (primary) and **Product Manager** roles (secondary).

**Chosen use case (selected 2026-04-26, domain pivoted same day, renamed 2026-04-27):** "IncidentOps" (formerly "Ops Resilience Copilot") — a grounded, action-aware AI agent for **enterprise SaaS support and platform operations**. Synthetic archetype: **VertexCloud**, modelled on Salesforce / ServiceNow / Qinecsa Solutions tier players. Agent diagnoses customer-reported incidents in real time using a six-stage pipeline (triage, retrieval, diagnosis, read-only tool use, remediation, handoff) over the SaaS company's runbooks, ticket history, Slack threads, and live telemetry. Read-only by architecture; humans authorise every state change.

**Pivot note:** Original framing was UK retail bank payment ops (NorthStar Bank archetype, FPS scheme). User pivoted to enterprise SaaS on 2026-04-26 because "all SaaS companies face this problem" and TAT improvement is universal across SaaS support ops. Architecture decisions unchanged; only domain, archetype, and corpus changed. See `session-log.md` Session 4 entry for full pivot details.

**Work lives at:** GitHub repo `sapnilbhatnagar/incidentops`. Cloned locally — on Windows: `D:\Obsidian Vault\Sapnil Bhatnagar\knowledge base\Interview Preparation\10. product prototype\`; on macOS: wherever the user cloned it (typically `~/projects/incidentops/`). Two active top-level files: `incidentops-brief.md` (the deep brief) and `session-log.md` (decision audit trail). Synthetic corpus in `incidentops/data/` (5 runbooks, 10 tickets, 2 incidents, 30 SaaS issue codes, telemetry). The build plan lives in the repo at `incidentops/_planning/build-plan.md`. Always read the session log first when resuming.

**Why:** This is the post-Bauer pivot. The user is applying broadly across AI consultancies and product roles, with Tomoro.ai as the first concrete target. Their Edinburgh + UK-wide AI Delivery Lead role (£70k–£100k) is open and well-aligned.

**How to apply:** When the user resumes this project, do not re-derive context. Read `session-log.md` (focus on the most recent Session entry for current state), read sections 4, 5, and 7 (with the 7.0 consolidated HHH metric table) of `incidentops-brief.md`, then move into the next pending phase of `incidentops/_planning/build-plan.md`. As of 2026-04-27, Phase 0 is complete and Phase 1 (repo scaffold + corpus expansion) is the next pending phase. The gold set (`incidentops/data/gold-set-spec.md` is the schema; Phase 1 produces 30 items) is the bottleneck for everything downstream. Application packaging (proposal/Loom/outreach) was scoped out of the build plan — focus is the working product.
