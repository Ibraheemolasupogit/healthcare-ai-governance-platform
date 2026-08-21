# Fabric Semantic Model (intended design)

**No Fabric workspace, capacity, or semantic model exists.** This document describes the intended
design for a future implementation milestone, per ADR
[0004](../../docs/architecture/decisions/0004-fabric-powerbi-as-future-reporting-layer.md). It
contains no Fabric artifact (`.pbip`, `.tmdl`, dataset definition) — only a design description.

## Purpose

Model governance state — inventory, access, audit, and risk/compliance data — from the intended
Snowflake governed platform into a semantic layer Power BI dashboards can query, per
[`reports/architecture.md`](../../reports/architecture.md)'s reporting plane.

## Intended shape: star schema

**Fact tables** (one row per event/state snapshot):

- `fact_access_grant` — one row per access grant, referencing dataset/model, researcher, project,
  and status (active, expired, revoked). Backs [access_review.md](../../governance/access_review.md).
- `fact_audit_event` — one row per audit event (registration, approval, grant, revocation),
  referencing the acting entity and affected object. Backs
  [audit_evidence.md](../../governance/audit_evidence.md).
- `fact_risk_score` — one row per (entity, scoring date), holding a computed risk/compliance
  score. Backs [compliance_monitoring.md](../../governance/compliance_monitoring.md).

**Dimension tables:**

- `dim_dataset` — dataset inventory: owner, sensitivity classification, lifecycle state.
- `dim_model` — model inventory: owner, risk tier, lifecycle state.
- `dim_researcher` — researcher identity and role.
- `dim_project` — approved research project, status, expiry.
- `dim_control` — governance control definition, for mapping risk scores and audit events back to
  the policy-as-code control that was evaluated.
- `dim_date` — standard date dimension for time-based reporting.

## Intended measures (illustrative, not implemented)

- Active access grants by classification tier
- Access grants past recertification due date
- Open compliance violations by control
- Median time from access request to grant
- Model approval rate by risk tier

## Current status

**Not implemented.** No Fabric workspace, dataset, or semantic model file exists in this
repository. This design assumes the metadata/inventory, access, audit, and risk/compliance planes
are implemented first, since the semantic model has nothing to model without them.
