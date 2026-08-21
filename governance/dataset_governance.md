# Dataset Governance

## Purpose

Define how datasets used in healthcare AI research are registered, classified, and tracked
through their lifecycle, so that every dataset in the platform has a known owner, a known
sensitivity level, and a known state before anyone can request access to it.

## Scope

Applies to any dataset intended for use in AI model training, evaluation, or research analysis
within the platform — synthetic in this project, by design (see ADR
[0001](../docs/architecture/decisions/0001-synthetic-data-only.md)). Excludes raw source-system
data outside the platform's inventory.

## Key roles

- **Dataset owner** — accountable for a dataset's classification and continued fitness for use.
- **Data governance steward** — reviews and approves dataset registration and classification.
- **Metadata/inventory plane maintainer** — operates the system of record datasets are registered
  into.

## Intended controls

- Every dataset is registered with: owner, source/provenance, sensitivity classification, intended
  use, and lifecycle state (proposed → approved → active → deprecated → retired).
- Sensitivity classification determines the access controls later enforced by the access/
  research-control plane and the masking/row-access policies documented in
  [`infrastructure/snowflake/`](../infrastructure/snowflake/).
- Datasets cannot move to "active" without a recorded governance steward approval.
- Deprecated/retired datasets are retained in inventory (for audit continuity) but blocked from
  new access grants.

## Current status

**Not implemented.** `src/governance_platform/inventory/` is a placeholder module; no dataset
registration, classification, or lifecycle logic exists. No synthetic dataset inventory has been
generated yet.

## Related ADRs / planes

- Plane: Metadata / inventory (see [`reports/architecture.md`](../reports/architecture.md))
- ADRs: [0001](../docs/architecture/decisions/0001-synthetic-data-only.md),
  [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
