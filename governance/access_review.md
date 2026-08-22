# Access Review

## Purpose

Define how access to inventoried datasets and models is requested, granted, and periodically
recertified, so that access reflects an approved research purpose at all times rather than only
at the moment it was first granted.

## Scope

Applies to any grant of access to an inventoried dataset or model. Depends on
[`research_approval.md`](research_approval.md) (an approved project must exist first) and on
dataset/model classification from [`dataset_governance.md`](dataset_governance.md) /
[`model_governance.md`](model_governance.md) (classification determines what level of access, if
any, is grantable).

## Key roles

- **Requester** — an individual requesting access under an approved project.
- **Access approver** — reviews and grants/denies an individual access request.
- **Access reviewer** — performs periodic recertification of standing access grants.
- **Access / research-control plane maintainer** — operates the system that tracks grants and
  their state.

## Intended controls

- Every access request references an approved project and a specific dataset or model; scope,
  duration, and justification are recorded.
- Grants are time-bounded by default, tied to the referencing project's expiry at the latest.
- Standing access is recertified on a defined cadence (e.g. quarterly) — a reviewer must
  reconfirm continued need, or the grant is revoked.
- Every grant, denial, and revocation is recorded as an auditable event (see
  [`audit_evidence.md`](audit_evidence.md)).
- Access to higher-classification datasets requires a correspondingly senior approver, per the
  classification recorded in dataset/model governance.

## Current status

**Not implemented.** No access-request intake, approval workflow, grant tracking, or
recertification engine exists in this repository. This document describes the intended process
only; it is not an access-review engine.

As of Milestone 2, the dataset/model classification this plane will depend on is a concrete,
validated inventory (`src/governance_platform/inventory/`) rather than only a documented intent —
see [`dataset_governance.md`](dataset_governance.md) and [`model_governance.md`](model_governance.md).
No access-review logic reads that inventory yet.

## Related ADRs / planes

- Plane: Access / research-control
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
