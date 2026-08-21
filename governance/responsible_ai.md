# Responsible AI

## Purpose

Define the review criteria a model must satisfy before approval, covering fairness, robustness,
explainability, and appropriateness of use in a healthcare research context — inputs to the model
governance approval step, not a separate approval track.

## Scope

Applies to any model registered under [`model_governance.md`](model_governance.md), scaled by risk
tier: higher-risk models (e.g. those informing decisions closer to patient care, even in a
synthetic research context) require deeper review.

## Key roles

- **Model risk reviewer** — evaluates a model against these criteria and records findings.
- **Model owner** — responsible for remediating findings before re-review.
- **Risk / compliance plane maintainer** — operates any tooling that runs automated portions of
  this review in a later milestone.

## Intended review criteria

- **Intended use fit** — is the model's registered intended use appropriate for the data it was
  trained/evaluated on, and does it stay within the scope approved for the underlying dataset(s)?
- **Fairness / bias** — has performance been evaluated across relevant subgroups present in the
  (synthetic) data, and are material disparities documented?
- **Robustness** — has the model been evaluated for stability under reasonable input variation
  and data drift?
- **Explainability** — is there a documented, appropriate level of interpretability for the
  model's risk tier and intended use?
- **Human oversight** — is there a defined point of human review before the model's output
  informs any downstream decision?

## Current status

**Not implemented.** No automated responsible AI checks, scoring, or review tooling exist in this
repository. This document defines criteria for a future reviewer (human or automated) to apply; it
is not itself an enforcement mechanism.

## Related ADRs / planes

- Plane: Risk / compliance (feeding into Metadata / inventory approval)
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
