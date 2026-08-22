"""Policy and control catalog for implemented compliance controls.

Milestone 9 formalizes metadata and traceability for the fixed Milestone 5
control evaluator. This module catalogs existing controls; it does not create a
generic policy DSL or perform live policy enforcement.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.compliance.controls import default_control_definitions
from governance_platform.compliance.entities import ComplianceAssessment, ControlDefinition
from governance_platform.compliance.enums import (
    ComplianceEntityType,
    ControlDomain,
    ControlSeverity,
)

POLICY_CATALOG_JSON_FILENAME = "policy_catalog.json"
CONTROL_CATALOG_JSON_FILENAME = "control_catalog.json"
CONTROL_CATALOG_CSV_FILENAME = "control_catalog.csv"
CONTROL_EVIDENCE_TRACEABILITY_CSV_FILENAME = "control_evidence_traceability.csv"
POLICY_ASSURANCE_SUMMARY_JSON_FILENAME = "policy_assurance_summary.json"
POLICY_ASSURANCE_SUMMARY_MARKDOWN_FILENAME = "policy_assurance_summary.md"

POLICY_OUTPUT_FILENAMES: tuple[str, ...] = (
    POLICY_CATALOG_JSON_FILENAME,
    CONTROL_CATALOG_JSON_FILENAME,
    CONTROL_CATALOG_CSV_FILENAME,
    CONTROL_EVIDENCE_TRACEABILITY_CSV_FILENAME,
    POLICY_ASSURANCE_SUMMARY_JSON_FILENAME,
    POLICY_ASSURANCE_SUMMARY_MARKDOWN_FILENAME,
)

_LIST_FIELD_SEPARATOR = ";"


class PolicyDomain(str, Enum):
    """Local policy domains aligned to implemented control domains."""

    INVENTORY_GOVERNANCE = "inventory_governance"
    DATASET_GOVERNANCE = "dataset_governance"
    MODEL_GOVERNANCE = "model_governance"
    RESEARCH_GOVERNANCE = "research_governance"
    ACCESS_GOVERNANCE = "access_governance"
    AUDIT_COMPLETENESS = "audit_completeness"
    EVIDENCE_COMPLETENESS = "evidence_completeness"
    RESPONSIBLE_AI_READINESS = "responsible_ai_readiness"
    OPERATIONAL_GOVERNANCE = "operational_governance"


class PolicyStatus(str, Enum):
    """Restrained local lifecycle status for policy metadata."""

    IMPLEMENTED_LOCAL = "implemented_local"


class EvaluationType(str, Enum):
    """How an implemented control is evaluated."""

    DETERMINISTIC_LOCAL_FUNCTION = "deterministic_local_function"


class SourcePlane(str, Enum):
    """Source planes that can back evidence requirements."""

    INVENTORY = "inventory"
    ACCESS = "access"
    AUDIT = "audit"
    COMPLIANCE = "compliance"
    REPORTING = "reporting"
    GOVERNANCE = "governance"
    REVIEWER = "reviewer"


class EvidenceRequirement(BaseModel):
    """Evidence metadata required by one implemented control."""

    model_config = {"frozen": True, "extra": "forbid"}

    requirement_id: str = Field(pattern=r"^ER-CTRL-\d{4}-\d{2}$")
    control_id: str = Field(pattern=r"^CTRL-\d{4}$")
    evidence_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_plane: SourcePlane
    required: bool = True
    expected_reference_pattern: str = Field(min_length=1)


class PolicyDefinition(BaseModel):
    """Local portfolio policy metadata for implemented controls."""

    model_config = {"frozen": True, "extra": "forbid"}

    policy_id: str = Field(pattern=r"^POL-\d{4}$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    policy_domain: PolicyDomain
    objective: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    status: PolicyStatus
    related_control_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    @field_validator("related_control_ids", "limitations")
    @classmethod
    def _tuple_is_not_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("field must contain at least one value")
        return value


class ControlCatalogEntry(BaseModel):
    """Reviewer-facing catalog metadata for one implemented control."""

    model_config = {"frozen": True, "extra": "forbid"}

    control_id: str = Field(pattern=r"^CTRL-\d{4}$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    control_domain: ControlDomain
    objective: str = Field(min_length=1)
    severity: ControlSeverity
    applies_to: tuple[ComplianceEntityType, ...]
    implementation_ref: str = Field(min_length=1)
    evaluation_type: EvaluationType
    evidence_requirements: tuple[EvidenceRequirement, ...]
    expected_evidence_refs: tuple[str, ...]
    failure_effect: str = Field(min_length=1)
    reviewer_guidance: str = Field(min_length=1)
    policy_ids: tuple[str, ...]
    enabled: bool

    @field_validator("applies_to", "evidence_requirements", "policy_ids")
    @classmethod
    def _tuple_is_not_empty(cls, value: tuple[Any, ...]) -> tuple[Any, ...]:
        if not value:
            raise ValueError("field must contain at least one value")
        return value

    @model_validator(mode="after")
    def _evidence_requirements_belong_to_control(self) -> ControlCatalogEntry:
        for requirement in self.evidence_requirements:
            if requirement.control_id != self.control_id:
                raise ValueError("evidence requirement control_id must match catalog entry")
        return self


class PolicyAssuranceSummary(BaseModel):
    """Aggregate policy/control coverage over the current assessment."""

    model_config = {"frozen": True, "extra": "forbid"}

    generated_at: datetime
    assessment_id: str = Field(pattern=r"^CA-\d{4}$")
    policy_count: int
    control_count: int
    enabled_control_count: int
    evidence_requirement_count: int
    traceability_row_count: int
    controls_by_domain: dict[str, int]
    controls_by_severity: dict[str, int]
    evaluation_status_counts: dict[str, int]
    missing_evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> PolicyAssuranceSummary:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError("policy summary must preserve synthetic/local/non-production flags")
        return self


class PolicyCatalogBundle(BaseModel):
    """Validated in-memory policy/control catalog bundle."""

    model_config = {"frozen": True, "extra": "forbid"}

    policies: tuple[PolicyDefinition, ...]
    controls: tuple[ControlCatalogEntry, ...]
    traceability_rows: tuple[dict[str, Any], ...]
    assurance_summary: PolicyAssuranceSummary


_DOMAIN_POLICY_META: dict[ControlDomain, dict[str, str]] = {
    ControlDomain.INVENTORY_GOVERNANCE: {
        "policy_id": "POL-0001",
        "name": "Inventory Governance Policy",
        "objective": "Maintain complete, uniquely identified, synthetic-only inventory metadata.",
        "owner_role": "Governance Metadata Owner",
    },
    ControlDomain.DATASET_GOVERNANCE: {
        "policy_id": "POL-0002",
        "name": "Dataset Governance Policy",
        "objective": (
            "Ensure governed datasets are classified, approved, and suitable for research use."
        ),
        "owner_role": "Dataset Governance Owner",
    },
    ControlDomain.MODEL_GOVERNANCE: {
        "policy_id": "POL-0003",
        "name": "Model Governance Policy",
        "objective": "Ensure models have approved lifecycle, lineage, and monitoring metadata.",
        "owner_role": "Model Governance Owner",
    },
    ControlDomain.RESEARCH_GOVERNANCE: {
        "policy_id": "POL-0004",
        "name": "Research Governance Policy",
        "objective": "Ensure active access aligns to approved, in-scope research projects.",
        "owner_role": "Research Governance Owner",
    },
    ControlDomain.ACCESS_GOVERNANCE: {
        "policy_id": "POL-0005",
        "name": "Access Governance Policy",
        "objective": "Ensure grants are approved, time-bounded, and lifecycle-correct.",
        "owner_role": "Access Governance Owner",
    },
    ControlDomain.AUDIT_COMPLETENESS: {
        "policy_id": "POL-0006",
        "name": "Audit Completeness Policy",
        "objective": "Ensure expected local audit evidence and correlation chains are present.",
        "owner_role": "Audit Evidence Owner",
    },
    ControlDomain.EVIDENCE_COMPLETENESS: {
        "policy_id": "POL-0007",
        "name": "Evidence Completeness Policy",
        "objective": "Ensure compliance evidence references resolve to generated source state.",
        "owner_role": "Compliance Evidence Owner",
    },
    ControlDomain.RESPONSIBLE_AI_READINESS: {
        "policy_id": "POL-0008",
        "name": "Responsible AI Readiness Policy",
        "objective": "Ensure high-risk model readiness is visible before approved use.",
        "owner_role": "Responsible AI Reviewer",
    },
    ControlDomain.OPERATIONAL_GOVERNANCE: {
        "policy_id": "POL-0009",
        "name": "Operational Governance Policy",
        "objective": (
            "Ensure reviewer-facing operational metadata remains current enough to inspect."
        ),
        "owner_role": "Governance Operations Owner",
    },
}

_EVALUATOR_REF = "governance_platform.compliance.evaluation.ComplianceEvaluator"
_IMPLEMENTATION_REFS: dict[str, str] = {
    "CTRL-0001": f"{_EVALUATOR_REF}._inventory_unique_ids",
    "CTRL-0002": f"{_EVALUATOR_REF}._inventory_refs_resolve",
    "CTRL-0003": f"{_EVALUATOR_REF}._synthetic_only",
    "CTRL-0004": f"{_EVALUATOR_REF}._ownership_metadata",
    "CTRL-0005": f"{_EVALUATOR_REF}._review_dates",
    "CTRL-0006": f"{_EVALUATOR_REF}._research_prohibited_not_granted",
    "CTRL-0007": f"{_EVALUATOR_REF}._granted_datasets_approved",
    "CTRL-0008": f"{_EVALUATOR_REF}._dataset_sensitivity_present",
    "CTRL-0009": f"{_EVALUATOR_REF}._dataset_lifecycle_compatible",
    "CTRL-0010": f"{_EVALUATOR_REF}._approved_high_risk_rai_review",
    "CTRL-0011": f"{_EVALUATOR_REF}._approved_high_risk_monitoring",
    "CTRL-0012": f"{_EVALUATOR_REF}._granted_models_approved",
    "CTRL-0013": f"{_EVALUATOR_REF}._model_dataset_refs_resolve",
    "CTRL-0014": f"{_EVALUATOR_REF}._high_risk_readiness_tracked",
    "CTRL-0015": f"{_EVALUATOR_REF}._active_grant_project_approved",
    "CTRL-0016": f"{_EVALUATOR_REF}._active_grant_project_not_expired",
    "CTRL-0017": f"{_EVALUATOR_REF}._granted_assets_within_scope",
    "CTRL-0018": f"{_EVALUATOR_REF}._grant_decision_evidence",
    "CTRL-0019": f"{_EVALUATOR_REF}._rejected_requests_no_grants",
    "CTRL-0020": f"{_EVALUATOR_REF}._grants_time_bounded",
    "CTRL-0021": f"{_EVALUATOR_REF}._inactive_grants_not_active",
    "CTRL-0022": f"{_EVALUATOR_REF}._audit_completeness",
    "CTRL-0023": f"{_EVALUATOR_REF}._required_lifecycle_events",
    "CTRL-0024": f"{_EVALUATOR_REF}._correlation_traceable",
    "CTRL-0025": f"{_EVALUATOR_REF}._duplicate_audit_ids_absent",
    "CTRL-0026": f"{_EVALUATOR_REF}._evidence_refs_resolve",
}

_EVIDENCE_META: dict[str, tuple[SourcePlane, str, str]] = {
    "inventory_portfolio": (
        SourcePlane.INVENTORY,
        "source_output",
        "outputs/inventory/inventory_portfolio.json",
    ),
    "dataset_registration": (
        SourcePlane.INVENTORY,
        "entity_metadata",
        "outputs/inventory/inventory_portfolio.json",
    ),
    "adr_0001": (
        SourcePlane.GOVERNANCE,
        "architecture_decision",
        "docs/architecture/decisions/0001-synthetic-data-only.md",
    ),
    "access_control_state": (
        SourcePlane.ACCESS,
        "source_output",
        "outputs/access/access_control_state.json",
    ),
    "responsible_ai_review_status": (
        SourcePlane.INVENTORY,
        "entity_metadata",
        "outputs/inventory/inventory_portfolio.json",
    ),
    "audit_events": (SourcePlane.AUDIT, "source_output", "outputs/evidence/audit_events.json"),
    "control_results": (
        SourcePlane.COMPLIANCE,
        "source_output",
        "outputs/compliance/control_results.json",
    ),
    "source_state": (SourcePlane.COMPLIANCE, "source_state", "outputs/"),
}

_EXPECTED_REFERENCE_PATTERNS: dict[str, str] = {
    "inventory_portfolio": "portfolio:synthetic_governance_state or entity-specific inventory refs",
    "dataset_registration": "dataset:<dataset_id>",
    "adr_0001": "adr:0001",
    "access_control_state": "access_request/access_grant/approval_decision refs",
    "responsible_ai_review_status": "model:<model_id>",
    "audit_events": "audit_log:audit_events or audit_event:<event_id>",
    "control_results": "evidence_pack:<evidence_pack_id>",
    "source_state": "any source-state ref emitted by prior compliance results",
}

_LIMITATIONS: tuple[str, ...] = (
    "This is a local portfolio control catalog over implemented deterministic controls.",
    "Policies are local governance metadata, not legally binding external policy instruments.",
    "No generic policy DSL, live enforcement, automated remediation, or certification is provided.",
)


def _domain_to_policy_domain(domain: ControlDomain) -> PolicyDomain:
    return PolicyDomain(domain.value)


def _policy_id_for_domain(domain: ControlDomain) -> str:
    return _DOMAIN_POLICY_META[domain]["policy_id"]


def _requirement(control: ControlDefinition, evidence_name: str, index: int) -> EvidenceRequirement:
    source_plane, evidence_type, source_file = _EVIDENCE_META[evidence_name]
    return EvidenceRequirement(
        requirement_id=f"ER-{control.control_id}-{index:02d}",
        control_id=control.control_id,
        evidence_type=evidence_type,
        description=f"{control.name} requires {evidence_name} ({source_file}).",
        source_plane=source_plane,
        required=True,
        expected_reference_pattern=_EXPECTED_REFERENCE_PATTERNS[evidence_name],
    )


def build_policy_definitions(
    control_definitions: tuple[ControlDefinition, ...] | None = None,
) -> tuple[PolicyDefinition, ...]:
    """Build deterministic local policy metadata for implemented control domains."""
    controls = control_definitions or default_control_definitions()
    policies: list[PolicyDefinition] = []
    for domain in ControlDomain:
        meta = _DOMAIN_POLICY_META[domain]
        related = tuple(
            control.control_id for control in controls if control.control_domain == domain
        )
        policies.append(
            PolicyDefinition(
                policy_id=meta["policy_id"],
                name=meta["name"],
                description=(
                    f"Local portfolio governance policy for {domain.value.replace('_', ' ')} "
                    "controls implemented by the deterministic compliance plane."
                ),
                policy_domain=_domain_to_policy_domain(domain),
                objective=meta["objective"],
                owner_role=meta["owner_role"],
                status=PolicyStatus.IMPLEMENTED_LOCAL,
                related_control_ids=related,
                limitations=_LIMITATIONS,
            )
        )
    return tuple(sorted(policies, key=lambda policy: policy.policy_id))


def build_control_catalog(
    control_definitions: tuple[ControlDefinition, ...] | None = None,
) -> tuple[ControlCatalogEntry, ...]:
    """Build catalog entries directly from implemented control definitions."""
    controls = control_definitions or default_control_definitions()
    entries: list[ControlCatalogEntry] = []
    for control in controls:
        if control.control_id not in _IMPLEMENTATION_REFS:
            raise ValueError(f"missing implementation reference for {control.control_id}")
        requirements = tuple(
            _requirement(control, evidence_name, index)
            for index, evidence_name in enumerate(control.evidence_requirements, start=1)
        )
        policy_id = _policy_id_for_domain(control.control_domain)
        entries.append(
            ControlCatalogEntry(
                control_id=control.control_id,
                name=control.name,
                description=control.description,
                control_domain=control.control_domain,
                objective=(
                    f"Evaluate {control.control_domain.value.replace('_', ' ')} requirement: "
                    f"{control.description}"
                ),
                severity=control.severity,
                applies_to=control.applies_to,
                implementation_ref=_IMPLEMENTATION_REFS[control.control_id],
                evaluation_type=EvaluationType.DETERMINISTIC_LOCAL_FUNCTION,
                evidence_requirements=requirements,
                expected_evidence_refs=tuple(
                    requirement.expected_reference_pattern for requirement in requirements
                ),
                failure_effect=(
                    f"A non-passing result contributes a {control.severity.value} finding and may "
                    "contribute to bounded risk/posture calculations."
                ),
                reviewer_guidance=(
                    f"Review current results for {control.control_id}, inspect listed evidence "
                    "references, and confirm the finding remains consistent with generated "
                    "synthetic source outputs."
                ),
                policy_ids=(policy_id,),
                enabled=control.enabled,
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.control_id))


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple | list):
        return _LIST_FIELD_SEPARATOR.join(str(_csv_value(item)) for item in value)
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, columns: tuple[str, ...], rows: tuple[dict[str, object], ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row.get(column, "")) for column in columns])


def _control_result_lookup(assessment: ComplianceAssessment) -> dict[str, tuple[Any, ...]]:
    grouped: dict[str, list[Any]] = {}
    for result in assessment.control_results:
        grouped.setdefault(result.control_id, []).append(result)
    return {
        control_id: tuple(sorted(results, key=lambda result: result.result_id))
        for control_id, results in grouped.items()
    }


def _source_plane_for_evidence_ref(evidence_ref: str) -> SourcePlane:
    if evidence_ref.startswith(("dataset:", "model:", "research_project:", "portfolio:")):
        return SourcePlane.INVENTORY
    if evidence_ref.startswith(("access_request:", "approval_decision:", "access_grant:")):
        return SourcePlane.ACCESS
    if evidence_ref.startswith(("audit_log:", "audit_event:", "evidence_pack:")):
        return SourcePlane.AUDIT
    if evidence_ref.startswith("adr:"):
        return SourcePlane.GOVERNANCE
    return SourcePlane.COMPLIANCE


def _matching_requirement(
    requirements: tuple[EvidenceRequirement, ...], evidence_ref: str
) -> EvidenceRequirement:
    if evidence_ref == "adr:0001":
        for requirement in requirements:
            if "adr" in requirement.expected_reference_pattern:
                return requirement
    source_plane = _source_plane_for_evidence_ref(evidence_ref)
    for requirement in requirements:
        if requirement.source_plane == source_plane:
            return requirement
    return requirements[0]


def build_traceability_matrix(
    policies: tuple[PolicyDefinition, ...],
    controls: tuple[ControlCatalogEntry, ...],
    assessment: ComplianceAssessment,
) -> tuple[dict[str, Any], ...]:
    """Build deterministic control-to-evidence traceability rows."""
    policy_by_control = {
        control_id: policy.policy_id
        for policy in policies
        for control_id in policy.related_control_ids
    }
    results_by_control = _control_result_lookup(assessment)
    rows: list[dict[str, Any]] = []
    for control in controls:
        results = results_by_control.get(control.control_id, ())
        if not results:
            for requirement in control.evidence_requirements:
                rows.append(
                    {
                        "policy_id": policy_by_control.get(control.control_id, ""),
                        "control_id": control.control_id,
                        "control_name": control.name,
                        "control_domain": control.control_domain.value,
                        "severity": control.severity.value,
                        "applies_to": ";".join(entity.value for entity in control.applies_to),
                        "implementation_ref": control.implementation_ref,
                        "evidence_requirement": requirement.requirement_id,
                        "source_plane": requirement.source_plane.value,
                        "evidence_ref": "",
                        "evaluation_status": "not_evaluated",
                        "finding_code": "",
                        "reviewer_location": "outputs/compliance/control_results.json",
                    }
                )
            continue
        for result in results:
            evidence_refs = result.evidence_refs or ("",)
            for evidence_ref in evidence_refs:
                requirement = _matching_requirement(control.evidence_requirements, evidence_ref)
                rows.append(
                    {
                        "policy_id": policy_by_control[control.control_id],
                        "control_id": control.control_id,
                        "control_name": control.name,
                        "control_domain": control.control_domain.value,
                        "severity": control.severity.value,
                        "applies_to": ";".join(entity.value for entity in control.applies_to),
                        "implementation_ref": control.implementation_ref,
                        "evidence_requirement": requirement.requirement_id,
                        "source_plane": requirement.source_plane.value,
                        "evidence_ref": evidence_ref,
                        "evaluation_status": result.status.value,
                        "finding_code": result.finding_code.value,
                        "reviewer_location": (
                            f"outputs/compliance/control_results.json#{result.result_id}"
                        ),
                    }
                )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row["policy_id"],
                row["control_id"],
                row["evidence_requirement"],
                row["reviewer_location"],
                row["evidence_ref"],
            ),
        )
    )


def validate_policy_catalog(
    policies: tuple[PolicyDefinition, ...],
    controls: tuple[ControlCatalogEntry, ...],
    assessment: ComplianceAssessment,
    *,
    implemented_controls: tuple[ControlDefinition, ...] | None = None,
    known_evidence_refs: set[str] | None = None,
) -> list[str]:
    """Return policy/control catalog validation problems."""
    implemented = implemented_controls or default_control_definitions()
    problems: list[str] = []

    implemented_ids = {control.control_id for control in implemented}
    catalog_ids = {control.control_id for control in controls}
    policy_ids = {policy.policy_id for policy in policies}
    requirement_ids = [
        requirement.requirement_id
        for control in controls
        for requirement in control.evidence_requirements
    ]

    for control_id in sorted(implemented_ids - catalog_ids):
        problems.append(f"implemented control missing from catalog: {control_id}")
    for control_id in sorted(catalog_ids - implemented_ids):
        problems.append(f"catalog control does not resolve to implemented control: {control_id}")
    for control_id, count in sorted(Counter(control.control_id for control in controls).items()):
        if count > 1:
            problems.append(f"duplicate catalog control id: {control_id}")
    for policy_id, count in sorted(Counter(policy.policy_id for policy in policies).items()):
        if count > 1:
            problems.append(f"duplicate policy id: {policy_id}")
    for requirement_id, count in sorted(Counter(requirement_ids).items()):
        if count > 1:
            problems.append(f"duplicate evidence requirement id: {requirement_id}")

    policy_control_refs = {
        control_id for policy in policies for control_id in policy.related_control_ids
    }
    for control in controls:
        if not control.policy_ids:
            problems.append(f"control has no policy reference: {control.control_id}")
        if control.enabled and not control.evidence_requirements:
            problems.append(f"enabled control has no evidence requirement: {control.control_id}")
        for policy_id in control.policy_ids:
            if policy_id not in policy_ids:
                problems.append(
                    f"control {control.control_id} references unknown policy: {policy_id}"
                )
        for requirement in control.evidence_requirements:
            if requirement.control_id != control.control_id:
                problems.append(
                    f"orphan evidence requirement {requirement.requirement_id}: "
                    f"expected {control.control_id}, got {requirement.control_id}"
                )
            if requirement.source_plane not in SourcePlane:
                problems.append(
                    f"evidence requirement has invalid source plane: {requirement.requirement_id}"
                )

    for policy in policies:
        for control_id in policy.related_control_ids:
            if control_id not in catalog_ids:
                problems.append(
                    f"policy {policy.policy_id} references unknown control: {control_id}"
                )
    for control_id in sorted(catalog_ids - policy_control_refs):
        problems.append(f"catalog control is not referenced by any policy: {control_id}")

    assessment_control_ids = {result.control_id for result in assessment.control_results}
    for control_id in sorted(implemented_ids - assessment_control_ids):
        matching = next(control for control in implemented if control.control_id == control_id)
        if matching.enabled:
            problems.append(f"enabled control has no current assessment result: {control_id}")

    if known_evidence_refs is not None:
        evidence_refs = {
            ref for result in assessment.control_results for ref in result.evidence_refs if ref
        }
        for ref in sorted(evidence_refs - known_evidence_refs):
            problems.append(f"expected evidence reference does not resolve: {ref}")

    return problems


def build_policy_assurance_summary(
    policies: tuple[PolicyDefinition, ...],
    controls: tuple[ControlCatalogEntry, ...],
    assessment: ComplianceAssessment,
    traceability_rows: tuple[dict[str, Any], ...],
    *,
    known_evidence_refs: set[str] | None = None,
) -> PolicyAssuranceSummary:
    """Build aggregate policy assurance metadata for reviewer documentation."""
    evidence_refs = {
        ref for result in assessment.control_results for ref in result.evidence_refs if ref
    }
    missing = tuple(sorted(evidence_refs - known_evidence_refs)) if known_evidence_refs else ()
    return PolicyAssuranceSummary(
        generated_at=assessment.evaluated_at,
        assessment_id=assessment.assessment_id,
        policy_count=len(policies),
        control_count=len(controls),
        enabled_control_count=sum(1 for control in controls if control.enabled),
        evidence_requirement_count=sum(len(control.evidence_requirements) for control in controls),
        traceability_row_count=len(traceability_rows),
        controls_by_domain={
            domain.value: sum(1 for control in controls if control.control_domain == domain)
            for domain in ControlDomain
        },
        controls_by_severity={
            severity.value: sum(1 for control in controls if control.severity == severity)
            for severity in ControlSeverity
        },
        evaluation_status_counts={
            status: count
            for status, count in sorted(
                Counter(result.status.value for result in assessment.control_results).items()
            )
        },
        missing_evidence_refs=missing,
        limitations=_LIMITATIONS,
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def build_policy_catalog_bundle(
    assessment: ComplianceAssessment,
    *,
    control_definitions: tuple[ControlDefinition, ...] | None = None,
    known_evidence_refs: set[str] | None = None,
) -> PolicyCatalogBundle:
    """Build and validate the full deterministic policy/control catalog bundle."""
    implemented = control_definitions or default_control_definitions()
    policies = build_policy_definitions(implemented)
    controls = build_control_catalog(implemented)
    traceability = build_traceability_matrix(policies, controls, assessment)
    problems = validate_policy_catalog(
        policies,
        controls,
        assessment,
        implemented_controls=implemented,
        known_evidence_refs=known_evidence_refs,
    )
    if problems:
        raise ValueError("policy catalog validation failed: " + "; ".join(problems))
    summary = build_policy_assurance_summary(
        policies, controls, assessment, traceability, known_evidence_refs=known_evidence_refs
    )
    return PolicyCatalogBundle(
        policies=policies,
        controls=controls,
        traceability_rows=traceability,
        assurance_summary=summary,
    )


def render_policy_assurance_summary_markdown(bundle: PolicyCatalogBundle) -> str:
    """Render concise reviewer-facing policy assurance documentation."""
    summary = bundle.assurance_summary
    lines: list[str] = [
        "# Policy Assurance Summary",
        "",
        "> Local deterministic policy/control catalog over implemented synthetic governance "
        "controls. This is not a regulatory certification or live policy enforcement system.",
        "",
        f"- **Assessment ID:** {summary.assessment_id}",
        f"- **Generated at:** {summary.generated_at.isoformat()}",
        f"- **Policies:** {summary.policy_count}",
        f"- **Controls:** {summary.control_count}",
        f"- **Evidence requirements:** {summary.evidence_requirement_count}",
        f"- **Traceability rows:** {summary.traceability_row_count}",
        "",
        "## Policy Catalog Overview",
        "",
    ]
    for policy in bundle.policies:
        lines.append(
            f"- **{policy.policy_id} — {policy.name}:** {policy.objective} "
            f"({len(policy.related_control_ids)} control(s))"
        )
    lines.extend(["", "## Control Coverage", ""])
    lines.append(f"- Enabled controls: {summary.enabled_control_count}")
    lines.append(f"- Current pass results: {summary.evaluation_status_counts.get('pass', 0)}")
    lines.append(f"- Current warning results: {summary.evaluation_status_counts.get('warning', 0)}")
    lines.append(f"- Current failed results: {summary.evaluation_status_counts.get('fail', 0)}")
    lines.extend(["", "## Controls By Domain", ""])
    lines.extend(f"- {domain}: {count}" for domain, count in summary.controls_by_domain.items())
    lines.extend(["", "## Controls By Severity", ""])
    lines.extend(
        f"- {severity}: {count}" for severity, count in summary.controls_by_severity.items()
    )
    lines.extend(["", "## Evidence Coverage", ""])
    if summary.missing_evidence_refs:
        lines.extend(
            f"- Missing evidence reference: {ref}" for ref in summary.missing_evidence_refs
        )
    else:
        lines.append(
            "- All current compliance-result evidence references resolve in the known index."
        )
    lines.extend(["", "## Reviewer Guidance", ""])
    for control in bundle.controls:
        if control.control_id in {"CTRL-0014", "CTRL-0026"}:
            lines.append(f"- **{control.control_id}:** {control.reviewer_guidance}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in summary.limitations)
    lines.append("")
    return "\n".join(lines)


def _control_catalog_rows(controls: tuple[ControlCatalogEntry, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "control_id": control.control_id,
            "name": control.name,
            "description": control.description,
            "control_domain": control.control_domain.value,
            "objective": control.objective,
            "severity": control.severity.value,
            "applies_to": tuple(entity.value for entity in control.applies_to),
            "implementation_ref": control.implementation_ref,
            "evaluation_type": control.evaluation_type.value,
            "evidence_requirements": tuple(
                requirement.requirement_id for requirement in control.evidence_requirements
            ),
            "expected_evidence_refs": control.expected_evidence_refs,
            "failure_effect": control.failure_effect,
            "reviewer_guidance": control.reviewer_guidance,
            "policy_ids": control.policy_ids,
            "enabled": control.enabled,
        }
        for control in controls
    )


def export_policy_catalog_bundle(bundle: PolicyCatalogBundle, output_dir: str | Path) -> None:
    """Export policy catalog artifacts in deterministic JSON/CSV/Markdown form."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_json(
        out / POLICY_CATALOG_JSON_FILENAME,
        [policy.model_dump(mode="json") for policy in bundle.policies],
    )
    _write_json(
        out / CONTROL_CATALOG_JSON_FILENAME,
        [control.model_dump(mode="json") for control in bundle.controls],
    )
    _write_csv(
        out / CONTROL_CATALOG_CSV_FILENAME,
        (
            "control_id",
            "name",
            "description",
            "control_domain",
            "objective",
            "severity",
            "applies_to",
            "implementation_ref",
            "evaluation_type",
            "evidence_requirements",
            "expected_evidence_refs",
            "failure_effect",
            "reviewer_guidance",
            "policy_ids",
            "enabled",
        ),
        _control_catalog_rows(bundle.controls),
    )
    _write_csv(
        out / CONTROL_EVIDENCE_TRACEABILITY_CSV_FILENAME,
        (
            "policy_id",
            "control_id",
            "control_name",
            "control_domain",
            "severity",
            "applies_to",
            "implementation_ref",
            "evidence_requirement",
            "source_plane",
            "evidence_ref",
            "evaluation_status",
            "finding_code",
            "reviewer_location",
        ),
        bundle.traceability_rows,
    )
    _write_json(
        out / POLICY_ASSURANCE_SUMMARY_JSON_FILENAME,
        bundle.assurance_summary.model_dump(mode="json"),
    )
    (out / POLICY_ASSURANCE_SUMMARY_MARKDOWN_FILENAME).write_text(
        render_policy_assurance_summary_markdown(bundle), encoding="utf-8"
    )


