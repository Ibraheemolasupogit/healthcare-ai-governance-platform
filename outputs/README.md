# Outputs

Local, gitignored destination for generated artifacts — evidence packs, reports, exports — that
later milestones will produce from code, per the evidence-as-code principle (ADR
[0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)).

Nothing in this directory is committed to version control except this file and `.gitkeep` (see
[`.gitignore`](../.gitignore)): outputs are reproducible from source data and code, not stored as
static artifacts in the repository.

## Current status

As of Milestone 2, `inventory/` is populated by running `python scripts/generate_inventory.py`
(see the root [README's Inventory outputs section](../README.md#inventory-outputs)): the
deterministic synthetic dataset/model/research-project inventory as JSON and CSV, plus an
aggregate summary.

As of Milestone 3, `access/` is populated by running `python scripts/generate_access.py` (see the
root [README's Access outputs section](../README.md#access-outputs)): the deterministic synthetic
access requests, approval decisions, and grants produced by running the Milestone 3 scenarios
through `governance_platform.access.AccessControlService` against the Milestone 2 inventory, plus
an aggregate access-review summary.

As of Milestone 4, `evidence/` is populated by running `python scripts/generate_evidence.py` (see
the root [README's Evidence outputs section](../README.md#evidence-outputs)): the append-only audit
log (JSON and CSV) built deterministically from the existing inventory and access-control output, an
aggregate audit summary, and a deterministic, reviewer-readable evidence pack (JSON and Markdown).
This is a local governance simulation — no live Snowflake query-history/audit-log ingestion, SIEM,
Microsoft Purview, or Entra ID integration exists.

As of Milestone 5, `compliance/` is populated by running
`python scripts/generate_compliance.py` (see the root
[README's Compliance outputs section](../README.md#compliance-outputs)): deterministic control
results, bounded risk indicators, a canonical compliance assessment summary, and a
reviewer-readable governance posture report. This is local control evaluation over synthetic
state only — not regulatory certification, live monitoring, alerting, or production enforcement.

As of Milestone 6, `reporting/` is populated by running
`python scripts/generate_reporting.py` (see the root
[README's Reporting outputs section](../README.md#reporting-outputs)): deterministic governance
KPI rows, a canonical reporting snapshot, and a concise executive summary. This is local reporting
over synthetic state only — not a deployed Fabric semantic model, Power BI report, live refresh,
or tenant integration.

As of Milestone 8, `reviewer/` is populated by running
`python scripts/generate_reviewer_bundle.py` (see the root
[README's Reviewer export and demo handoff section](../README.md#reviewer-export-and-demo-handoff)):
a deterministic reviewer briefing, reviewer KPI/findings exports, a reviewer-friendly evidence
index, and compact saved reviewer views. This is local reviewer handoff packaging over generated
synthetic outputs only — not production hosting, authentication, Power BI/Fabric deployment, live
tenant integration, monitoring, alerting, or regulatory certification.

As of Milestone 9, `policy/` is populated by running
`python scripts/generate_policy_catalog.py` (see the root
[README's Policy and control catalog outputs section](../README.md#policy-and-control-catalog-outputs)):
local policy metadata, a control catalog, control-to-evidence traceability, and a reviewer-readable
policy assurance summary derived from implemented compliance controls and generated evidence refs.
This is local governance metadata only — not a generic policy DSL, live enforcement, automatic
remediation, production compliance orchestration, or regulatory certification.

As of Milestone 10, `assurance/` is populated by running
`python scripts/generate_assurance_history.py` (see the root
[README's Assurance history and drift outputs section](../README.md#assurance-history-and-drift-outputs)):
explicit local assurance snapshots, a deterministic snapshot comparison, control drift, risk
drift, summary metrics, and a reviewer-readable change report. This is local historical
comparison over synthetic snapshots only — not real-time monitoring, scheduling, alerting,
automatic remediation, production observability, a production history store, or regulatory
certification.

As of Milestone 11, `assurance_pack/` is populated by running
`python scripts/generate_assurance_pack.py` (see the root
[README's Integrated assurance review pack outputs section](../README.md#integrated-assurance-review-pack-outputs)):
a concise integrated assurance review pack, priority findings, reviewer actions, and a compact
finding/control/policy/evidence/drift map. This is reviewer handoff packaging over generated
synthetic outputs only — not new control logic, new risk scoring, workflow automation,
notifications, remediation, production observability, external governance integration, or
regulatory certification.

As of Milestone 12, `readiness/` is populated by running
`python scripts/generate_review_readiness.py` (see the root
[README's Reviewer acceptance and demo readiness outputs section](../README.md#reviewer-acceptance-and-demo-readiness-outputs)):
a deterministic acceptance checklist, semantic artifact completeness evidence, demo-readiness
result, and concise review-readiness report. This is local review-readiness evidence only — not
human review, organisational approval, governance-board sign-off, production acceptance, or
regulatory certification.
