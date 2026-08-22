# Audit & Evidence

## Purpose

Define how governed activity — dataset/model registration and approval, project approval, access
grants, access exercised — is captured as an immutable audit trail, and how evidence artifacts are
produced from that trail for internal review or external audit.

## Scope

Applies to every state-changing action across the other governance domains: dataset/model
governance, research approval, and access review. The audit plane is a consumer of events from
those domains, not a producer of governance decisions itself.

## Key roles

- **Event producers** — the dataset/model, research approval, and access review processes, each
  responsible for emitting an audit event when their state changes.
- **Audit/evidence plane maintainer** — operates the immutable event store and evidence generation
  tooling.
- **Auditor / compliance reviewer** — consumes generated evidence artifacts.

## Intended controls

- Every governance state change (registration, classification change, approval, grant, denial,
  revocation, recertification) is recorded as an immutable, timestamped audit event referencing
  the actor, the entity, and the action.
- Audit events are append-only; corrections are recorded as new events, not edits to history.
- Evidence artifacts (e.g. "show every access grant to dataset X in the last quarter and its
  current recertification status") are generated deterministically from the audit event store, per
  the evidence-as-code principle (ADR
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)), not
  assembled by hand.
- Generated evidence artifacts land in [`outputs/`](../outputs/), which is gitignored — evidence
  is reproducible from source data, not committed to version control.

## Traceability relationship

As of Milestone 9, audit and evidence outputs are referenced by the local policy/control catalog's
traceability matrix. Controls that require lifecycle events, correlation chains, duplicate audit ID
checks, and evidence-reference resolution point back to generated audit/evidence identifiers such
as `audit_log:audit_events`, `audit_event:AE-0033`, and `evidence_pack:EVP-0001`. This adds
reviewer traceability over existing generated evidence; it does not introduce live audit ingestion
or production audit enforcement.

## Current status

**Partially implemented (Milestone 4), as a local, deterministic governance simulation.**
`src/governance_platform/audit/` implements a typed, immutable `AuditEvent`, an append-only
`AuditLog` (no update/remove method on its public API — corrections would be new events, not
edits, exactly as described above), deterministic event generation over the existing Milestone 2/3
inventory and access-control output, evidence-completeness checks, and a deterministic evidence
pack (JSON and Markdown) built from references, identifiers, timestamps, decisions, and control
outcomes. See the root [README's Evidence outputs section](../README.md#evidence-outputs) for the
event taxonomy, correlation approach, and limitations.

This is a local simulation over data this repository already generates, not a live event store —
there is no audit-event *ingestion* from a real system: no Snowflake query-history/audit-log
collection, no SIEM, no Microsoft Purview or Entra ID audit-log integration, and no real-time
streaming. Generated evidence artifacts land in `outputs/evidence/`, which is gitignored, per the
paragraph above.
As of Milestone 9, selected audit/evidence references also appear in
`outputs/policy/control_evidence_traceability.csv` for reviewer traceability.

## Related ADRs / planes

- Plane: Audit / evidence
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
