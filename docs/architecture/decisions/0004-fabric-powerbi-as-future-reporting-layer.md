# 0004. Fabric / Power BI as future reporting layer

**Status:** Accepted

## Context

Governance state — inventory, access, audit, and risk/compliance data — is only useful to
oversight stakeholders (governance committees, compliance officers, research leadership) if it is
surfaced legibly, not queried directly from source systems. The platform needs a designated
reporting layer, and Microsoft Fabric / Power BI is a realistic, enterprise-standard choice for
healthcare and life-sciences organisations, consistent with Snowflake being the designated
governed data platform (ADR [0003](0003-snowflake-as-future-governed-platform.md)).

No semantic model, dataset, or dashboard exists yet — this repository contains no `.pbix` files
and no Fabric workspace configuration.

## Decision

Microsoft Fabric (as the semantic modelling layer) and Power BI (as the dashboard/reporting
surface) are designated as the platform's future reporting plane. Later milestones that implement
the reporting plane will build a Fabric semantic model over the governed Snowflake data/metadata
layer and publish Power BI dashboards from it. Until then, `fabric/semantic_model/` and
`fabric/dashboards/` contain only documentation of the intended model and dashboard design — no
`.pbix` files, no fabricated screenshots, and no claim that a Fabric tenant or Power BI workspace
exists.

## Consequences

- Reporting design (star-schema shape, planned dashboard pages) can be documented and reviewed
  before any implementation effort, giving later milestones a clear target.
- This repository must not include placeholder or fake `.pbix` files, exported screenshots, or
  any artifact implying a published dashboard before one is actually built.
- Any future Fabric/Power BI implementation will need synthetic governance data flowing from the
  earlier planes (inventory, access, audit, risk) before it has anything real to model — this ADR
  does not commit to a specific milestone ordering beyond that dependency.
