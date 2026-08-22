# Policy & Control Catalog

## Purpose

Document the local policy/control catalog introduced in Milestone 9: how implemented compliance
controls are cataloged, mapped to local governance policies, connected to evidence requirements,
and surfaced for reviewer traceability.

## Scope

This catalog covers the deterministic controls already implemented in
`src/governance_platform/compliance/controls.py` and evaluated by
`src/governance_platform/compliance/evaluation.py`. It does not define a new policy language,
runtime policy engine, live enforcement service, remediation workflow, or regulatory
interpretation layer.

## Policy Catalog

The generated policy catalog groups implemented controls into local portfolio policy domains:

- Inventory Governance Policy
- Dataset Governance Policy
- Model Governance Policy
- Research Governance Policy
- Access Governance Policy
- Audit Completeness Policy
- Evidence Completeness Policy
- Responsible AI Readiness Policy
- Operational Governance Policy

These policies are local governance metadata for review and traceability. They are not legally
binding external policy instruments.

## Control Catalog

Each generated `ControlCatalogEntry` derives from an implemented `ControlDefinition` and augments
it with reviewer-facing metadata:

- objective
- severity
- applies-to entity types
- implementation reference
- deterministic evaluation type
- evidence requirements
- expected evidence-reference patterns
- failure effect
- reviewer guidance
- related policy IDs

The catalog validates that every implemented control has exactly one catalog entry and that every
cataloged control resolves to an implemented control.

## Control Ownership

Ownership is expressed through local policy owner roles:

- Governance Metadata Owner
- Dataset Governance Owner
- Model Governance Owner
- Research Governance Owner
- Access Governance Owner
- Audit Evidence Owner
- Compliance Evidence Owner
- Responsible AI Reviewer
- Governance Operations Owner

These are fictional role labels for a synthetic portfolio project, not real user accounts or live
responsibility assignments.

## Evidence Requirements

Evidence requirements describe the generated source state a control needs, such as:

- `outputs/inventory/inventory_portfolio.json`
- `outputs/access/access_control_state.json`
- `outputs/evidence/audit_events.json`
- `outputs/compliance/control_results.json`
- `docs/architecture/decisions/0001-synthetic-data-only.md`

Current compliance results emit evidence references such as `model:MD-0003`,
`access_grant:AG-0001`, `audit_event:AE-0033`, `audit_log:audit_events`, and
`evidence_pack:EVP-0001`. The policy catalog validates these against the generated reviewer
evidence index.

## Traceability Approach

The traceability matrix is generated to `outputs/policy/control_evidence_traceability.csv`. Each
row ties together:

- local policy ID
- implemented control ID and name
- control domain and severity
- implementation reference
- evidence requirement
- actual evidence reference
- current evaluation status
- finding code
- reviewer location in generated compliance outputs

The matrix is deterministic and generated from current compliance results, not manually assembled.

## Assurance Drift Linkage

Milestone 10 uses the generated control catalog when building
`outputs/assurance/control_drift.csv`. Each changed control row carries the implemented control ID,
related policy ID, control objective, evidence requirement, evidence refs, and reviewer guidance
from the catalog. Assurance drift therefore traces back to implemented controls and generated
evidence without duplicating the control definitions.

The assurance-history layer compares explicit local snapshots only. It does not add live policy
enforcement, scheduled checks, alerting, remediation, or production observability.

## Integrated Review Pack Linkage

Milestone 11 uses the catalog and assurance drift outputs when building
`outputs/assurance_pack/assurance_evidence_map.csv`. Priority findings in the pack carry control
IDs, policy IDs, evidence refs, drift IDs where applicable, reviewer locations, and reviewer
guidance. This makes the generated review pack a compact handoff index over implemented controls
and evidence, not a duplicate control catalog or a new evaluation engine.

The review pack contains review recommendations only. It does not execute approvals,
remediation, notifications, or workflow automation.

## Control Lifecycle

Adding or changing a control should follow this sequence:

1. Update the implemented `ControlDefinition` and evaluator behavior.
2. Update catalog implementation/evidence metadata only where needed.
3. Run `python scripts/generate_compliance.py`.
4. Run `python scripts/generate_reviewer_bundle.py`.
5. Run `python scripts/generate_policy_catalog.py`.
6. Run `python scripts/generate_assurance_history.py`.
7. Run `python scripts/generate_assurance_pack.py`.
8. Run lint, tests, and repository validation.

Catalog validation is expected to fail if implemented controls and catalog metadata drift apart.

## Reviewer Interpretation

Reviewers should use the catalog to answer:

- what control exists
- why it exists
- which local policy owns it
- what entity types it applies to
- which evaluator function implements it
- which evidence supports the current result
- what a warning/failure means
- where to inspect the generated result

The catalog complements the reviewer portal and handoff bundle. It does not replace the generated
compliance assessment or evidence pack.

## Limitations

This catalog is local, deterministic, read-only, synthetic-data-only, and non-production. It does
not implement:

- generic policy DSL or OPA/Rego integration
- live policy enforcement
- Snowflake policy deployment
- Purview policy integration
- Entra Conditional Access
- regulatory interpretation
- automatic remediation
- production compliance orchestration
- Power BI/Fabric deployment
- Terraform deployment
- public hosting
- regulatory certification
