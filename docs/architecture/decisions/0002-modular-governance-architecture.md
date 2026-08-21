# 0002. Modular governance architecture (seven planes)

**Status:** Accepted

## Context

Healthcare AI governance covers distinct concerns — policy definition, inventory, access control,
audit, risk scoring, reporting, and the infrastructure underneath — that are typically owned by
different roles (data engineering, security/compliance, research leadership, oversight
committees) and evolve on different timelines. A single monolithic "governance module" would
couple these concerns together, making it hard to implement, test, or reason about them
independently, and hard to build the platform incrementally across milestones without large
modules half-implementing several concerns at once.

## Decision

The platform is organised into seven planes, each with a single responsibility and a clear
boundary, described in full in [`reports/architecture.md`](../../../reports/architecture.md):

1. Governance control plane (policy-as-code)
2. Metadata / inventory plane (datasets, models)
3. Access / research-control plane (approval, access governance)
4. Audit / evidence plane (audit trail, evidence generation)
5. Risk / compliance plane (scoring, monitoring)
6. Reporting plane (Fabric / Power BI)
7. Engineering / infrastructure plane (Docker, Terraform, CI/CD, Snowflake)

This is mirrored directly in the repository layout: `governance/` for operating-model docs,
`src/governance_platform/{inventory,access,audit,risk,responsible_ai,reporting}/` for the
corresponding code modules, `infrastructure/` and `fabric/` for the platforms each plane depends
on. Planes communicate through defined interfaces (shared inventory/audit identifiers) rather than
reaching into each other's internals, so later milestones can implement one plane at a time.

## Consequences

- Each milestone can implement one or two planes end-to-end (schema, logic, tests, docs) without
  needing to finish the others first — Milestone 1 deliberately implements zero governance
  logic and only the infrastructure plane's foundation.
- The seven-plane split adds structural overhead relative to a single script or notebook; this is
  accepted because the goal is to demonstrate an enterprise-shaped platform, not the fastest path
  to a demo.
- Cross-plane features (e.g. a risk score that depends on inventory classification and audit
  history) require explicit interfaces between planes rather than shared mutable state — this is
  intentional and will be revisited in a future ADR once the first cross-plane feature is built.