def load_policy_catalog(input_dir: str | Path) -> tuple[PolicyDefinition, ...]:
    """Load canonical policy catalog JSON."""
    path = Path(input_dir) / POLICY_CATALOG_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Policy catalog file not found: {path}")
    return tuple(PolicyDefinition.model_validate(item) for item in json.loads(path.read_text()))


def load_control_catalog(input_dir: str | Path) -> tuple[ControlCatalogEntry, ...]:
    """Load canonical control catalog JSON."""
    path = Path(input_dir) / CONTROL_CATALOG_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Control catalog file not found: {path}")
    return tuple(ControlCatalogEntry.model_validate(item) for item in json.loads(path.read_text()))


def load_policy_assurance_summary(input_dir: str | Path) -> PolicyAssuranceSummary:
    """Load canonical policy assurance summary JSON."""
    path = Path(input_dir) / POLICY_ASSURANCE_SUMMARY_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Policy assurance summary file not found: {path}")
    return PolicyAssuranceSummary.model_validate(json.loads(path.read_text()))


def validate_policy_catalog_files(input_dir: str | Path) -> list[str]:
    """Validate exported policy catalog files without raising."""
    root = Path(input_dir)
    problems: list[str] = []
    for filename in POLICY_OUTPUT_FILENAMES:
        if not (root / filename).is_file():
            problems.append(f"missing policy output: {root / filename}")
    try:
        load_policy_catalog(root)
        load_control_catalog(root)
        load_policy_assurance_summary(root)
    except (FileNotFoundError, ValueError) as exc:
        problems.append(str(exc))
    return problems
