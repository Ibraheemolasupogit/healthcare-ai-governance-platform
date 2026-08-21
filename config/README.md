# Configuration

Non-secret, environment-agnostic configuration for the platform's Python package. **No secrets or
credentials belong in this directory or anywhere in this repository** — see the root
[`.gitignore`](../.gitignore) for the patterns kept out of version control (`.env`, `*.key`,
`*.pem`, `*.tfvars`).

## Current contents

- [`settings.example.yaml`](settings.example.yaml) — illustrates the shape
  `governance_platform.config.load_settings` (see
  [`src/governance_platform/config/`](../src/governance_platform/config/)) expects to read: a flat
  set of non-secret key/value settings. Nothing in the platform consumes these values for
  governance decisions yet — Milestone 1 only implements the loader itself.

## Intended future use

As governance planes are implemented, module-specific configuration (e.g. access recertification
cadence, risk-scoring thresholds) is expected to live here as versioned, reviewable YAML, per the
policy-as-code principle (ADR
[0005](../docs/architecture/decisions/0005-policy-as-code-and-evidence-as-code.md)) — not as
hard-coded constants in application code.
