# Reviewer Demo Runbook

This runbook supports a local reviewer walkthrough of the synthetic healthcare AI governance
platform through Milestone 11. It is for demonstration and review only.

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

Build the Milestone 8 reviewer handoff bundle, Milestone 9 policy/control catalog, and
Milestone 10 assurance-history drift outputs, then build the Milestone 11 integrated assurance
review pack.

```bash
python scripts/generate_reviewer_bundle.py
python scripts/generate_policy_catalog.py
python scripts/generate_assurance_history.py
python scripts/generate_assurance_pack.py
```

Generated files are written to `outputs/reviewer/`:

- `reviewer_briefing.json`
- `reviewer_briefing.md`
- `reviewer_kpis.csv`
- `reviewer_findings.csv`
- `reviewer_evidence_index.csv`
- `reviewer_filtered_views.csv`
- `reviewer_filtered_views.md`

Policy catalog files are written to `outputs/policy/`:

- `policy_catalog.json`
- `control_catalog.json`
- `control_catalog.csv`
- `control_evidence_traceability.csv`
- `policy_assurance_summary.json`
- `policy_assurance_summary.md`

Assurance history files are written to `outputs/assurance/`:

- `assurance_snapshots.json`
- `assurance_comparison.json`
- `control_drift.csv`
- `risk_drift.csv`
- `assurance_drift_summary.json`
- `assurance_drift_report.md`

Integrated assurance review pack files are written to `outputs/assurance_pack/`:

- `assurance_review_pack.json`
- `priority_findings.csv`
- `reviewer_actions.csv`
- `assurance_evidence_map.csv`
- `assurance_review_pack.md`

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
9. Policy/control traceability
10. Assurance history and drift
11. Integrated assurance review pack
12. Reviewer briefing export

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

**Policy & Controls:** show local policy count `9`, implemented control count `26`, current
warning count `1`, and traceability rows for control `CTRL-0014`. Use the control table to show
implementation references and reviewer guidance.

**Assurance History / Drift:** show baseline snapshot `AS-0001` compared to controlled snapshot
`AS-0002`, risk score delta `-2`, resolved `CTRL-0014` for `MD-0003`, new low-severity `CTRL-0005`
operational warning, and changed policy IDs `POL-0008` and `POL-0009`.

**Assurance Review Pack:** show pack `ARP-0001`, priority finding `PF-0001` for the controlled
`CTRL-0005` drift, priority finding `PF-0002` for current `CTRL-0014` model-readiness warning,
reviewer actions `RA-0001` through `RA-0003`, and evidence map rows linking findings to policy,
control, evidence, and drift IDs.

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
- `POL-0008` - Responsible AI Readiness Policy
- `POL-0009` - Operational Governance Policy
- `CTRL-0014` - cataloged high-risk model readiness control
- `CTRL-0005` - review-date control used in the controlled drift snapshot
- `ER-CTRL-0014-01` - evidence requirement for `CTRL-0014`
- `AS-0001` - baseline assurance snapshot for canonical governance state
- `AS-0002` - controlled comparison assurance snapshot
- `AC-0001` - assurance comparison
- `CD-0001` / `CD-0002` - control drift rows in the generated comparison
- `ARP-0001` - integrated assurance review pack
- `PF-0001` - priority finding for the controlled `CTRL-0005` new-warning drift
- `PF-0002` - priority finding for the current `CTRL-0014` warning
- `RA-0001` - first review-only action in the integrated pack

Suggested drill-through path:

```text
Executive posture -> Data & Model Governance filter risk_tier=high -> MD-0003
-> Research & Access Governance request AR-0002 -> Audit & Evidence project RP-0001
-> Compliance & Risk result CR-0034 -> Evidence reference model:MD-0003
-> Policy & Controls filter CTRL-0014 -> outputs/policy/policy_assurance_summary.md
-> Assurance History / Drift -> outputs/assurance/assurance_drift_report.md
-> Assurance Review Pack -> outputs/assurance_pack/assurance_review_pack.md
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
- real-time monitoring, scheduled evaluation, alerting, or enterprise observability
- automatic remediation or a production history database
- workflow automation, notifications, or external governance integrations
- Terraform deployment
- Salesforce integration
- regulatory certification
- generic policy DSL, live policy enforcement, or automatic remediation

Treat the generated artifacts as reviewer handoff evidence for a portfolio/demo repository, not as
production governance evidence for a real healthcare environment.
