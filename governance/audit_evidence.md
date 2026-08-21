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

## Current status

**Not implemented.** No audit event store, event emission, or evidence generation exists in this
repository. There is no audit-event simulator. This document describes the intended process only.

## Related ADRs / planes

- Plane: Audit / evidence
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
