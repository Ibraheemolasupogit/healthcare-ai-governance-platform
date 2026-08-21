# Compliance Monitoring

## Purpose

Define how the platform's ongoing compliance posture — across datasets, models, access, and audit
history — is continuously scored and surfaced, so drift and violations are detected rather than
discovered only at audit time.

## Scope

Applies platform-wide: it is the aggregation layer that reads state from dataset/model governance,
research approval, access review, and audit/evidence, and produces a risk/compliance posture over
time. It does not itself hold source-of-truth governance state.

## Key roles

- **Risk / compliance plane maintainer** — operates scoring logic and monitoring tooling.
- **Compliance officer** — consumes compliance posture and risk scores via the reporting plane
  (Fabric / Power BI) and drives remediation.
- **Domain owners** (dataset, model, access) — responsible for remediating flagged issues in their
  domain.

## Intended controls

- Defined controls (e.g. "no active access grant against an expired project," "no approved model
  missing a responsible AI review at its risk tier") are evaluated against current governance and
  audit state on a regular cadence, per the policy-as-code principle (ADR
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)).
- Violations and drift are recorded and surfaced through the reporting plane, not just logged
  silently.
- A risk score is computed per dataset, model, and/or project from classification, access
  patterns, and audit history, giving oversight stakeholders a prioritised view rather than a raw
  event list.
- Compliance monitoring results feed evidence generation (see
  [`audit_evidence.md`](audit_evidence.md)) so posture claims are backed by reproducible
  evidence.

## Current status

**Not implemented.** No risk scoring engine, control evaluation, or monitoring tooling exists in
this repository. This document describes the intended process only.

## Related ADRs / planes

- Plane: Risk / compliance
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
