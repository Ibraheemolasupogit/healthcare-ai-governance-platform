# Data

**Synthetic data only** — see ADR
[0001](../docs/architecture/decisions/0001-synthetic-data-only.md). No real patient, clinician, or
institutional data will ever be placed in this directory.

## Current status

Empty in Milestone 1. Generating a synthetic research inventory (datasets, models, researchers,
projects) is explicitly out of scope for this milestone — see the Milestone 1 non-goals in the
root [`README.md`](../README.md). `data/synthetic/` is scaffolded as the intended location for
that future synthetic data.

## Intended future contents

- `data/synthetic/` — generated synthetic inventory, access, and audit data used to exercise the
  governance planes once they're implemented, clearly labelled as synthetic at the point of
  generation.
