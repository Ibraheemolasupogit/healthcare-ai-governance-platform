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
aggregate summary. No evidence-pack generation or audit-report-producing code exists yet.
