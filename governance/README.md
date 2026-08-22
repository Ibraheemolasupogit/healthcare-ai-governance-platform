# Governance Operating Model

This directory documents the operating model for each governance domain the platform is designed
to support. Each document describes **intended** process, roles, and controls — a target for
later milestones to implement against the [policy-as-code and evidence-as-code
principles](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md).

**None of these processes are automated or enforced by this repository yet.** No engine reads
these documents; they are the design and reference material a future implementation is built
from. See [`reports/architecture.md`](../reports/architecture.md) for how each domain maps onto
the platform's seven governance planes.

As of Milestone 2, [`dataset_governance.md`](dataset_governance.md),
[`model_governance.md`](model_governance.md), and [`research_approval.md`](research_approval.md)
each have a concrete, typed, validated counterpart in
[`src/governance_platform/inventory/`](../src/governance_platform/inventory/). As of Milestone 3,
[`access_review.md`](access_review.md) has a concrete counterpart — a local governance simulation,
not live enforcement — in
[`src/governance_platform/access/`](../src/governance_platform/access/), which also implements the
"access requests must reference an approved, non-expired project" rule from
[`research_approval.md`](research_approval.md). As of Milestone 4,
[`audit_evidence.md`](audit_evidence.md) has a concrete counterpart — again a local, deterministic
simulation, not live audit-log ingestion — in
[`src/governance_platform/audit/`](../src/governance_platform/audit/), which records the events the
inventory and access planes above already produce. As of Milestone 5,
[`compliance_monitoring.md`](compliance_monitoring.md) has a concrete counterpart — local
deterministic control evaluation and bounded risk indicators, not certification or live
monitoring — in [`src/governance_platform/compliance/`](../src/governance_platform/compliance/).
As of Milestone 6, the implemented reporting plane in
[`src/governance_platform/reporting/`](../src/governance_platform/reporting/) derives governance
KPIs and executive summaries from those local outputs; the Fabric/Power BI files remain future
architecture specifications, not deployed artifacts. As of Milestone 7, the local reviewer portal
in [`src/governance_platform/reviewer_app.py`](../src/governance_platform/reviewer_app.py) provides
read-only review pages over generated outputs. As of Milestone 8,
[`src/governance_platform/reviewer/`](../src/governance_platform/reviewer/) also provides
deterministic reviewer briefing exports, saved reviewer views, an evidence index, and demo smoke
checks. These are local handoff artifacts only, not production workflow automation or regulatory
certification. As of Milestone 9, [`controls/`](controls/) documents the local policy/control
catalog, ownership, evidence requirements, traceability approach, lifecycle, reviewer
interpretation, and limitations over the implemented compliance controls; it is not a generic
policy engine or live enforcement system. See each document's "Current status" section for exactly
what that does and does not cover.

## Domains

| Document | Domain | Primary plane |
| --- | --- | --- |
| [dataset_governance.md](dataset_governance.md) | Dataset registration, classification, lifecycle | Metadata / inventory |
| [model_governance.md](model_governance.md) | Model registration, approval, lifecycle | Metadata / inventory |
| [research_approval.md](research_approval.md) | Research project approval | Access / research-control |
| [access_review.md](access_review.md) | Access request, grant, recertification | Access / research-control |
| [audit_evidence.md](audit_evidence.md) | Audit trail and evidence generation | Audit / evidence |
| [responsible_ai.md](responsible_ai.md) | Responsible AI review criteria | Risk / compliance |
| [compliance_monitoring.md](compliance_monitoring.md) | Ongoing compliance and risk monitoring | Risk / compliance |
| [controls/](controls/) | Policy/control catalog and traceability | Risk / compliance |

## Document structure

Each domain document follows the same shape: **Purpose**, **Scope**, **Key roles**, **Intended
controls**, **Current status**, and **Related ADRs / planes** — so the documents stay easy to scan
and easy to keep honest about what is (not) implemented.
