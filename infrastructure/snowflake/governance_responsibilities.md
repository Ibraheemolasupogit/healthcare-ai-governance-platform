# Snowflake: Intended Governance Responsibilities

**Status: design intent only.** No live Snowflake account backs any of this. All SQL below is
illustrative of intended shape, not code that has been executed anywhere in this project.

## 1. Role-based access control (RBAC)

Intended to enforce the access grants defined by the [access review operating
model](../../governance/access_review.md) using Snowflake's native role hierarchy: a functional
role per governance persona (e.g. `RESEARCHER_ROLE`, `DATA_STEWARD_ROLE`, `AUDITOR_ROLE`) granted
to users, and access roles scoped to specific database objects granted to functional roles —
avoiding direct object grants to individual users so every grant is traceable to a role a
governance process controls.

```sql
-- Illustrative only — not executed against any account.
CREATE ROLE IF NOT EXISTS researcher_role;
GRANT ROLE researcher_role TO ROLE data_steward_role; -- example hierarchy, not prescriptive
```

## 2. Object tagging for inventory

Intended to back the [dataset](../../governance/dataset_governance.md) and
[model](../../governance/model_governance.md) governance inventory using Snowflake object tags —
e.g. `SENSITIVITY_CLASSIFICATION`, `DATASET_OWNER`, `LIFECYCLE_STATE` — applied to tables/views
representing inventoried datasets, so inventory metadata lives alongside the data it describes and
is queryable via `ACCOUNT_USAGE.TAG_REFERENCES`.

## 3. Masking and row access policies

Intended to enforce dataset sensitivity classification at query time: dynamic data masking
policies on sensitive columns, and row access policies scoping visible rows to what a given access
role has been granted, per the classification recorded in the metadata/inventory plane. Since all
data in this platform is synthetic (ADR
[0001](../../docs/architecture/decisions/0001-synthetic-data-only.md)), these policies would
govern synthetic sensitivity labels, not real PHI.

## 4. Native audit logging

Intended to back the [audit/evidence plane](../../governance/audit_evidence.md) using Snowflake's
`ACCOUNT_USAGE` and `INFORMATION_SCHEMA` views (query history, access history, grants-to-users
history) as an input to the platform's own append-only audit event store, rather than
re-implementing query logging independently.

## 5. Resource monitors and network policies

Intended as operational guardrails once a real (still non-production, sandbox-style) account is
provisioned in a later milestone: resource monitors to bound compute spend, and network policies
to restrict account access to expected origins. Not relevant to governance logic directly, but
part of the responsible operation of the platform once it exists.

## Mapping to governance planes

| Responsibility | Governance plane | Governance doc |
| --- | --- | --- |
| RBAC | Access / research-control | [access_review.md](../../governance/access_review.md) |
| Object tagging | Metadata / inventory | [dataset_governance.md](../../governance/dataset_governance.md), [model_governance.md](../../governance/model_governance.md) |
| Masking / row access | Access / research-control | [access_review.md](../../governance/access_review.md) |
| Audit logging | Audit / evidence | [audit_evidence.md](../../governance/audit_evidence.md) |
| Resource monitors / network policy | Engineering / infrastructure | [reports/architecture.md](../../reports/architecture.md) |
