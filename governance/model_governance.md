# Model Governance

## Purpose

Define how AI/ML models used in healthcare research are registered, reviewed, and tracked through
their lifecycle, so every model in the platform has a known owner, a known intended use, a known
risk tier, and a documented approval before it can be used against governed data.

## Scope

Applies to any model (statistical, ML, or LLM-based) proposed for use against inventoried datasets
within the platform. Excludes model training infrastructure itself, which is out of scope for
governance and belongs to the engineering/infrastructure plane.

## Key roles

- **Model owner** — accountable for a model's documented intended use and continued validity.
- **Model risk reviewer** — evaluates a model against the responsible AI review criteria in
  [`responsible_ai.md`](responsible_ai.md) before approval.
- **Metadata/inventory plane maintainer** — operates the system of record models are registered
  into, alongside datasets.

## Intended controls

- Every model is registered with: owner, intended use, training data provenance (referencing
  inventoried datasets), risk tier, and lifecycle state (proposed → under review → approved →
  deployed → retired).
- Higher risk-tier models require a recorded responsible AI review before moving to "approved."
- Model registration links to the dataset(s) it was trained or evaluated on, so risk/compliance
  scoring can trace a model's data lineage.
- Retired models are retained in inventory for audit continuity but blocked from new usage grants.

## Current status

**Not implemented.** `src/governance_platform/inventory/` is a placeholder module; no model
registration, risk tiering, or approval workflow exists. No approval engine or automated review is
implemented — see the explicit non-goals in the platform's Milestone 1 scope.

## Related ADRs / planes

- Plane: Metadata / inventory, with review criteria owned by Risk / compliance
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
