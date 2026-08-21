# Terraform (restrained foundation)

## Purpose

Establish naming and tagging conventions for future infrastructure modules, without provisioning
anything. **This configuration declares no provider and no resources.** There is nothing here to
`apply` against real infrastructure — `terraform plan` against this configuration produces no
changes because there is nothing to change.

## Contents

- `versions.tf` — Terraform version constraint only, no provider block.
- `variables.tf` — placeholder inputs (`project_name`, `environment`, `owner`) that future modules
  are expected to consume.
- `main.tf` — a `local` value deriving a naming prefix and a common tag set from those variables,
  for future resources to reference.
- `outputs.tf` — exposes the naming prefix and tag set for inspection.

## What this deliberately does not include

- No cloud provider (AWS/Azure/GCP), no Snowflake provider, no Fabric/Power BI provider.
- No backend configuration (state stays local if you ever run this, and nothing writes state
  today since there are no resources).
- No `.tfvars` file with real values — `variables.tf` defaults are placeholders.
- No CI step runs `terraform plan`/`apply`; this scaffold is not wired into
  [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) because there is nothing to
  validate against a real backend yet.

## Local validation (optional)

If you have Terraform installed locally, this configuration is safe to initialise and validate —
it will not contact any provider or provision anything, because none is declared:

```bash
cd infrastructure/terraform
terraform init
terraform validate
```

## Intended future direction

As governance planes are implemented, this directory is expected to grow provider-specific
modules (e.g. Snowflake RBAC/tagging objects backing
[`infrastructure/snowflake/`](../snowflake/), Fabric capacity/workspace configuration backing
[`fabric/`](../../fabric/)) — each introduced deliberately, alongside the milestone that needs it,
not provisioned speculatively.
