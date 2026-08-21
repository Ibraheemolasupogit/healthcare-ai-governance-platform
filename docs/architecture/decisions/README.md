# Architecture Decision Records

This directory records the significant architectural decisions behind the platform, using the
lightweight ADR format (Context / Decision / Consequences). ADRs are immutable once accepted — a
changed decision gets a new ADR that supersedes the old one, rather than an edit in place.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-synthetic-data-only.md) | Synthetic data only | Accepted |
| [0002](0002-modular-governance-architecture.md) | Modular governance architecture (seven planes) | Accepted |
| [0003](0003-snowflake-as-future-governed-platform.md) | Snowflake as future governed data/metadata platform | Accepted |
| [0004](0004-fabric-powerbi-as-future-reporting-layer.md) | Fabric / Power BI as future reporting layer | Accepted |
| [0005](0005-policy-as-code-and-evidence-as-code.md) | Policy-as-code and evidence-as-code principles | Accepted |

## Format

Each ADR follows:

- **Status** — Proposed / Accepted / Superseded
- **Context** — the forces at play, including any constraint that makes this a decision worth
  recording
- **Decision** — what was decided
- **Consequences** — what this makes easier, what it makes harder, and what it explicitly rules
  out
