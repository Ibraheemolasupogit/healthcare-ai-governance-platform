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

**Partially implemented (Milestone 2).** `src/governance_platform/inventory/` implements a typed,
validated `AIModel` entity (owner, intended use, model type, risk tier, responsible AI review
status, monitoring requirement, `linked_dataset_ids`) and a deterministic synthetic model portfolio
covering low, medium, and high risk tiers. A high-risk model cannot be constructed as
`approval_status=approved` without `responsible_ai_review_status=approved`, and must have
`monitoring_required=true` — encoding this document's core rule as a validation invariant rather
than only prose. See the root [README's Inventory outputs section](../README.md#inventory-outputs).

Still not implemented: model training, deployment, inference, or monitoring; an approval workflow
or automated review engine (see the explicit non-goals in the platform's Milestone 2 scope); or any
persistent backing store.

## Related ADRs / planes

- Plane: Metadata / inventory, with review criteria owned by Risk / compliance
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
