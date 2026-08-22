# Research Approval

## Purpose

Define how a proposed research project — a stated purpose for using one or more inventoried
datasets and/or models — is reviewed and approved before it can be used as the basis for an access
grant.

## Scope

Applies to any research activity within the platform that would require access to governed
datasets or models. A project must exist and be approved before an individual access request
(see [`access_review.md`](access_review.md)) can reference it.

## Key roles

- **Research requester** — proposes a project with a stated purpose and requested scope.
- **Research approval committee** — reviews project proposals against governance policy and
  approves, rejects, or requests changes.
- **Access / research-control plane maintainer** — operates the system that tracks project status
  and links it to subsequent access grants.

## Intended controls

- A project proposal records: requester, stated research purpose, requested datasets/models,
  intended duration, and approval status (proposed → under review → approved → expired/closed).
- Access requests must reference an approved, non-expired project; there is no standing access
  independent of an approved research purpose.
- Approved projects have an expiry date; access tied to an expired project is expected to be
  revoked as part of access review, not to lapse silently.
- Project approval decisions are recorded as auditable events (see
  [`audit_evidence.md`](audit_evidence.md)).

## Current status

**Partially implemented (Milestone 2).** `src/governance_platform/inventory/` implements a typed,
validated `ResearchProject` entity (principal owner, purpose, `linked_dataset_ids`,
`linked_model_ids`, approval status, risk classification, start/expiry dates, workspace status) as
part of the metadata/inventory plane, and a deterministic synthetic portfolio covering approved,
pending, and expired projects. A project's dataset/model references must resolve to entities that
actually exist in the same inventory. See the root
[README's Inventory outputs section](../README.md#inventory-outputs).

Still not implemented: project intake, an approval workflow, expiry handling (an expired project's
`approval_status` is asserted metadata, not computed or enforced against the current date), or
workspace provisioning. This document describes the intended process only.

As of Milestone 3, "Access requests must reference an approved, non-expired project" (above) is a
concrete, enforced check: `src/governance_platform/access/policy.py` rejects any access request
whose referenced project is missing, not approved, or has `approval_status=expired` — see
[`access_review.md`](access_review.md) and the root
[README's Access outputs section](../README.md#access-outputs).

## Related ADRs / planes

- Plane: Access / research-control
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
