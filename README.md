# Healthcare AI Governance & Secure Research Platform

> **Portfolio project. Synthetic data only.** This repository does not connect to, represent,
> or imply the existence of any real healthcare organisation, patient data, production Snowflake
> account, Microsoft Fabric tenant, secure research environment, or live cloud infrastructure.
> Every dataset, credential, tenant, and workload referenced here is fictional or intentionally
> unimplemented until explicitly built and labelled as such.

## What this is

A from-scratch, architecture-first foundation for a platform that governs the use of AI in a
healthcare research setting: what datasets and models exist, who is allowed to access them, what
research they're approved for, how that activity is audited, how risk and compliance are scored,
and how all of it is reported to oversight stakeholders.

The platform is being built in milestones. **This repository currently contains Milestone 1
(Platform Foundation), Milestone 2 (Synthetic Research & AI Inventory), Milestone 3 (Access &
Research Control Plane), Milestone 4 (Audit & Evidence Plane), Milestone 5 (Risk &
Compliance Monitoring Plane), Milestone 6 (Governance Reporting & Semantic Plane), and
Milestone 7 (Local Governance Reviewer Portal).**
Milestone 2 adds a typed, validated metadata/inventory plane and a deterministic synthetic
dataset/model/research portfolio generated from it. Milestone 3 adds a **local governance
simulation** of the access request → decision → grant → revocation/expiry workflow, evaluated
deterministically against that inventory. Milestone 4 adds an append-only audit trail over
Milestones 2–3's activity and a deterministic, reviewer-readable evidence pack derived from it.
Milestone 5 adds deterministic control evaluation, compliance findings, bounded risk indicators,
and a governance posture over that same local state. Milestone 6 adds reporting-ready semantic
contracts, deterministic governance KPIs, and an executive summary over existing outputs.
Milestone 7 adds a local Streamlit reviewer portal over those generated outputs. No model
approval automation, responsible AI workflow automation, live identity/RBAC/SIEM enforcement,
authentication, production hosting, or Fabric/Power BI deployment has been implemented yet. See
[Implemented vs. Planned](#implemented-vs-planned) below before assuming any capability exists.

## Platform intent

The platform is designed around seven governance planes, described in full in
[`reports/architecture.md`](reports/architecture.md):

- **Governance control plane** — policy and control definitions (policy-as-code)
- **Metadata / inventory plane** — dataset and model inventory
- **Access / research-control plane** — research approval and access governance
- **Audit / evidence plane** — auditability and evidence generation
- **Risk / compliance plane** — compliance and risk scoring
- **Reporting plane** — Fabric / Power BI governance reporting
- **Engineering / infrastructure plane** — Docker, Terraform, CI/CD, and the future Snowflake
  data/metadata platform

Core technologies planned across the platform: Python, SQL, Snowflake, Microsoft Fabric, Power
BI, Docker, Terraform, GitHub Actions, and policy-as-code tooling.

## Repository structure

```
.
├── data/                       # Synthetic data only (empty; generated inventory lives in outputs/)
├── src/governance_platform/
│   ├── inventory/              # Metadata/inventory plane: entities, generation, validation, I/O
│   ├── access/                 # Access/research-control plane: request/decision/grant simulation
│   ├── audit/                  # Audit/evidence plane: append-only log + evidence-pack generation
│   ├── compliance/             # Risk/compliance plane: controls, findings, posture outputs
│   ├── reporting/              # Reporting plane: deterministic KPIs and snapshots
│   ├── reviewer/               # Reviewer portal data-loading/filter/drill-through helpers
│   └── reviewer_app.py         # Local Streamlit reviewer portal
├── governance/                 # Governance operating-model documentation
├── infrastructure/
│   ├── docker/                 # Minimal local development container
│   ├── terraform/              # Restrained IaC foundation (no live infra)
│   └── snowflake/              # Documented intent, no live account/credentials
├── fabric/
│   ├── semantic_model/         # Documented intent, no semantic model built yet
│   └── dashboards/             # Documented intent, no PBIX/dashboards built yet
├── config/                     # Non-secret configuration scaffolding
├── outputs/
│   ├── inventory/              # Generated inventory CSV/JSON (gitignored, reproducible)
│   ├── access/                 # Generated access requests/decisions/grants (gitignored)
│   ├── evidence/               # Generated audit log + evidence pack (gitignored)
│   ├── compliance/             # Generated control/risk/posture outputs (gitignored)
│   └── reporting/              # Generated reporting KPIs/snapshot (gitignored)
├── reports/
│   └── architecture.md         # Full architecture write-up + diagram
├── docs/
│   └── architecture/decisions/ # Architecture Decision Records (ADRs)
├── scripts/
│   ├── generate_inventory.py   # Generate/validate/export the synthetic inventory
│   ├── generate_access.py      # Generate/evaluate/validate/export the access-control state
│   ├── generate_evidence.py    # Build the audit log/evidence pack from the above
│   ├── generate_compliance.py  # Evaluate controls and export compliance posture
│   └── generate_reporting.py   # Build reporting KPIs and executive summary
├── tests/                      # Foundation + inventory + access + audit + compliance + reporting + reviewer
└── .github/workflows/          # CI: install, lint, test, validate
```

## Implemented vs. Planned

### Implemented (Milestone 7 — Local Governance Reviewer Portal)

- A local reviewer-facing Streamlit app (`src/governance_platform/reviewer_app.py`) over the
  generated synthetic governance outputs — not a production web app, hosted service, Fabric
  report, Power BI dashboard, or authenticated application
- A clean UI data-access layer (`src/governance_platform/reviewer/`) that loads canonical outputs
  through existing loaders (`outputs/inventory`, `outputs/access`, `outputs/evidence`,
  `outputs/compliance`, `outputs/reporting`) and prepares deterministic reviewer-friendly rows;
  it does not hard-code or duplicate governance source state
- Five read-only reviewer sections: Executive Governance Overview, Data & Model Governance,
  Research & Access Governance, Audit & Evidence, and Compliance & Risk
- Deterministic KPI views, restrained built-in Streamlit charts, readable tables, source/evidence
  identifiers, useful empty states, and filters/search for dataset/model/project/access/audit/
  control/risk review
- Drill-through helpers by research project, request, grant, and evidence reference, linking
  related requests, decisions, grants, audit events, control results, risk indicators, and
  source records
- Clear missing-output handling: if generated artifacts are absent, the portal reports the
  missing files and lists the generation commands to run
- pytest coverage for portal data loading, source-output validation, filtering helpers, KPI
  lookup, drill-through selection, status aggregation, missing-output handling, stable sorting,
  and synthetic-data safeguards

Run locally after generating outputs:

```bash
streamlit run src/governance_platform/reviewer_app.py
```

This portal is a local portfolio/demo interface only. It has no editing or approval workflows,
authentication, role-based application access, production hosting, live refresh, alerting, or
regulatory certification.

### Implemented (Milestone 6 — Governance Reporting & Semantic Plane)

- The reporting plane (`src/governance_platform/reporting/`), as a **local deterministic
  reporting layer** over existing synthetic governance state — not a deployed Microsoft Fabric
  semantic model, Power BI report, live refresh, or tenant integration
- Typed, immutable reporting models: `GovernanceKPI` and `ReportingSnapshot`, with strict enum
  vocabularies for metric domains and units, source references on every KPI, and deterministic KPI
  ordering
- Governance KPIs derived from existing source-of-truth state and summary APIs: inventory posture,
  dataset governance, model governance, research governance, access-control activity, grant
  lifecycle status, rejected-access reasons, audit activity, evidence completeness, compliance
  control results, risk indicators, bounded risk score, and overall governance posture
- Loading, export, source-reference validation, and concise executive Markdown summary generation
  — see [Reporting outputs](#reporting-outputs) below
- `scripts/generate_reporting.py` — builds the same deterministic inventory, access, audit,
  evidence, and compliance state as prior milestones, derives KPIs and a reporting snapshot,
  writes outputs, then reloads and validates canonical JSON and source references
- Fabric semantic-model and dashboard specifications in `fabric/semantic_model/` and
  `fabric/dashboards/`, documenting future fact-style entities, dimension-style entities, keys,
  relationships, grains, measures, pages, filters, and drill-through paths without creating or
  claiming any deployed Fabric or Power BI artifact
- pytest coverage for reporting model validation, metric calculations, source-reference integrity,
  approval/pass-rate calculations, grant status metrics, audit metrics, compliance metrics, risk
  metrics, snapshot construction, deterministic ordering, export/reload, deterministic output
  generation, and synthetic-data safeguards

This plane packages the current local governance state for review. It does not deploy Fabric,
create `.pbix` files, call Fabric REST APIs, create workspaces, connect to Snowflake, perform live
refresh, or assert regulatory certification.

### Implemented (Milestone 5 — Risk & Compliance Monitoring Plane)

- The risk/compliance plane (`src/governance_platform/compliance/`), as a **local,
  deterministic governance simulation** — not certification, live monitoring, alerting, or
  production enforcement: typed, immutable `ControlDefinition`, `ControlResult`,
  `RiskIndicator`, `ComplianceSummary`, and `ComplianceAssessment` models with strict enum
  vocabularies for domain, status, severity, entity type, finding code, risk category, and posture
- A fixed, restrained control set covering inventory governance, dataset governance, model
  governance, research governance, access governance, audit completeness, evidence completeness,
  responsible AI readiness, and operational governance; controls are ordinary Python functions,
  not a generic rules DSL
- Deterministic evaluation over the existing Milestone 2 inventory, Milestone 3 access-control
  state, and Milestone 4 audit/evidence state, reusing `evaluate_eligibility`,
  `AccessControlService.is_grant_active`, and `check_completeness` where those rules already
  exist; all findings are returned rather than stopping at the first failure
- Bounded, explainable risk indicators derived only from warning/failed control results:
  `low=1`, `medium=3`, `high=5`, `critical=8`, capped at 100 total. Overall posture is
  `healthy` when all controls pass, `attention_required` when any warning/failure exists or score
  is at least 5, and `high_risk` for any critical failure, at least 3 failures, or score at least
  25
- Loading, export, standalone validation, and reviewer-readable Markdown posture reporting — see
  [Compliance outputs](#compliance-outputs) below
- `scripts/generate_compliance.py` — builds/loads the same deterministic inventory, access,
  audit, and evidence state as prior milestones, evaluates controls, derives risk indicators and
  posture, writes outputs, then reloads and re-validates canonical JSON in one reproducible
  command
- pytest coverage for model validation, deterministic ordering, inventory/dataset/model/research/
  access/audit/evidence controls, simultaneous findings, severity handling, risk-score bounds,
  posture thresholds, evidence references, negative fixtures, deterministic generation,
  canonical JSON round-tripping, and synthetic-data safeguards

This plane evaluates the local synthetic governance state only. It does not assert NHS DSPT,
UK GDPR, MHRA, ISO, or any other regulatory certification; it does not monitor live systems,
enforce access, train models, automate model approval, or replace human responsible-AI review.

### Implemented (Milestone 4 — Audit & Evidence Plane)

- The audit/evidence plane (`src/governance_platform/audit/`), as a **local, deterministic
  governance simulation** — not a production audit trail or live SIEM: a typed, immutable
  `AuditEvent` (`entities.py`) with enums for actor type, entity type, action, event type, and
  outcome (`enums.py`), and structural invariants tying `action`/`entity_type` to `event_type` so
  they can never drift apart; an append-only `AuditLog` (`log.py`) with no update/remove method —
  `append()` always returns a new log — enforcing unique `event_id`s and non-decreasing timestamps
  within each correlated activity
- Pure adapter functions (`adapters.py`) that translate already-produced Milestone 2/3 records into
  audit events without wrapping or modifying `AccessControlService` — the access plane stays
  independently testable — plus a deterministic orchestration layer (`generation.py`) that builds
  the full log from the existing `generate_portfolio()`/`generate_access_control_state()` output
  (no separate synthetic universe) with sequential `AE-0001`, `AE-0002`, ... event IDs and
  correlation IDs derived from `request_id` (`CORR-{request_id}`), so a whole
  request → evaluation → decision → grant → revocation/expiry activity is traceable as one group
- Evidence-completeness checks (`completeness.py`) — every request has an evaluation event, every
  rejected request has rejection evidence, every grant has a creation event, every revoked grant
  has a revocation event, and every referenced ID resolves where a valid reference is actually
  expected — returning human-readable problems rather than raising
- A deterministic, reviewer-readable evidence pack (`evidence.py`, rendered by `markdown.py`):
  inventory/access-control/audit summaries, per-request and per-grant evidence, correlation-group
  traceability, a control-assurance summary, and a factual limitations section — derived entirely
  from references, identifiers, timestamps, decisions, and control outcomes, never full dataset
  records
- Loading, export, and standalone validation (`io.py`, `validation.py`) — see
  [Evidence outputs](#evidence-outputs) below
- `scripts/generate_evidence.py` — loads the inventory, runs the access scenarios, builds the audit
  log, checks completeness, derives and exports the evidence pack, then reloads and re-validates
  the canonical JSON in one reproducible command
- pytest coverage for event validation, immutability, deterministic IDs, duplicate/ordering
  rejection, filtering, correlation, full request→decision→grant event chains, rejected/revoked/
  expired evidence, completeness validation (including invalid references), evidence-pack
  generation, JSON round-tripping, and the synthetic-data safeguards

This is a local simulation over Milestones 2–3's own output — it does not implement a real SIEM,
cloud audit service, Snowflake query-history ingestion, Microsoft Purview or Entra ID audit-log
ingestion, real-time streaming, or an incident-response engine (see
[Explicit non-goals](#explicit-non-goals) below).

### Implemented (Milestone 3 — Access & Research Control Plane)

- The access/research-control plane (`src/governance_platform/access/`), as a **local governance
  simulation** — not live identity or Snowflake RBAC enforcement: typed, immutable
  `AccessRequest`, `ApprovalDecision`, and `AccessGrant` entities (`entities.py`); deterministic
  eligibility evaluation against the Milestone 2 inventory (`policy.py`) implementing the checks
  in [Access outputs](#access-outputs) below; an `AccessControlService`
  (`service.py`) orchestrating request → decision → grant → revocation/expiry, with grant
  activity always computed from an explicitly supplied evaluation instant, never the system clock;
  and an `AccessControlPortfolio` (`portfolio.py`) enforcing the access plane's own referential
  integrity (no duplicate IDs, no grant without an approved decision, no grant exceeding what was
  requested)
- Deterministic synthetic scenario generation (`generation.py`): ten fixed requests run through the
  real service against the Milestone 2 inventory, covering valid approved access; requests against
  pending and expired projects; unlinked, research-use-prohibited, and unapproved datasets/models;
  unknown dataset/model/project references; a duration exceeding project expiry; and, among the
  approved requests, one active, one time-expired, and one explicitly revoked grant
- Loading, export, standalone validation, and an aggregate access-review summary (`io.py`,
  `validation.py`, `summary.py`) — see [Access outputs](#access-outputs) below
- `scripts/generate_access.py` — loads the inventory, generates and evaluates the scenarios,
  exports, reloads, and re-validates the access-control state in one reproducible command
- pytest coverage for entity validation, policy evaluation (every rule below, individually),
  service orchestration, referential integrity, deterministic generation, load/export
  round-tripping, summary calculations, and the synthetic-data safeguards

This is metadata and simulated decisions about access — it does not authenticate anyone, does not
call Snowflake, Entra ID, or any other identity system, and does not provision or enforce real
access to anything (see [Explicit non-goals](#explicit-non-goals) below).

### Implemented (Milestone 2 — Synthetic Research & AI Inventory)

- The metadata/inventory plane (`src/governance_platform/inventory/`): typed, validated dataset,
  AI/ML model, and research project entities (`entities.py`), enums for sensitivity, lifecycle,
  approval, risk tier, etc. (`enums.py`), and an `InventoryPortfolio` (`portfolio.py`) that
  enforces cross-entity referential integrity — duplicate IDs and dangling dataset/model
  references fail with a clear, human-readable error
- Deterministic synthetic inventory generation (`generation.py`): a fixed, restrained portfolio of
  6 datasets, 5 models, and 4 research projects covering multiple sensitivity classifications,
  approved/pending/deprecated datasets, low/medium/high-risk models, and
  approved/pending/expired research projects — identical on every run, on every machine
- Loading, export, standalone validation, and an aggregate governance summary (`io.py`,
  `validation.py`, `summary.py`) — see [Inventory outputs](#inventory-outputs) below
- `scripts/generate_inventory.py` — generates, exports, reloads, and re-validates the inventory in
  one reproducible command (documented under [Getting started](#getting-started-local-development))
- pytest coverage for entity validation, referential integrity, deterministic generation,
  load/export round-tripping, summary calculations, and the synthetic-data safeguard

This plane is metadata about datasets, models, and research projects — it does not implement model
training, deployment, inference, or monitoring, research workspace provisioning, approval-workflow
automation, or any Snowflake connectivity (see [Explicit non-goals](#explicit-non-goals) below).

### Implemented (Milestone 1 — Platform Foundation)

- Repository structure and conventions listed above
- Python package skeleton (`governance_platform`) with a config loader and logging setup utility
  — foundation code only, no governance logic
- Architecture documentation (`reports/architecture.md`) covering all seven governance planes,
  including a Mermaid diagram
- Architecture Decision Records for the foundational design choices (synthetic data only,
  modular architecture, Snowflake as a future platform, Fabric/Power BI as a future reporting
  layer, policy-as-code / evidence-as-code principles)
- Lightweight governance operating-model documentation (dataset governance, model governance,
  research approval, access review, audit/evidence, responsible AI, compliance monitoring) —
  documentation of intended process, not working systems
- Minimal development Docker image and Compose file for a reproducible local dev/test shell
- Restrained Terraform scaffold (variables/outputs only, no providers, no resources, no state
  backend, nothing deployable)
- Documentation of intended Snowflake governance responsibilities (RBAC, tagging, masking, audit
  logging) with no account, connection, or credentials
- Documentation of intended Fabric/Power BI reporting architecture, with no semantic model or
  dashboard files
- pytest-based foundation tests validating package importability, config loading, and repository
  structure
- GitHub Actions CI: Python setup, dependency install, lint/format checks, tests, repository
  validation

### Planned (later milestones — **not implemented in this repository yet**)

- Live Snowflake schema, roles, tags, and masking policies against a real (still non-production,
  sandbox-style) account backing the inventory and access grants (see ADR
  [0003](docs/architecture/decisions/0003-snowflake-as-future-governed-platform.md)) — this
  milestone's inventory and access state are local JSON/CSV, not a Snowflake integration
- Live Snowflake RBAC / role-grant enforcement, and Snowflake user/role provisioning
- Entra ID (or any other) identity integration, authentication, and real user accounts
- Periodic access recertification (the "reconfirm continued need, or revoke" cadence described in
  [`governance/access_review.md`](governance/access_review.md))
- Research workspace provisioning
- Live Snowflake audit-log/query-history ingestion, a real SIEM, Microsoft Purview integration, or
  Entra ID audit-log ingestion feeding the audit plane — Milestone 4's audit log is local and
  self-contained, not fed by any of these
- Real-time event streaming or production observability of any kind
- An incident-response engine
- A model approval / responsible-AI review workflow with automated checks
- Deployed Fabric semantic model and live semantic-model refresh
- Published Power BI governance dashboards or `.pbix`/PBIP artifacts
- Authentication, role-based application access, and production hosting for the local reviewer
  portal
- Any live Terraform deployment or cloud provisioning

Do not treat anything in this list as available — it is documented here precisely so it isn't
assumed to exist.

### Explicit non-goals

Milestones 2–7 are metadata, inventory, local access-control, audit/evidence, compliance,
reporting, and reviewer-portal **simulations** only. They do not implement: Snowflake connectivity or deployed schemas, live
Snowflake RBAC or user/role provisioning, Entra ID integration, authentication, real user accounts,
cloud identity, live Snowflake query-history/audit-log ingestion, a real SIEM, Microsoft Purview
integration, Entra ID audit-log ingestion, real-time streaming, production observability, an
incident-response engine, a generic policy-as-code engine, approval-workflow automation,
responsible-AI workflow automation, model approval automation, Fabric semantic models, Power BI
dashboards, Terraform deployment, Salesforce workflows, regulatory certification, live monitoring,
alerting, production hosting, or production access/audit/compliance enforcement of any kind. These
remain [Planned](#planned-later-milestones--not-implemented-in-this-repository-yet) above.

## Getting started (local development)

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest
ruff check .
ruff format --check .
python scripts/validate_repository.py

# Generate, export, and validate the synthetic governance inventory (Milestone 2):
python scripts/generate_inventory.py

# Generate, evaluate, export, and validate the synthetic access-control state (Milestone 3):
python scripts/generate_access.py

# Build the audit log, check completeness, and generate the evidence pack (Milestone 4):
python scripts/generate_evidence.py

# Evaluate controls, derive bounded risk indicators, and generate posture outputs (Milestone 5):
python scripts/generate_compliance.py

# Build reporting KPIs, snapshot, and executive summary (Milestone 6):
python scripts/generate_reporting.py

# Start the local reviewer portal (Milestone 7):
streamlit run src/governance_platform/reviewer_app.py
```

### Using Docker instead

```bash
docker compose -f infrastructure/docker/docker-compose.yml run --rm dev
```

This drops you into the same dependency set inside a container. See
[`infrastructure/docker/README.md`](infrastructure/docker/README.md) — it is a development
convenience, not a deployment artifact.

## Inventory outputs

`python scripts/generate_inventory.py` writes the following to `outputs/inventory/` (gitignored —
reproducible from `src/governance_platform/inventory/`, not stored as static artifacts, per ADR
[0005](docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)):

```text
outputs/inventory/inventory_portfolio.json   # canonical, lossless JSON (datasets + models + projects)
outputs/inventory/datasets.csv
outputs/inventory/models.csv
outputs/inventory/research_projects.csv
outputs/inventory/inventory_summary.json     # aggregate counts by status, classification, risk tier
```

### Entities and relationships

- **Dataset** (`dataset_id`, e.g. `DS-0001`) — owner, steward, sensitivity classification, data
  category, source type, lifecycle/approval status, retention class, and a
  `contains_synthetic_data_only` flag that entity-level validation requires to be `true` for every
  dataset (ADR [0001](docs/architecture/decisions/0001-synthetic-data-only.md)).
- **AIModel** (`model_id`, e.g. `MD-0001`) — owner, model type, intended use, risk tier,
  responsible-AI review status, and `linked_dataset_ids` referencing the dataset(s) it was
  trained/evaluated on. A model at `risk_tier=high` cannot be `approval_status=approved` without
  `responsible_ai_review_status=approved`, and must have `monitoring_required=true` — encoding the
  rule described in `governance/model_governance.md`.
- **ResearchProject** (`research_project_id`, e.g. `RP-0001`) — principal owner, purpose,
  `linked_dataset_ids` and `linked_model_ids`, approval status, risk classification, and
  start/expiry dates (`expiry_date` must be after `start_date`).
- `InventoryPortfolio` (`src/governance_platform/inventory/portfolio.py`) validates the whole set
  together: no duplicate IDs across any entity type, and every `linked_dataset_ids`/
  `linked_model_ids` reference must resolve to a dataset/model that actually exists — a dangling
  or duplicate reference fails construction with a specific error identifying the offending ID.

### Generation and validation process

`generation.py` returns a **fixed, hand-authored** portfolio (six datasets, five models, four
research projects) rather than randomly sampled data — deterministic by construction, so
`generate_portfolio()` returns byte-identical data on every call, process, and machine. It
deliberately covers, without padding the count further: an operational, a population-health, a
synthetic clinical-text, and a research-feature dataset; approved, pending, and deprecated
datasets; low/medium/high-risk models; and approved, pending, and expired research projects. Every
identity (`owner`, `steward`, `principal_owner`) is a fictional role title (e.g. "Population Health
Data Owner"), never a real person's name.

Validation happens in two layers: pydantic raises immediately on construction (`Dataset(...)`,
`InventoryPortfolio(...)`), while `governance_platform.inventory.validation.validate_portfolio_data`
/ `validate_portfolio_file` return a list of human-readable problems instead of raising, for
CLI-style reporting against hand-edited or externally-produced inventory data.

### Limitations

This is metadata about datasets, models, and research projects — not the datasets, models, or
research workspaces themselves. No model training, deployment, inference, or monitoring; no
research workspace provisioning; no approval-workflow automation. As of Milestone 3, the access
plane reads this inventory for eligibility evaluation, and as of Milestone 4, the audit/evidence
plane reads both for evidence generation. As of Milestone 5, the compliance plane reads the
inventory, access-control state, audit log, and evidence pack to evaluate deterministic controls
and derive bounded risk indicators. `inventory_summary.json` itself remains counts and breakdowns
only.

## Access outputs

`python scripts/generate_access.py` writes the following to `outputs/access/` (gitignored —
reproducible from `src/governance_platform/access/`, not stored as static artifacts, per ADR
[0005](docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)):

```text
outputs/access/access_control_state.json     # canonical, lossless JSON (requests + decisions + grants)
outputs/access/access_requests.csv
outputs/access/approval_decisions.csv
outputs/access/access_grants.csv
outputs/access/access_review_summary.json    # aggregate counts by status, grant activity, rejection reason
```

### Lifecycle: request -> decision -> grant -> revocation/expiry

`governance_platform.access.AccessControlService`, given a Milestone 2 `InventoryPortfolio`
snapshot, orchestrates four immutable steps — each one a new record, never an edit to a previous
one (consistent with `governance/audit_evidence.md`'s append-only principle):

1. **`submit_request(...)`** creates an `AccessRequest` (`request_id`, e.g. `AR-0001`) with
   `status=submitted`. No eligibility check happens yet.
2. **`decide(request, ...)`** evaluates the request via `evaluate_eligibility` (below), records an
   `ApprovalDecision` (`decision_id`, e.g. `AD-0001`) with `decision=approved`/`rejected` and a
   `decision_reason` built from every violation found, and returns a new `AccessRequest` with
   `status` finalized to match — the original request object is left untouched (it is frozen).
3. **`create_grant(request, decision, ...)`** creates a time-bounded `AccessGrant` (`grant_id`, e.g.
   `AG-0001`) only from an approved decision — it raises `ValueError` for a rejected or
   mismatched decision.
4. **`revoke_grant(grant, ...)`** returns a new, revoked copy of a grant with `revoked_at` and
   `revocation_reason` set. **`is_grant_active(grant, at)`** and **`expired_grants(grants, at)`**
   determine activity purely from the explicitly supplied instant `at` against
   `granted_at`/`expires_at`/`status` — never the system clock, so evaluation is reproducible
   regardless of when it runs.

### Policy checks implemented

`governance_platform.access.policy.evaluate_eligibility(request, inventory)` is a pure function
that checks, and reports *every* applicable violation for (not just the first):

1. the referenced `ResearchProject` exists in the inventory
2. it is `approval_status=approved`
3. it is not `approval_status=expired`
4. every requested dataset exists in the inventory
5. every requested model exists in the inventory
6. every requested dataset/model is already in the project's `linked_dataset_ids`/`linked_model_ids`
7. every requested dataset has `research_use_allowed=true`
8. every requested dataset and model is itself `approval_status=approved`
9. `requested_until` does not fall after the project's `expiry_date`

A request can fail for more than one reason at once — `EligibilityResult.violations` carries a
structured `RejectionReasonCode` and a human-readable detail per violation, so every rejection is
explainable. `AccessGrant` itself enforces rule 10 (time-bounded: `expires_at` must be after
`granted_at`) and consistent revocation fields as entity-level invariants, and
`AccessControlPortfolio` enforces rule 11 (no grant without an approved decision) as a
cross-entity invariant — both fail construction rather than relying on caller discipline.

### Generation and validation process

`generation.py` runs ten fixed requests through the real `AccessControlService` against the
Milestone 2 synthetic inventory — deterministic by construction, so
`generate_access_control_state()` returns byte-identical data on every call. It covers: valid
approved access; a pending project; an expired project; a dataset not linked to its project; a
dataset whose research use is prohibited; a duration exceeding project expiry; unknown
dataset/model references; an unknown research project; and, among the three approved requests, one
grant left active, one left to expire by the fixed reference evaluation time
(`REFERENCE_EVALUATION_TIME`, 2025-03-15 — a synthetic reference point, not "now"), and one
explicitly revoked. Every `requester_id`/`approver_id` is a fictional, role-based access-plane
identifier (e.g. `"researcher-population-health-01"`), never a real person's name.

Validation happens in two layers, mirroring the inventory plane: pydantic raises immediately on
construction (`AccessRequest(...)`, `AccessControlPortfolio(...)`), while
`governance_platform.access.validation.validate_access_state_data`/`validate_access_state_file`
return a list of human-readable problems instead of raising, for CLI-style reporting. That
validation covers the access plane's own referential integrity only (duplicate IDs, dangling
request references, grants without an approved decision) — it does not re-run inventory
eligibility policy, which is a property of a request/inventory pair, not of a state file alone.

### Synthetic/local nature and limitations

This is a **local governance simulation**: typed records and deterministic policy evaluation run
in-process against an in-memory inventory snapshot. It does not authenticate anyone, does not call
Snowflake, Entra ID, or any other identity system, does not provision or enforce real access to
anything. As of Milestone 4, this plane's activity is recorded by the audit/evidence plane below,
and as of Milestone 5 it is evaluated by the compliance plane for evidence-backed controls — see
[Evidence outputs](#evidence-outputs). Periodic access recertification (`governance/access_review.md`'s
"reconfirm continued need, or revoke" cadence) is also not implemented — a grant's activity is
always recomputed from its fixed window, not
re-reviewed on a cadence.

## Evidence outputs

`python scripts/generate_evidence.py` writes the following to `outputs/evidence/` (gitignored —
reproducible from `src/governance_platform/audit/`, not stored as static artifacts, per ADR
[0005](docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)):

```text
outputs/evidence/audit_events.json    # canonical, lossless JSON — the full AuditLog
outputs/evidence/audit_events.csv
outputs/evidence/audit_summary.json   # aggregate counts by type, outcome, entity type, project
outputs/evidence/evidence_pack.json   # canonical, lossless JSON — the full EvidencePack
outputs/evidence/evidence_pack.md     # reviewer-readable Markdown rendering of the same pack
```

### Append-only audit model

`AuditEvent` (`src/governance_platform/audit/entities.py`) is frozen and `extra="forbid"`, exactly
like the inventory and access entities. `AuditLog` (`log.py`) holds a tuple of events and exposes
no update/remove method on its public API — `append(event)` returns a **new** `AuditLog` rather
than mutating the one it was called on, and re-validates the full resulting sequence: duplicate
`event_id`s are rejected, and within each correlation group (below), a newly appended event's
`occurred_at` may not be earlier than the previous event recorded in that group. This mirrors
`governance/audit_evidence.md`'s "audit events are append-only; corrections are recorded as new
events, not edits to history."

### Event taxonomy

A restrained set of nine `AuditEventType` values covers exactly the actions the inventory and
access planes actually perform — nothing speculative:

`inventory_created`, `inventory_validated`, `access_requested`, `access_evaluated`,
`access_approved`, `access_rejected`, `grant_created`, `grant_revoked`, `grant_expired`.

Each event type is tied by construction to exactly one `entity_type` (`inventory` /
`access_request` / `access_grant`) and one normalized `action` verb (e.g. both
`inventory_created` and `grant_created` carry `action=create`) — `AuditEvent` rejects a mismatch at
construction time rather than relying on caller discipline. `outcome` (`success` / `denied` /
`revoked` / `expired`) records the governance-relevant result; `reason` carries the decision/
revocation reason for a denial or revocation. `metadata` is a small `dict[str, str]` for
non-sensitive context (e.g. a dataset/model count); entity-level validation rejects any metadata
entry that looks like it might contain a secret or patient-level marker (`ssn`, `password`,
`token`, `mrn`, `patient`, etc.) as a structural, not just conventional, safeguard.

### Correlation approach

Every event carries a `correlation_id` so a whole governance activity — request → evaluation →
approval/rejection → grant creation → revocation/expiry — is discoverable as one group via
`AuditLog.filter_by_correlation_id`/`correlation_groups`. Correlation IDs are **derived, not
randomly generated**: `governance_platform.audit.adapters.request_correlation_id(request_id)`
returns `f"CORR-{request_id}"` (e.g. `CORR-AR-0001`), so every event tied to that request —
including any grant created from it — shares the same id by construction. The two inventory-plane
events share a fixed `CORR-INVENTORY-0001`.

### Evidence-pack composition

`EvidencePack` (`evidence.py`) is a pure function of the inventory, access-control state, audit
log, and explicitly supplied `generated_at`/`evaluated_at` timestamps — never the system clock. It
does not copy full dataset/model/project records; it carries counts, breakdowns, identifiers,
timestamps, decisions, and control outcomes: inventory evidence (counts + status breakdowns),
access-request evidence, approval-decision evidence, grant evidence (status as of the evaluation
instant), rejected-access evidence, correlation-group evidence (the event-type chain and final
outcome per activity), a completeness result, and a fixed `limitations` section. `markdown.py`
renders the same pack as reviewer-readable Markdown with no new computation — evidence-pack ID,
generation timestamp, scope, source systems, inventory/access-control summaries, key audit events
(grouped by correlation), rejected-access evidence, active/expired/revoked grant evidence, a
control-assurance summary, and limitations, in that order.

### Evidence-completeness validation

`governance_platform.audit.completeness.check_completeness(audit_log, inventory, access_state)` is
**evidence completeness validation, not a generic policy engine** — it asks "is evidence we'd
expect to exist actually present?", not "was the governed activity correct?" (that's
`governance_platform.access.policy`'s job). It checks: every access request has an
`access_evaluated` event; every rejected request has an `access_rejected` event; every grant has a
`grant_created` event; every revoked grant has a `grant_revoked` event; every emitted `event_id` is
unique; and every `request_id`/`decision_id`/`grant_id` reference resolves. A
`research_project_id` is only required to resolve on events that could only exist once a project
was already validated (`access_approved`, `grant_created`, `grant_revoked`, `grant_expired`) — a
request rejected specifically because it named an unknown project still carries that (unresolved)
project id on its `access_requested`/`access_evaluated`/`access_rejected` events, which is the
audit trail correctly preserving what was claimed, not a completeness gap.

### Synthetic/local nature and relationship to the inventory and access planes

This is a **local, deterministic governance simulation** layered over Milestones 2–3's own output
— `generate_audit_log` takes the exact `InventoryPortfolio`/`AccessControlPortfolio` those
milestones' generators produce (or any equivalent reloaded state) and translates it into events via
pure adapter functions; it does not create a separate synthetic universe, and it does not wrap or
modify `AccessControlService`, so the access plane remains independently testable. It does not
implement a real SIEM, cloud audit service, Snowflake query-history ingestion, Microsoft Purview or
Entra ID audit-log ingestion, real-time streaming, or an incident-response engine (those remain
[Planned](#planned-later-milestones--not-implemented-in-this-repository-yet)). Nothing here claims
regulatory certification or production audit-trail status — see the evidence pack's own
`limitations` section.

## Compliance outputs

`python scripts/generate_compliance.py` writes the following to `outputs/compliance/`
(gitignored — reproducible from `src/governance_platform/compliance/`, not stored as static
artifacts, per ADR [0005](docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)):

```text
outputs/compliance/control_results.json      # canonical control-result list
outputs/compliance/control_results.csv
outputs/compliance/risk_indicators.json      # bounded risk indicators from non-passing results
outputs/compliance/compliance_summary.json   # canonical, lossless ComplianceAssessment
outputs/compliance/governance_posture.md     # reviewer-readable posture report
```

The control flow is deterministic:

```text
Governance State -> Control Evaluation -> Compliance Findings -> Risk Indicators
-> Governance Posture
```

Controls cover inventory identifiers and references, the synthetic-data-only invariant,
ownership/stewardship and review metadata, granted dataset/model approval and lifecycle state,
research project approval/expiry/scope for active grants, grant decision evidence, rejected
request handling, grant time bounds, audit completeness, lifecycle events, correlation chains,
duplicate audit IDs, evidence-reference resolution, and high-risk model readiness.

Risk scoring is bounded and transparent: warning/failed findings become indicators scored by
severity (`low=1`, `medium=3`, `high=5`, `critical=8`) with a total cap of 100. Posture is
`healthy` when all controls pass, `attention_required` when any warning/failure exists or score is
at least 5, and `high_risk` for any critical failure, at least 3 failures, or score at least 25.
The generated canonical portfolio currently produces one responsible-AI readiness warning for the
pending high-risk LLM (`MD-0003`) and no failures. This is not predictive modelling, regulatory
certification, live monitoring, alerting, or production policy enforcement.

## Reporting outputs

`python scripts/generate_reporting.py` writes the following to `outputs/reporting/`
(gitignored — reproducible from `src/governance_platform/reporting/`, not stored as static
artifacts, per ADR [0005](docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)):

```text
outputs/reporting/governance_kpis.json      # canonical reporting KPI rows
outputs/reporting/governance_kpis.csv
outputs/reporting/reporting_snapshot.json   # canonical, lossless ReportingSnapshot
outputs/reporting/executive_summary.md      # concise reviewer/executive summary
```

The reporting flow is deterministic:

```text
Inventory + Access + Audit + Evidence + Compliance
        -> Reporting Semantic Layer
        -> Governance Metrics
        -> Reviewer / Executive Views
```

Metrics include inventory counts and breakdowns, dataset/model/research governance posture,
access-request approval and rejection metrics, grant lifecycle status, rejection reasons, audit
event counts and completeness, evidence completeness, compliance pass/warning/failure metrics,
findings by domain/severity, risk indicator counts, bounded risk score, and overall governance
posture. Every KPI has source references back to the local source artifact(s). This is not a
deployed Fabric semantic model, Power BI report, live refresh, or tenant integration.

## Local reviewer portal

`streamlit run src/governance_platform/reviewer_app.py` starts a local read-only reviewer portal
over the generated outputs. Generate the deterministic state first with the five scripts above.

The portal reads canonical files rather than rebuilding governance logic:

```text
Governance Source State -> Existing Reporting Snapshot -> Reviewer Portal
-> Navigation / Filtering / Drill-through -> Governance Review Experience
```

Implemented sections:

- **Executive Governance Overview** — posture, bounded risk score, control pass/warning/failure
  metrics, inventory totals, access totals, grant status, and audit/evidence completeness.
- **Data & Model Governance** — dataset and model inventory review with filters for approval,
  sensitivity, research-use eligibility, risk tier, and model approval state.
- **Research & Access Governance** — research projects, access requests, decisions, grants,
  rejection reasons, and drill-through by project/request/grant.
- **Audit & Evidence** — audit-event timeline with filters for event type, outcome, project,
  request, and grant, plus evidence-pack completeness summary.
- **Compliance & Risk** — controls, pass rate, findings by severity/domain, risk indicators,
  bounded risk score, posture, and evidence-reference drill-through.

The app fails clearly when required generated outputs are missing and tells the reviewer which
generation commands to run. It has no write/edit workflows, approval actions, authentication,
role-based app access, production hosting, Power BI/Fabric deployment, live refresh, alerting, or
regulatory certification.

## Architecture and design records

- [`reports/architecture.md`](reports/architecture.md) — the seven-plane architecture and diagram
- [`docs/architecture/decisions/`](docs/architecture/decisions/) — ADRs behind the foundational
  choices
- [`src/governance_platform/inventory/`](src/governance_platform/inventory/) — the Milestone 2
  metadata/inventory plane implementation
- [`src/governance_platform/access/`](src/governance_platform/access/) — the Milestone 3
  access/research-control plane implementation
- [`src/governance_platform/audit/`](src/governance_platform/audit/) — the Milestone 4
  audit/evidence plane implementation
- [`src/governance_platform/compliance/`](src/governance_platform/compliance/) — the Milestone 5
  risk/compliance monitoring plane implementation
- [`src/governance_platform/reporting/`](src/governance_platform/reporting/) — the Milestone 6
  reporting and semantic snapshot implementation
- [`src/governance_platform/reviewer/`](src/governance_platform/reviewer/) and
  [`src/governance_platform/reviewer_app.py`](src/governance_platform/reviewer_app.py) — the
  Milestone 7 local reviewer portal
- [`governance/`](governance/) — operating-model documentation per governance domain
- [`infrastructure/snowflake/`](infrastructure/snowflake/) — intended Snowflake governance
  responsibilities (no live account)
- [`fabric/`](fabric/) — future Fabric/Power BI semantic-model and dashboard specifications

## Non-affiliation and data statement

This is an independent portfolio project. It is not affiliated with, endorsed by, or built
against any real healthcare organisation, Snowflake account, Microsoft Fabric tenant, or Power BI
workspace. All data referenced anywhere in this repository is, and will remain, synthetic. No
real patient data (PHI/PII) is or will be used.
