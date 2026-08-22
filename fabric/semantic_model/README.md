# Fabric Semantic Model (future design)

**No Fabric workspace, capacity, deployed semantic model, live refresh, or `.pbip`/TMDL artifact
exists.** This document is a Milestone 6 semantic-model specification for a future Fabric/Power BI
implementation. The implemented reporting layer is local and deterministic in
`src/governance_platform/reporting/` and exports JSON/CSV/Markdown under `outputs/reporting/`.

## Purpose

Define a reporting-ready semantic contract over the synthetic governance outputs:
inventory, access-control state, audit/evidence, compliance findings, risk indicators, and overall
posture. The contract is intended to make a later Fabric semantic model straightforward without
claiming one has been deployed.

## Reporting Subject Areas

- Executive governance posture
- Dataset governance
- Model governance
- Research project governance
- Access request and grant lifecycle
- Rejected-access reasons
- Audit and evidence completeness
- Compliance control results
- Risk indicators and bounded risk score

## Fact-Style Entities

| Entity | Grain | Key | Source |
| --- | --- | --- | --- |
| `FactAccessRequest` | One access request | `request_id` | `outputs/access/access_control_state.json` |
| `FactApprovalDecision` | One approval/rejection decision | `decision_id` | `outputs/access/access_control_state.json` |
| `FactAccessGrant` | One access grant | `grant_id` | `outputs/access/access_control_state.json` |
| `FactAuditEvent` | One audit event | `event_id` | `outputs/evidence/audit_events.json` |
| `FactControlResult` | One evaluated control result | `result_id` | `outputs/compliance/control_results.json` |
| `FactRiskIndicator` | One risk indicator | `indicator_id` | `outputs/compliance/risk_indicators.json` |
| `FactGovernanceKPI` | One reporting KPI at one as-of timestamp | `metric_id` | `outputs/reporting/governance_kpis.json` |

## Dimension-Style Entities

| Entity | Grain | Key | Source |
| --- | --- | --- | --- |
| `DimDataset` | One inventoried dataset | `dataset_id` | `outputs/inventory/inventory_portfolio.json` |
| `DimModel` | One inventoried model | `model_id` | `outputs/inventory/inventory_portfolio.json` |
| `DimResearchProject` | One research project | `research_project_id` | `outputs/inventory/inventory_portfolio.json` |
| `DimControl` | One control definition | `control_id` | `src/governance_platform/compliance/controls.py` |
| `DimGovernanceDomain` | One reporting/control domain | `domain` | Reporting/compliance enums |
| `DimDate` | One calendar date | `date` | Derived from explicit source timestamps |

## Relationships

- `FactAccessRequest[research_project_id]` -> `DimResearchProject[research_project_id]`
- `FactApprovalDecision[request_id]` -> `FactAccessRequest[request_id]`
- `FactAccessGrant[request_id]` -> `FactAccessRequest[request_id]`
- `FactAccessGrant[research_project_id]` -> `DimResearchProject[research_project_id]`
- Grant-to-dataset/model relationships are many-to-many through bridge tables derived from
  `dataset_ids` and `model_ids`.
- `FactAuditEvent[request_id]` -> `FactAccessRequest[request_id]` where present.
- `FactAuditEvent[grant_id]` -> `FactAccessGrant[grant_id]` where present.
- `FactControlResult[control_id]` -> `DimControl[control_id]`
- `FactRiskIndicator` relates to `FactControlResult` through evidence references and to affected
  entities through `entity_type` + `entity_id`.
- `FactGovernanceKPI[source_refs]` provides lineage back to source artifacts; it is not a
  relational key without parsing.

## Suggested Measures

- Total datasets
- Approved datasets
- Datasets by sensitivity classification
- Total models
- Models by risk tier
- Total research projects
- Projects by approval state
- Total access requests
- Approved requests
- Rejected requests
- Access approval rate
- Active grants
- Expired grants
- Revoked grants
- Rejection reasons by category
- Total audit events
- Audit events by type
- Audit completeness status
- Evidence completeness status
- Traceable correlation chains
- Controls evaluated
- Controls passed
- Control warnings
- Control failures
- Control pass rate
- Findings by domain
- Findings by severity
- Risk indicator count
- Bounded risk score
- Risk indicators by severity
- Overall governance posture

## Current Status

Implemented locally: deterministic reporting models and KPI generation in
`src/governance_platform/reporting/`, plus reproducible outputs from
`python scripts/generate_reporting.py`.

Planned only: deployed Fabric semantic model, Fabric workspace integration, Power BI dataset/report
publishing, live refresh, tenant integration, and any real Snowflake-backed source.
