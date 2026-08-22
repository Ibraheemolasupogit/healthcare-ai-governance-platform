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
