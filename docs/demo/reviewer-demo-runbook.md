# Reviewer Demo Runbook

This runbook supports a local reviewer walkthrough of the synthetic healthcare AI governance
platform through Milestone 8. It is for demonstration and review only.

## 1. Environment Setup

Use Python 3.11 or newer from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
```

## 2. Dependency Installation

Install the package with development dependencies. Streamlit is included as a runtime dependency
for the local reviewer portal.

```bash
pip install -e ".[dev]"
```

## 3. Full Data Generation Pipeline

Generate the deterministic synthetic governance state in order.

```bash
python scripts/generate_inventory.py
python scripts/generate_access.py
python scripts/generate_evidence.py
python scripts/generate_compliance.py
python scripts/generate_reporting.py
```

Expected deterministic anchors:

- 6 datasets, 5 models, and 4 research projects
- 10 access requests, 3 grants, 37 audit events
- 52 control results, 1 warning, 0 failures
- Governance posture `attention_required`
- Bounded risk score `3`

## 4. Reviewer Export Generation

Build the Milestone 8 reviewer handoff bundle.

```bash
python scripts/generate_reviewer_bundle.py
```

Generated files are written to `outputs/reviewer/`:

- `reviewer_briefing.json`
- `reviewer_briefing.md`
- `reviewer_kpis.csv`
- `reviewer_findings.csv`
- `reviewer_evidence_index.csv`
- `reviewer_filtered_views.csv`
- `reviewer_filtered_views.md`

## 5. Start The Streamlit Portal

```bash
streamlit run src/governance_platform/reviewer_app.py
```

Open the local URL printed by Streamlit. The app is local only and read only.

## 6. Recommended Demo Walkthrough

1. Executive posture
2. Inventory overview
3. High-risk model review
4. Rejected access request
5. Grant lifecycle
6. Audit correlation chain
7. Compliance finding
8. Evidence reference
9. Reviewer briefing export

## 7. What To Show On Each Portal Page

**Executive Governance Overview:** show posture `attention_required`, bounded risk score `3`,
control warning count `1`, failures `0`, inventory totals, access totals, and audit/evidence
completeness.

**Data & Model Governance:** filter models to `risk_tier=high` and show `MD-0003`, the Clinical
Note Summarization LLM. Note that it is pending, high risk, and has responsible AI review
`in_progress`.

**Research & Access Governance:** show rejected access request `AR-0002`, which references pending
project `RP-0003` and pending model `MD-0003`. Then show grant lifecycle states: active
`AG-0001`, expired `AG-0002`, and revoked `AG-0003`.

**Audit & Evidence:** filter audit events by research project `RP-0001` to show the request,
decision, grant, and lifecycle evidence chain for the approved population-health scenario.

**Compliance & Risk:** show warning control `CR-0034` for high-risk model `MD-0003`, risk
indicator `RI-0001`, and evidence reference `model:MD-0003`.

## 8. Evidence IDs And Drill-through Paths

Use these deterministic IDs during the review:

- `MD-0003` - high-risk pending LLM model
- `RP-0003` - pending clinical note summarization research project
- `AR-0002` - rejected request tied to pending project/model
- `AG-0001` - active grant for approved request `AR-0001`
- `AG-0002` - expired grant
- `AG-0003` - revoked grant
- `CR-0034` - warning control result for high-risk model readiness
- `RI-0001` - bounded risk indicator derived from `CR-0034`
- `model:MD-0003` - evidence reference for the compliance warning
- `evidence_pack:EVP-0001` - generated reviewer-readable evidence pack

Suggested drill-through path:

```text
Executive posture -> Data & Model Governance filter risk_tier=high -> MD-0003
-> Research & Access Governance request AR-0002 -> Audit & Evidence project RP-0001
-> Compliance & Risk result CR-0034 -> Evidence reference model:MD-0003
-> outputs/reviewer/reviewer_briefing.md
```

## 9. Shutdown Steps

Stop Streamlit with `Ctrl+C` in the terminal where it is running.

Optionally run the smoke check after stopping the manual portal session:

```bash
python scripts/smoke_reviewer_demo.py
```

The smoke check starts the app briefly in headless mode and stops it before exiting.
If the execution environment blocks local port binding, it reports that condition and validates
the Streamlit dependency and app entrypoint instead.

## 10. Limitations And Claim Boundaries

This demo is local, deterministic, read-only, and synthetic-data-only. It does not implement:

- production deployment or public hosting
- authentication, Entra ID, live RBAC, or real user accounts
- write/edit workflows, approval actions, or access provisioning
- live Snowflake connectivity
- Fabric deployment or Power BI `.pbix`
- Purview integration
- real-time monitoring, alerting, or enterprise observability
- Terraform deployment
- Salesforce integration
- regulatory certification

Treat the generated artifacts as reviewer handoff evidence for a portfolio/demo repository, not as
production governance evidence for a real healthcare environment.
