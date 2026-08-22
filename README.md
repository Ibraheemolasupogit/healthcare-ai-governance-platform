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
(Platform Foundation) and Milestone 2 (Synthetic Research & AI Inventory).** Milestone 2 adds a
typed, validated metadata/inventory plane and a deterministic synthetic dataset/model/research
portfolio generated from it. No access review, audit simulation, risk scoring, model approval
automation, responsible AI automation, or evidence generation has been implemented yet. See
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
│   └── inventory/              # Metadata/inventory plane: entities, generation, validation, I/O
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
│   └── inventory/              # Generated inventory CSV/JSON (gitignored, reproducible)
├── reports/
│   └── architecture.md         # Full architecture write-up + diagram
├── docs/
│   └── architecture/decisions/ # Architecture Decision Records (ADRs)
├── scripts/
│   └── generate_inventory.py   # Generate/validate/export the synthetic inventory
├── tests/                      # Foundation + inventory tests
└── .github/workflows/          # CI: install, lint, test, validate
```

## Implemented vs. Planned

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
automation, or any Snowflake connectivity (see [Explicit non-goals](#explicit-non-goals-of-milestone-2)
below).

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
  sandbox-style) account backing the inventory (see ADR
  [0003](docs/architecture/decisions/0003-snowflake-as-future-governed-platform.md)) — this
  milestone's inventory is local JSON/CSV, not a Snowflake integration
- An access-review engine (request → approval → periodic recertification)
- An audit-event simulator and evidence trail generator
- A risk-scoring and compliance-monitoring engine, including any calculated enterprise risk score
- A model approval / responsible-AI review workflow with automated checks
- Research workspace provisioning
- Automated evidence-pack generation for audits
- A built Fabric semantic model
- Published Power BI governance dashboards
- Any live Terraform deployment or cloud provisioning

Do not treat anything in this list as available — it is documented here precisely so it isn't
assumed to exist.

### Explicit non-goals of Milestone 2

Milestone 2 is metadata and inventory only. It does not implement: Snowflake connectivity or
deployed schemas, an access-review engine, RBAC enforcement or access provisioning, audit-event
simulation, a risk-scoring engine, policy-as-code execution, approval-workflow automation,
responsible-AI automation, evidence-pack generation, Fabric semantic models, Power BI dashboards,
or any cloud/infrastructure deployment. These remain [Planned](#planned-later-milestones--not-implemented-in-this-repository-yet)
above.

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
research workspace provisioning; no approval-workflow automation; no access, audit, or risk-scoring
logic reads this inventory yet (those remain [Planned](#planned-later-milestones--not-implemented-in-this-repository-yet)).
No calculated enterprise risk score is produced — `inventory_summary.json` is counts and
breakdowns only.

## Architecture and design records

- [`reports/architecture.md`](reports/architecture.md) — the seven-plane architecture and diagram
- [`docs/architecture/decisions/`](docs/architecture/decisions/) — ADRs behind the foundational
  choices
- [`src/governance_platform/inventory/`](src/governance_platform/inventory/) — the Milestone 2
  metadata/inventory plane implementation
- [`governance/`](governance/) — operating-model documentation per governance domain
- [`infrastructure/snowflake/`](infrastructure/snowflake/) — intended Snowflake governance
  responsibilities (no live account)
- [`fabric/`](fabric/) — intended Fabric/Power BI reporting architecture (nothing built yet)

## Non-affiliation and data statement

This is an independent portfolio project. It is not affiliated with, endorsed by, or built
against any real healthcare organisation, Snowflake account, Microsoft Fabric tenant, or Power BI
workspace. All data referenced anywhere in this repository is, and will remain, synthetic. No
real patient data (PHI/PII) is or will be used.
