# Power BI Dashboard Specification (future design)

**No `.pbix` file, published dashboard, screenshot, Power BI workspace, or Fabric deployment
exists.** This is a Milestone 6 dashboard specification over the local deterministic reporting
outputs. It is architecture/documentation only.

## Source Contract

Future dashboards should read from the semantic model described in
[`../semantic_model/README.md`](../semantic_model/README.md), whose local source equivalent is:

- `outputs/reporting/governance_kpis.json`
- `outputs/reporting/reporting_snapshot.json`
- `outputs/compliance/control_results.json`
- `outputs/compliance/risk_indicators.json`
- `outputs/evidence/audit_events.json`
- `outputs/access/access_control_state.json`
- `outputs/inventory/inventory_portfolio.json`

## Page 1: Executive Governance Overview

- **KPIs:** overall governance posture, total datasets, total models, total research projects,
  active grants, controls passed, control warnings, control failures, bounded risk score.
- **Charts:** KPI trend placeholder by snapshot date, findings by severity, findings by domain,
  active/expired/revoked grants.
- **Tables:** top non-passing control results, risk indicators, recent audit event types.
- **Filters/slicers:** as-of date, governance domain, severity, posture.
- **Drill-through:** from posture or warning counts to Compliance & Risk page.
- **Fields:** `FactGovernanceKPI.metric_name`, `value`, `as_of`, `metric_domain`;
  `FactControlResult.status`, `severity`, `finding_code`; `FactRiskIndicator.score`.

## Page 2: Data & Model Governance

- **KPIs:** approved datasets, datasets by sensitivity, total models, models by risk tier,
  all-datasets-synthetic-only flag.
- **Charts:** datasets by sensitivity classification, models by risk tier, dataset/model approval
  state.
- **Tables:** dataset inventory, model inventory, model linked datasets, responsible-AI review
  status.
- **Filters/slicers:** sensitivity classification, dataset approval status, model risk tier,
  lifecycle status, responsible-AI review status.
- **Drill-through:** dataset -> grants using that dataset; model -> projects and grants using that
  model.
- **Fields:** `DimDataset.*`, `DimModel.*`, `FactAccessGrant.dataset_ids`,
  `FactAccessGrant.model_ids`, `FactControlResult.entity_id`.

## Page 3: Research & Access Governance

- **KPIs:** total access requests, approved requests, rejected requests, approval rate, active
  grants, expired grants, revoked grants.
- **Charts:** request status distribution, rejection reasons, grant lifecycle status by project,
  request volume by project.
- **Tables:** access requests, decisions, grants with project and requester identifiers.
- **Filters/slicers:** project, request status, decision type, grant status, requester role,
  rejection reason.
- **Drill-through:** rejected request -> decision reason and audit chain; grant -> project scope
  and lifecycle evidence.
- **Fields:** `FactAccessRequest.*`, `FactApprovalDecision.*`, `FactAccessGrant.*`,
  `DimResearchProject.*`.

## Page 4: Audit & Evidence

- **KPIs:** total audit events, audit completeness status, evidence completeness status, traceable
  correlation chains.
- **Charts:** audit events by event type, audit outcomes, events by research project, lifecycle
  event coverage.
- **Tables:** audit event explorer, correlation groups, evidence pack completeness problems.
- **Filters/slicers:** event type, outcome, entity type, research project, correlation ID.
- **Drill-through:** correlation ID -> full event chain; grant -> creation/revocation/expiry
  evidence.
- **Fields:** `FactAuditEvent.*`, `FactAccessRequest.request_id`, `FactAccessGrant.grant_id`,
  evidence-pack correlation fields.

## Page 5: Compliance & Risk

- **KPIs:** controls evaluated, controls passed, warnings, failures, pass rate, risk indicator
  count, bounded risk score, overall posture.
- **Charts:** findings by severity, findings by domain, control result status distribution, risk
  indicators by severity/category.
- **Tables:** control results with evidence references, risk indicators with rationale, domain
  finding summary.
- **Filters/slicers:** control domain, control ID, finding code, status, severity, risk category,
  affected entity type.
- **Drill-through:** control result -> evidence references and affected entity; risk indicator ->
  originating finding and source artifact.
- **Fields:** `FactControlResult.*`, `FactRiskIndicator.*`, `DimControl.*`,
  `DimGovernanceDomain.*`.

## Current Status

Implemented locally: deterministic governance KPI generation and executive summary Markdown under
`outputs/reporting/`.

Planned only: deployed Power BI report, `.pbix`/PBIP artifacts, Fabric workspace creation, live
refresh, tenant integration, and production data connectivity.
