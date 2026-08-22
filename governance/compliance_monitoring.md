# Compliance Monitoring

## Purpose

Define how the platform's compliance posture — across the local synthetic inventory,
access-control state, audit trail, and evidence pack — is evaluated and surfaced in a
deterministic, evidence-backed way.

## Scope

Applies platform-wide within this repository's current local simulation: it reads state from
dataset/model governance, research approval, access review, and audit/evidence, and produces a
risk/compliance posture for a supplied evaluation timestamp. It does not itself hold
source-of-truth governance state.

## Key roles

- **Risk / compliance plane maintainer** — operates control evaluation and scoring logic.
- **Compliance officer** — consumes compliance posture and risk scores via the reporting plane
  generated Markdown/JSON outputs and, in a later milestone, through the reporting plane.
- **Domain owners** (dataset, model, access) — responsible for remediating flagged issues in their
  domain.

## Implemented controls

- A fixed control set is evaluated against the current deterministic governance state, per the
  policy-as-code principle (ADR
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)).
- Control domains are restrained to: inventory governance, dataset governance, model governance,
  research governance, access governance, audit completeness, evidence completeness, responsible
  AI readiness, and operational governance.
- Controls check inventory uniqueness and reference resolution, the synthetic-data-only invariant,
  ownership/stewardship metadata, review dates, active grant compatibility with dataset/model/
  project state, access-decision evidence, rejected-request handling, grant time bounds, audit
  completeness, lifecycle events, correlation chains, duplicate audit IDs, and compliance
  evidence-reference resolution.
- All findings are returned rather than stopping at the first failure, with stable finding codes
  and evidence references back to inventory, access, audit, evidence-pack, or ADR artifacts.
- Risk indicators are derived only from warning and failed control results using the bounded
  severity scale `low=1`, `medium=3`, `high=5`, `critical=8`, capped at 100 total. This is not
  predictive modelling.
- Posture thresholds are explicit: `healthy` when all controls pass, `attention_required` when any
  warning/failure exists or score is at least 5, and `high_risk` for any critical failure, at
  least 3 failures, or score at least 25.

## Policy catalog and traceability

As of Milestone 9, the implemented controls are also cataloged in
`src/governance_platform/compliance/catalog.py` and documented in
[`governance/controls/`](controls/). The catalog derives from the existing control definitions,
maps controls to local policy metadata, records implementation references, defines evidence
requirements, and generates a control-to-evidence traceability matrix under `outputs/policy/`.
This is reviewer traceability over implemented local controls, not a generic policy engine or
external certification framework.

## Current status

**Implemented as of Milestone 5, locally and deterministically.**
`src/governance_platform/compliance/` contains typed immutable control, result, risk indicator,
summary, and assessment models; fixed control definitions; deterministic evaluation; bounded risk
indicator derivation; posture classification; JSON/CSV/Markdown export; and validation helpers.
`scripts/generate_compliance.py` writes reproducible outputs to `outputs/compliance/`.
As of Milestone 9, `scripts/generate_policy_catalog.py` writes policy/control catalog and
traceability outputs to `outputs/policy/`.

This is not formal regulatory compliance, NHS DSPT certification, UK GDPR certification, MHRA
approval, ISO certification, live enterprise monitoring, alerting, or production policy
enforcement.

## Related ADRs / planes

- Plane: Risk / compliance
- ADRs: [0002](../docs/architecture/decisions/0002-modular-governance-architecture.md),
  [0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)
