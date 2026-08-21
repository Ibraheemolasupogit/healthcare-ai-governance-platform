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
(Platform Foundation) only.** No governance logic — access review, audit simulation, risk
scoring, model approval, responsible AI automation, or evidence generation — has been implemented
yet. See [Implemented vs. Planned](#implemented-vs-planned) below before assuming any capability
exists.

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
├── data/                       # Synthetic data only (empty in Milestone 1)
├── src/governance_platform/    # Python package: foundation utilities only
├── governance/                 # Governance operating-model documentation
├── infrastructure/
│   ├── docker/                 # Minimal local development container
│   ├── terraform/              # Restrained IaC foundation (no live infra)
│   └── snowflake/              # Documented intent, no live account/credentials
├── fabric/
│   ├── semantic_model/         # Documented intent, no semantic model built yet
│   └── dashboards/             # Documented intent, no PBIX/dashboards built yet
├── config/                     # Non-secret configuration scaffolding
├── outputs/                    # Local, gitignored generated artifacts
├── reports/
│   └── architecture.md         # Full architecture write-up + diagram
├── docs/
│   └── architecture/decisions/ # Architecture Decision Records (ADRs)
├── tests/                      # Foundation tests (structure, package, config)
└── .github/workflows/          # CI: install, lint, test, validate
```

## Implemented vs. Planned

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

- Synthetic research inventory datasets (datasets, models, researchers, projects)
- Live Snowflake schema, roles, tags, and masking policies against a real (still non-production,
  sandbox-style) account
- An access-review engine (request → approval → periodic recertification)
- An audit-event simulator and evidence trail generator
- A risk-scoring and compliance-monitoring engine
- A model approval / responsible-AI review workflow with automated checks
- Automated evidence-pack generation for audits
- A built Fabric semantic model
- Published Power BI governance dashboards
- Any live Terraform deployment or cloud provisioning

Do not treat anything in this list as available — it is documented here precisely so it isn't
assumed to exist.

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
```

### Using Docker instead

```bash
docker compose -f infrastructure/docker/docker-compose.yml run --rm dev
```

This drops you into the same dependency set inside a container. See
[`infrastructure/docker/README.md`](infrastructure/docker/README.md) — it is a development
convenience, not a deployment artifact.

## Architecture and design records

- [`reports/architecture.md`](reports/architecture.md) — the seven-plane architecture and diagram
- [`docs/architecture/decisions/`](docs/architecture/decisions/) — ADRs behind the foundational
  choices
- [`governance/`](governance/) — operating-model documentation per governance domain
- [`infrastructure/snowflake/`](infrastructure/snowflake/) — intended Snowflake governance
  responsibilities (no live account)
- [`fabric/`](fabric/) — intended Fabric/Power BI reporting architecture (nothing built yet)

## Non-affiliation and data statement

This is an independent portfolio project. It is not affiliated with, endorsed by, or built
against any real healthcare organisation, Snowflake account, Microsoft Fabric tenant, or Power BI
workspace. All data referenced anywhere in this repository is, and will remain, synthetic. No
real patient data (PHI/PII) is or will be used.
