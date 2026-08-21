# 0003. Snowflake as future governed data/metadata platform

**Status:** Accepted

## Context

The platform needs an eventual system of record for governed data and metadata — dataset and
model inventory, access grants, audit events — that supports the access controls, data
classification, and audit primitives healthcare governance requires (role-based access control,
column/row-level security, object tagging, native query/audit history). It also needs to be a
platform commonly encountered in real healthcare and enterprise data-governance settings, so the
portfolio value of the platform reflects realistic tooling choices.

No such platform exists yet in this project — there is no Snowflake account, warehouse, or
connection configured anywhere in this repository.

## Decision

Snowflake is designated as the platform's future governed data/metadata layer. When later
milestones implement the metadata/inventory, access, audit, or risk planes with a persistent
backing store, that store will be modelled as Snowflake — using its RBAC model, tagging, masking
policies, row access policies, and ACCOUNT_USAGE-based audit views — documented today only at the
level of intended responsibilities in [`infrastructure/snowflake/`](../../../infrastructure/snowflake/).

Until a milestone explicitly implements it, no code in this repository connects to Snowflake, no
credentials or account identifiers are stored anywhere, and no claim is made that a Snowflake
account backing this platform exists.

## Consequences

- Later milestones can design schemas, roles, and policies against a well-understood, real
  platform rather than an abstract one, improving realism of the eventual implementation.
- This repository must not accumulate Snowflake connection code, credentials, or account
  references before an implementation milestone actually lands — `infrastructure/snowflake/`
  stays documentation-only until then.
- If a future milestone determines Snowflake is impractical (e.g. cost, access), this ADR should
  be superseded rather than silently ignored, since downstream docs (architecture, governance
  operating model) reference Snowflake by name.
