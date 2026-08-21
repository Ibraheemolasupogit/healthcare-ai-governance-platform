# Power BI Dashboards (intended design)

**No `.pbix` file, published dashboard, or Power BI workspace exists.** This document describes
intended dashboard pages for a future implementation milestone, per ADR
[0004](../../docs/architecture/decisions/0004-fabric-powerbi-as-future-reporting-layer.md). No
screenshots or exports are included because nothing has been built yet.

## Purpose

Surface governance state from the [intended semantic model](../semantic_model/README.md) to
oversight stakeholders — governance committees, compliance officers, research leadership — as
described in the reporting plane of [`reports/architecture.md`](../../reports/architecture.md).

## Intended dashboard pages

1. **Governance Overview** — inventory counts by classification/risk tier, active vs. expiring
   projects, headline compliance posture. The landing page for a governance committee.
2. **Access Review** — active access grants, grants due for recertification, time-to-grant
   trends. Primary view for access approvers and reviewers, backing
   [access_review.md](../../governance/access_review.md).
3. **Risk & Compliance** — open violations by control, risk score trends by dataset/model/project,
   drill-down to affected entities. Backing
   [compliance_monitoring.md](../../governance/compliance_monitoring.md).
4. **Audit Trail Explorer** — filterable view over audit events for a specific dataset, model, or
   researcher, supporting ad hoc audit questions. Backing
   [audit_evidence.md](../../governance/audit_evidence.md).

## Current status

**Not implemented.** This is a design document only. Building these pages depends on the intended
semantic model, which in turn depends on the metadata/inventory, access, audit, and
risk/compliance planes being implemented first — none of which exist yet in this repository.
