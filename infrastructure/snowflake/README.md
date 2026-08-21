# Snowflake (intended governed data/metadata platform)

**No Snowflake account, connection, warehouse, or credential exists anywhere in this repository.**
This directory documents intended responsibilities only, per ADR
[0003](../../docs/architecture/decisions/0003-snowflake-as-future-governed-platform.md). It
contains no `.sql` migration scripts run against a real account, no connection strings, and no
account identifiers — real or placeholder-that-looks-real.

## Purpose

Snowflake is designated as the platform's future governed data/metadata layer — the eventual
system of record for the metadata/inventory, access, and audit planes described in
[`reports/architecture.md`](../../reports/architecture.md), once those planes are implemented in a
later milestone.

## Documents

- [`governance_responsibilities.md`](governance_responsibilities.md) — the specific governance
  responsibilities Snowflake is expected to carry (RBAC, tagging, masking, audit) and how each
  maps to the platform's governance planes.

## What "intended" means here

Every control described in this directory is a design target for a future implementation
milestone, not a control this repository currently enforces. Any SQL shown in these documents is
illustrative of intended schema/policy shape — it has not been run anywhere, and this repository
does not connect to Snowflake.
