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
(Platform Foundation), Milestone 2 (Synthetic Research & AI Inventory), and Milestone 3 (Access &
Research Control Plane).** Milestone 2 adds a typed, validated metadata/inventory plane and a
deterministic synthetic dataset/model/research portfolio generated from it. Milestone 3 adds a
**local governance simulation** of the access request → decision → grant → revocation/expiry
workflow, evaluated deterministically against that inventory. No audit simulation, risk scoring,
model approval automation, responsible AI automation, evidence generation, or live identity/RBAC
enforcement has been implemented yet. See [Implemented vs. Planned](#implemented-vs-planned) below
before assuming any capability exists.

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
│   └── access/                 # Access/research-control plane: request/decision/grant simulation
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
│   └── access/                 # Generated access requests/decisions/grants (gitignored)
├── reports/
│   └── architecture.md         # Full architecture write-up + diagram
├── docs/
│   └── architecture/decisions/ # Architecture Decision Records (ADRs)
├── scripts/
│   ├── generate_inventory.py   # Generate/validate/export the synthetic inventory
│   └── generate_access.py      # Generate/evaluate/validate/export the access-control state
├── tests/                      # Foundation + inventory + access tests
└── .github/workflows/          # CI: install, lint, test, validate
```

## Implemented vs. Planned

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
- An audit-event simulator and evidence trail generator
- A risk-scoring and compliance-monitoring engine, including any calculated enterprise risk score
- A model approval / responsible-AI review workflow with automated checks
- Automated evidence-pack generation for audits
- A built Fabric semantic model
- Published Power BI governance dashboards
- Any live Terraform deployment or cloud provisioning

Do not treat anything in this list as available — it is documented here precisely so it isn't
assumed to exist.

### Explicit non-goals

Milestones 2 and 3 are metadata, inventory, and a local access-control **simulation** only. They do
not implement: Snowflake connectivity or deployed schemas, live Snowflake RBAC or user/role
provisioning, Entra ID integration, authentication, real user accounts, cloud identity, audit-event
simulation, a risk-scoring engine, policy-as-code execution, approval-workflow automation,
responsible-AI automation, evidence-pack generation, Fabric semantic models, Power BI dashboards,
Terraform deployment, Salesforce workflows, or production access enforcement of any kind. These
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
plane below reads this inventory for eligibility evaluation; no audit or risk-scoring logic reads
it yet (those remain [Planned](#planned-later-milestones--not-implemented-in-this-repository-yet)).
No calculated enterprise risk score is produced — `inventory_summary.json` is counts and
breakdowns only.

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
anything, and does not simulate audit events or compute a risk score (those remain
[Planned](#planned-later-milestones--not-implemented-in-this-repository-yet)). Periodic access
recertification (`governance/access_review.md`'s "reconfirm continued need, or revoke" cadence) is
also not implemented — a grant's activity is always recomputed from its fixed window, not
re-reviewed on a cadence.

## Architecture and design records

- [`reports/architecture.md`](reports/architecture.md) — the seven-plane architecture and diagram
- [`docs/architecture/decisions/`](docs/architecture/decisions/) — ADRs behind the foundational
  choices
- [`src/governance_platform/inventory/`](src/governance_platform/inventory/) — the Milestone 2
  metadata/inventory plane implementation
- [`src/governance_platform/access/`](src/governance_platform/access/) — the Milestone 3
  access/research-control plane implementation
- [`governance/`](governance/) — operating-model documentation per governance domain
- [`infrastructure/snowflake/`](infrastructure/snowflake/) — intended Snowflake governance
  responsibilities (no live account)
- [`fabric/`](fabric/) — intended Fabric/Power BI reporting architecture (nothing built yet)

## Non-affiliation and data statement

This is an independent portfolio project. It is not affiliated with, endorsed by, or built
against any real healthcare organisation, Snowflake account, Microsoft Fabric tenant, or Power BI
workspace. All data referenced anywhere in this repository is, and will remain, synthetic. No
real patient data (PHI/PII) is or will be used.
