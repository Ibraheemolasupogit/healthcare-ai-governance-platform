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

**Partially implemented (Milestone 3), as a local governance simulation.**
`src/governance_platform/access/` implements access-request intake, deterministic eligibility
evaluation, approval/rejection decisions, and time-bounded grant creation/revocation against the
Milestone 2 inventory (`src/governance_platform/inventory/`) — see the root
[README's Access outputs section](../README.md#access-outputs) for the full rule list.

This is a simulation run against an in-memory inventory snapshot with explicitly supplied
timestamps, not a live service, not enforcement against a real identity system, and not connected
to Snowflake or Entra ID. Still not implemented: periodic recertification of standing access (the
"reconfirm continued need, or revoke" cadence described above), a persistent backing store, or any
audit-event trail — this document's audit-event line still describes intent only (see
[`audit_evidence.md`](audit_evidence.md)). "Access to higher-classification datasets requires a
correspondingly senior approver" is also not implemented — the current policy checks are dataset/
model/project state and linkage, not approver seniority.

## Related ADRs / planes

- Plane: Access / research-control
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
