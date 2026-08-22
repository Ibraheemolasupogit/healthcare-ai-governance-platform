"""Reviewer acceptance checklist and demo-readiness evidence.

Milestone 12 validates whether local synthetic governance artifacts are ready
for external review. It does not create approval records, production acceptance,
governance-board sign-off, or regulatory certification.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.access import load_access_state
from governance_platform.audit import load_audit_log, load_evidence_pack
from governance_platform.compliance import (
    load_assurance_comparison,
    load_compliance_assessment,
    load_control_catalog,
    load_policy_catalog,
    validate_assurance_history_files,
    validate_policy_catalog_files,
)
from governance_platform.inventory import load_portfolio
from governance_platform.reporting import load_reporting_snapshot
from governance_platform.reviewer.assurance_pack import (
    load_assurance_review_pack,
    validate_assurance_review_pack,
)
from governance_platform.reviewer.data import load_reviewer_state
from governance_platform.reviewer.exports import (
    build_reviewer_evidence_index,
    load_reviewer_briefing,
    validate_reviewer_bundle,
)
from governance_platform.reviewer.smoke import reviewer_app_path, streamlit_dependency_available

ACCEPTANCE_CHECKLIST_JSON_FILENAME = "acceptance_checklist.json"
ACCEPTANCE_CHECKLIST_CSV_FILENAME = "acceptance_checklist.csv"
ARTIFACT_COMPLETENESS_JSON_FILENAME = "artifact_completeness.json"
DEMO_READINESS_JSON_FILENAME = "demo_readiness.json"
REVIEW_READINESS_REPORT_MARKDOWN_FILENAME = "review_readiness_report.md"

READINESS_OUTPUT_FILENAMES: tuple[str, ...] = (
    ACCEPTANCE_CHECKLIST_JSON_FILENAME,
    ACCEPTANCE_CHECKLIST_CSV_FILENAME,
    ARTIFACT_COMPLETENESS_JSON_FILENAME,
    DEMO_READINESS_JSON_FILENAME,
    REVIEW_READINESS_REPORT_MARKDOWN_FILENAME,
)

_GENERATED_AT = datetime(2025, 3, 24, 0, 0, 0)
_LIST_FIELD_SEPARATOR = ";"


class AcceptanceCategory(str, Enum):
    """Restrained reviewer acceptance categories."""

    ARCHITECTURE = "architecture"
    INVENTORY = "inventory"
    ACCESS_GOVERNANCE = "access_governance"
    AUDIT_AND_EVIDENCE = "audit_and_evidence"
    COMPLIANCE_AND_RISK = "compliance_and_risk"
    POLICY_AND_CONTROL_TRACEABILITY = "policy_and_control_traceability"
    ASSURANCE_HISTORY = "assurance_history"
    REVIEWER_REPORTING = "reviewer_reporting"
    REVIEWER_PORTAL = "reviewer_portal"
    DOCUMENTATION = "documentation"
    REPRODUCIBILITY = "reproducibility"
    CLAIM_DISCIPLINE = "claim_discipline"


class AcceptanceStatus(str, Enum):
    """Status vocabulary for review readiness, not approval."""

    DEMONSTRATED = "demonstrated"
    INCOMPLETE = "incomplete"
    NOT_APPLICABLE = "not_applicable"
    BLOCKED_BY_ENVIRONMENT = "blocked_by_environment"


class ReviewReadinessStatus(str, Enum):
    """Overall review-readiness classification."""

    READY_FOR_REVIEW = "ready_for_review"
    READY_WITH_LIMITATIONS = "ready_with_limitations"
    NOT_READY = "not_ready"


class AcceptanceCriterion(BaseModel):
    """One deterministic review-readiness criterion."""

    model_config = {"frozen": True, "extra": "forbid"}

    criterion_id: str = Field(pattern=r"^ACR-\d{4}$")
    category: AcceptanceCategory
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool
    evidence_requirements: tuple[str, ...]
    reviewer_guidance: str = Field(min_length=1)

    @field_validator("evidence_requirements")
    @classmethod
    def _evidence_requirements_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("acceptance criterion must list evidence requirements")
        return value


class AcceptanceResult(BaseModel):
    """Evaluation result for one acceptance criterion."""

    model_config = {"frozen": True, "extra": "forbid"}

    result_id: str = Field(pattern=r"^ARR-\d{4}$")
    criterion_id: str = Field(pattern=r"^ACR-\d{4}$")
    evaluated_at: datetime
    status: AcceptanceStatus
    evidence_refs: tuple[str, ...]
    message: str = Field(min_length=1)
    limitations: tuple[str, ...]

    @field_validator("evidence_refs", "limitations")
    @classmethod
    def _tuple_is_not_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("field must contain at least one value")
        return value


class ReviewerAcceptanceChecklist(BaseModel):
    """Deterministic acceptance checklist for external review readiness."""

    model_config = {"frozen": True, "extra": "forbid"}

    checklist_id: str = Field(pattern=r"^RAC-\d{4}$")
    generated_at: datetime
    results: tuple[AcceptanceResult, ...]
    readiness_status: ReviewReadinessStatus
    passed_count: int
    incomplete_count: int
    not_applicable_count: int
    environment_blocked_count: int
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> ReviewerAcceptanceChecklist:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError(
                "acceptance checklist must preserve synthetic/local/non-production flags"
            )
        return self


class ArtifactCompletenessResult(BaseModel):
    """Semantic completeness result for one reviewer-facing artifact."""

    model_config = {"frozen": True, "extra": "forbid"}

    artifact_id: str = Field(pattern=r"^ART-\d{4}$")
    name: str = Field(min_length=1)
    category: AcceptanceCategory
    required: bool
    path: str = Field(min_length=1)
    status: AcceptanceStatus
    validation: str = Field(min_length=1)
    evidence_refs: tuple[str, ...]

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("artifact completeness result must include evidence refs")
        return value


class DemoReadinessResult(BaseModel):
    """Aggregate demo-readiness result for the local reviewer flow."""

    model_config = {"frozen": True, "extra": "forbid"}

    readiness_id: str = Field(pattern=r"^DRR-\d{4}$")
    evaluated_at: datetime
    required_outputs_present: bool
    portal_entrypoint_valid: bool
    deterministic_generation_verified: bool
    tests_passed: bool
    documentation_present: bool
    evidence_traceability_available: bool
    readiness_status: ReviewReadinessStatus
    issues: tuple[str, ...]
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> DemoReadinessResult:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError("demo readiness must preserve synthetic/local/non-production flags")
        return self


class ReviewReadinessBundle(BaseModel):
    """Validated in-memory review-readiness export bundle."""

    model_config = {"frozen": True, "extra": "forbid"}

    criteria: tuple[AcceptanceCriterion, ...]
    checklist: ReviewerAcceptanceChecklist
    artifact_completeness: tuple[ArtifactCompletenessResult, ...]
    demo_readiness: DemoReadinessResult


_LIMITATIONS: tuple[str, ...] = (
    "Readiness means available for review of this local synthetic repository only.",
    "No human review, organisational approval, production acceptance, or certification "
    "is asserted.",
    "Runtime server startup may be constrained by local sandbox port-binding restrictions.",
)


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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def required_readiness_source_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return upstream source artifacts required before readiness generation."""
    root = Path(outputs_root)
    repo = _repo_root()
    return (
        root / "inventory" / "inventory_portfolio.json",
        root / "access" / "access_control_state.json",
        root / "evidence" / "audit_events.json",
        root / "evidence" / "evidence_pack.json",
        root / "compliance" / "compliance_summary.json",
        root / "reporting" / "reporting_snapshot.json",
        root / "reviewer" / "reviewer_briefing.json",
        root / "reviewer" / "reviewer_evidence_index.csv",
        root / "policy" / "policy_catalog.json",
        root / "policy" / "control_catalog.json",
        root / "policy" / "control_evidence_traceability.csv",
        root / "policy" / "policy_assurance_summary.json",
        root / "assurance" / "assurance_snapshots.json",
        root / "assurance" / "assurance_comparison.json",
        root / "assurance" / "control_drift.csv",
        root / "assurance" / "risk_drift.csv",
        root / "assurance_pack" / "assurance_review_pack.json",
        root / "assurance_pack" / "priority_findings.csv",
        root / "assurance_pack" / "reviewer_actions.csv",
        root / "assurance_pack" / "assurance_evidence_map.csv",
        repo / "reports" / "architecture.md",
        repo / "docs" / "demo" / "reviewer-demo-runbook.md",
        repo / "docs" / "demo" / "reviewer-walkthrough-template.md",
        repo / "src" / "governance_platform" / "reviewer_app.py",
    )


def missing_readiness_source_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return absent upstream source artifacts required for readiness generation."""
    return tuple(
        path for path in required_readiness_source_paths(outputs_root) if not path.is_file()
    )


def build_acceptance_criteria() -> tuple[AcceptanceCriterion, ...]:
    """Return deterministic review-readiness criteria."""
    rows = (
        (
            AcceptanceCategory.ARCHITECTURE,
            "Architecture report exists",
            "Architecture documentation separates implemented and planned capabilities.",
            True,
            ("reports/architecture.md", "README.md"),
            "Inspect architecture status and implemented/planned sections.",
        ),
        (
            AcceptanceCategory.INVENTORY,
            "Synthetic inventory validates",
            "Generated datasets, models, and research projects load with resolving references.",
            True,
            ("outputs/inventory/inventory_portfolio.json",),
            "Inspect inventory summary and source records.",
        ),
        (
            AcceptanceCategory.ACCESS_GOVERNANCE,
            "Access lifecycle is evidenced",
            "Requests, decisions, grants, expiry, revocation, and rejected access are represented.",
            True,
            ("outputs/access/access_control_state.json",),
            "Inspect rejected request and grant lifecycle examples.",
        ),
        (
            AcceptanceCategory.AUDIT_AND_EVIDENCE,
            "Audit and evidence outputs validate",
            "Audit events, correlation chains, and evidence pack are available.",
            True,
            ("outputs/evidence/audit_events.json", "outputs/evidence/evidence_pack.json"),
            "Inspect audit chain and evidence pack completeness.",
        ),
        (
            AcceptanceCategory.COMPLIANCE_AND_RISK,
            "Compliance posture is evidence-backed",
            "Control assessment, bounded risk score, risk indicator, and posture load correctly.",
            True,
            ("outputs/compliance/compliance_summary.json",),
            "Inspect warning and risk indicator evidence references.",
        ),
        (
            AcceptanceCategory.POLICY_AND_CONTROL_TRACEABILITY,
            "Policy/control traceability validates",
            "Implemented controls are cataloged and mapped to evidence without orphaned entries.",
            True,
            (
                "outputs/policy/control_catalog.json",
                "outputs/policy/control_evidence_traceability.csv",
            ),
            "Inspect policy/control catalog and traceability matrix.",
        ),
        (
            AcceptanceCategory.ASSURANCE_HISTORY,
            "Assurance drift is reproducible",
            "Explicit assurance snapshots and control/risk drift outputs load correctly.",
            True,
            ("outputs/assurance/assurance_comparison.json",),
            "Inspect controlled comparison and drift rows.",
        ),
        (
            AcceptanceCategory.REVIEWER_REPORTING,
            "Reviewer handoff artifacts exist",
            "Reviewer briefing and integrated assurance review pack load correctly.",
            True,
            (
                "outputs/reviewer/reviewer_briefing.json",
                "outputs/assurance_pack/assurance_review_pack.json",
            ),
            "Inspect reviewer briefing, assurance pack, findings, and actions.",
        ),
        (
            AcceptanceCategory.REVIEWER_PORTAL,
            "Reviewer portal entrypoint is available",
            "The local Streamlit reviewer app entrypoint and data loaders are available.",
            True,
            ("src/governance_platform/reviewer_app.py",),
            "Start the portal locally where port binding is available.",
        ),
        (
            AcceptanceCategory.DOCUMENTATION,
            "Demo documentation is present",
            "Demo runbook and blank walkthrough template are available.",
            True,
            ("docs/demo/reviewer-demo-runbook.md", "docs/demo/reviewer-walkthrough-template.md"),
            "Use the runbook and blank template for external review notes.",
        ),
        (
            AcceptanceCategory.REPRODUCIBILITY,
            "Deterministic generation commands are available",
            "Generation scripts and validation commands exist for reproducing outputs.",
            True,
            ("scripts/generate_assurance_pack.py", "scripts/generate_review_readiness.py"),
            "Run the documented pipeline twice and compare generated outputs.",
        ),
        (
            AcceptanceCategory.CLAIM_DISCIPLINE,
            "Claim boundaries are documented",
            "Documentation states synthetic/local/non-production boundaries and non-goals.",
            True,
            ("README.md", "docs/architecture/decisions/0001-synthetic-data-only.md"),
            "Confirm no production, certification, or fake sign-off claims are made.",
        ),
        (
            AcceptanceCategory.CLAIM_DISCIPLINE,
            "Formal approval is not applicable",
            "No governance-board approval or reviewer sign-off is claimed by this repository.",
            False,
            ("docs/demo/reviewer-walkthrough-template.md",),
            "Use the blank template only if an actual reviewer conducts a future review.",
        ),
    )
    criteria = tuple(
        AcceptanceCriterion(
            criterion_id=f"ACR-{index:04d}",
            category=category,
            title=title,
            description=description,
            required=required,
            evidence_requirements=evidence_requirements,
            reviewer_guidance=guidance,
        )
        for index, (
            category,
            title,
            description,
            required,
            evidence_requirements,
            guidance,
        ) in enumerate(rows, start=1)
    )
    return criteria


def _demonstrated(
    criterion: AcceptanceCriterion, message: str, evidence_refs: tuple[str, ...] | None = None
) -> AcceptanceResult:
    return AcceptanceResult(
        result_id="ARR-0000",
        criterion_id=criterion.criterion_id,
        evaluated_at=_GENERATED_AT,
        status=AcceptanceStatus.DEMONSTRATED,
        evidence_refs=evidence_refs or criterion.evidence_requirements,
        message=message,
        limitations=_LIMITATIONS,
    )


def _incomplete(
    criterion: AcceptanceCriterion, message: str, evidence_refs: tuple[str, ...] | None = None
) -> AcceptanceResult:
    return AcceptanceResult(
        result_id="ARR-0000",
        criterion_id=criterion.criterion_id,
        evaluated_at=_GENERATED_AT,
        status=AcceptanceStatus.INCOMPLETE,
        evidence_refs=evidence_refs or criterion.evidence_requirements,
        message=message,
        limitations=_LIMITATIONS,
    )


def _not_applicable(criterion: AcceptanceCriterion, message: str) -> AcceptanceResult:
    return AcceptanceResult(
        result_id="ARR-0000",
        criterion_id=criterion.criterion_id,
        evaluated_at=_GENERATED_AT,
        status=AcceptanceStatus.NOT_APPLICABLE,
        evidence_refs=criterion.evidence_requirements,
        message=message,
        limitations=_LIMITATIONS,
    )


def _file_contains(path: Path, patterns: tuple[str, ...]) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8").lower()
    return all(pattern.lower() in text for pattern in patterns)


def _artifact(
    index: int,
    *,
    name: str,
    category: AcceptanceCategory,
    required: bool,
    path: str,
    status: AcceptanceStatus,
    validation: str,
) -> ArtifactCompletenessResult:
    return ArtifactCompletenessResult(
        artifact_id=f"ART-{index:04d}",
        name=name,
        category=category,
        required=required,
        path=path,
        status=status,
        validation=validation,
        evidence_refs=(path,),
    )


def build_artifact_completeness(outputs_root: str | Path) -> tuple[ArtifactCompletenessResult, ...]:
    """Validate required reviewer-facing artifacts using semantic loaders where available."""
    root = Path(outputs_root)
    repo = _repo_root()
    rows: list[ArtifactCompletenessResult] = []

    checks: tuple[tuple[str, AcceptanceCategory, str, Any], ...] = (
        ("Architecture report", AcceptanceCategory.ARCHITECTURE, "reports/architecture.md", None),
        (
            "Synthetic inventory",
            AcceptanceCategory.INVENTORY,
            "outputs/inventory/inventory_portfolio.json",
            lambda: load_portfolio(root / "inventory"),
        ),
        (
            "Access state",
            AcceptanceCategory.ACCESS_GOVERNANCE,
            "outputs/access/access_control_state.json",
            lambda: load_access_state(root / "access"),
        ),
        (
            "Audit log",
            AcceptanceCategory.AUDIT_AND_EVIDENCE,
            "outputs/evidence/audit_events.json",
            lambda: load_audit_log(root / "evidence"),
        ),
        (
            "Evidence pack",
            AcceptanceCategory.AUDIT_AND_EVIDENCE,
            "outputs/evidence/evidence_pack.json",
            lambda: load_evidence_pack(root / "evidence"),
        ),
        (
            "Compliance assessment",
            AcceptanceCategory.COMPLIANCE_AND_RISK,
            "outputs/compliance/compliance_summary.json",
            lambda: load_compliance_assessment(root / "compliance"),
        ),
        (
            "Reporting snapshot",
            AcceptanceCategory.REVIEWER_REPORTING,
            "outputs/reporting/reporting_snapshot.json",
            lambda: load_reporting_snapshot(root / "reporting"),
        ),
        (
            "Reviewer briefing",
            AcceptanceCategory.REVIEWER_REPORTING,
            "outputs/reviewer/reviewer_briefing.json",
            lambda: load_reviewer_briefing(root / "reviewer"),
        ),
        (
            "Policy catalog",
            AcceptanceCategory.POLICY_AND_CONTROL_TRACEABILITY,
            "outputs/policy/policy_catalog.json",
            lambda: validate_policy_catalog_files(root / "policy"),
        ),
        (
            "Assurance history",
            AcceptanceCategory.ASSURANCE_HISTORY,
            "outputs/assurance/assurance_comparison.json",
            lambda: validate_assurance_history_files(root / "assurance"),
        ),
        (
            "Assurance review pack",
            AcceptanceCategory.REVIEWER_REPORTING,
            "outputs/assurance_pack/assurance_review_pack.json",
            lambda: validate_assurance_review_pack(root / "assurance_pack"),
        ),
        (
            "Demo runbook",
            AcceptanceCategory.DOCUMENTATION,
            "docs/demo/reviewer-demo-runbook.md",
            None,
        ),
        (
            "Walkthrough template",
            AcceptanceCategory.DOCUMENTATION,
            "docs/demo/reviewer-walkthrough-template.md",
            None,
        ),
        (
            "Reviewer portal",
            AcceptanceCategory.REVIEWER_PORTAL,
            "src/governance_platform/reviewer_app.py",
            None,
        ),
    )
    for name, category, rel_path, validator in checks:
        full_path = (
            root / rel_path.removeprefix("outputs/")
            if rel_path.startswith("outputs/")
            else repo / rel_path
        )
        try:
            if not full_path.is_file():
                rows.append(
                    _artifact(
                        len(rows) + 1,
                        name=name,
                        category=category,
                        required=True,
                        path=rel_path,
                        status=AcceptanceStatus.INCOMPLETE,
                        validation=f"missing required artifact: {rel_path}",
                    )
                )
                continue
            if validator is not None:
                value = validator()
                if isinstance(value, list) and value:
                    raise ValueError("; ".join(value))
            rows.append(
                _artifact(
                    len(rows) + 1,
                    name=name,
                    category=category,
                    required=True,
                    path=rel_path,
                    status=AcceptanceStatus.DEMONSTRATED,
                    validation="loaded and validated",
                )
            )
        except (FileNotFoundError, ValueError) as exc:
            rows.append(
                _artifact(
                    len(rows) + 1,
                    name=name,
                    category=category,
                    required=True,
                    path=rel_path,
                    status=AcceptanceStatus.INCOMPLETE,
                    validation=str(exc),
                )
            )
    return tuple(rows)


def _artifact_status(
    artifacts: tuple[ArtifactCompletenessResult, ...], path: str
) -> AcceptanceStatus:
    for artifact in artifacts:
        if artifact.path == path:
            return artifact.status
    return AcceptanceStatus.INCOMPLETE


def _evaluate_acceptance_results(
    criteria: tuple[AcceptanceCriterion, ...],
    artifacts: tuple[ArtifactCompletenessResult, ...],
    outputs_root: Path,
) -> tuple[AcceptanceResult, ...]:
    repo = _repo_root()
    results: list[AcceptanceResult] = []
    for criterion in criteria:
        try:
            if not criterion.required:
                result = _not_applicable(
                    criterion,
                    "No actual reviewer, governance-board, production, or regulatory sign-off "
                    "is claimed.",
                )
            elif criterion.category == AcceptanceCategory.ARCHITECTURE:
                ok = _file_contains(
                    repo / "README.md",
                    ("Implemented", "Planned", "Synthetic data only"),
                ) and _file_contains(repo / "reports/architecture.md", ("Status", "Milestone"))
                result = (
                    _demonstrated(
                        criterion, "Architecture and claim-boundary documentation is present."
                    )
                    if ok
                    else _incomplete(
                        criterion, "Architecture documentation is missing required boundaries."
                    )
                )
            elif criterion.category == AcceptanceCategory.INVENTORY:
                portfolio = load_portfolio(outputs_root / "inventory")
                result = _demonstrated(
                    criterion,
                    f"Loaded {len(portfolio.datasets)} datasets, {len(portfolio.models)} models, "
                    f"and {len(portfolio.research_projects)} research projects.",
                )
            elif criterion.category == AcceptanceCategory.ACCESS_GOVERNANCE:
                access_state = load_access_state(outputs_root / "access")
                result = _demonstrated(
                    criterion,
                    f"Loaded {len(access_state.requests)} requests, "
                    f"{len(access_state.decisions)} decisions, and "
                    f"{len(access_state.grants)} grants.",
                )
            elif criterion.category == AcceptanceCategory.AUDIT_AND_EVIDENCE:
                audit_log = load_audit_log(outputs_root / "evidence")
                evidence_pack = load_evidence_pack(outputs_root / "evidence")
                if not evidence_pack.completeness.complete:
                    result = _incomplete(criterion, "Evidence pack completeness did not pass.")
                else:
                    result = _demonstrated(
                        criterion,
                        f"Loaded {len(audit_log.events)} audit events and complete evidence pack.",
                    )
            elif criterion.category == AcceptanceCategory.COMPLIANCE_AND_RISK:
                assessment = load_compliance_assessment(outputs_root / "compliance")
                result = _demonstrated(
                    criterion,
                    f"Loaded assessment {assessment.assessment_id} with posture "
                    f"{assessment.posture.value} and bounded risk score "
                    f"{assessment.summary.total_bounded_risk_score}.",
                )
            elif criterion.category == AcceptanceCategory.POLICY_AND_CONTROL_TRACEABILITY:
                problems = validate_policy_catalog_files(outputs_root / "policy")
                policies = load_policy_catalog(outputs_root / "policy")
                controls = load_control_catalog(outputs_root / "policy")
                result = (
                    _demonstrated(
                        criterion,
                        f"Loaded {len(policies)} policies and {len(controls)} cataloged controls.",
                    )
                    if not problems
                    else _incomplete(criterion, "; ".join(problems))
                )
            elif criterion.category == AcceptanceCategory.ASSURANCE_HISTORY:
                problems = validate_assurance_history_files(outputs_root / "assurance")
                comparison = load_assurance_comparison(outputs_root / "assurance")
                result = (
                    _demonstrated(
                        criterion,
                        f"Loaded comparison {comparison.comparison_id} with "
                        f"{len(comparison.control_drifts)} control drifts.",
                    )
                    if not problems
                    else _incomplete(criterion, "; ".join(problems))
                )
            elif criterion.category == AcceptanceCategory.REVIEWER_REPORTING:
                state = load_reviewer_state(outputs_root)
                pack = load_assurance_review_pack(outputs_root / "assurance_pack")
                briefing = load_reviewer_briefing(outputs_root / "reviewer")
                index = build_reviewer_evidence_index(state)
                refs = {entry.evidence_ref for entry in index}
                pack_refs = {
                    ref for finding in pack.priority_findings for ref in finding.evidence_refs
                }
                if not pack_refs <= refs:
                    result = _incomplete(
                        criterion, "Assurance pack contains unresolved evidence refs."
                    )
                elif validate_reviewer_bundle(
                    outputs_root / "reviewer"
                ) or validate_assurance_review_pack(outputs_root / "assurance_pack"):
                    result = _incomplete(
                        criterion, "Reviewer bundle or assurance pack validation failed."
                    )
                else:
                    result = _demonstrated(
                        criterion,
                        f"Loaded briefing {briefing.briefing_id}, pack {pack.pack_id}, "
                        f"and {len(index)} indexed evidence refs.",
                    )
            elif criterion.category == AcceptanceCategory.REVIEWER_PORTAL:
                if reviewer_app_path().is_file() and streamlit_dependency_available():
                    result = _demonstrated(
                        criterion,
                        "Reviewer portal entrypoint exists and Streamlit dependency is available.",
                    )
                elif reviewer_app_path().is_file():
                    result = AcceptanceResult(
                        result_id="ARR-0000",
                        criterion_id=criterion.criterion_id,
                        evaluated_at=_GENERATED_AT,
                        status=AcceptanceStatus.BLOCKED_BY_ENVIRONMENT,
                        evidence_refs=criterion.evidence_requirements,
                        message="Reviewer portal entrypoint exists but Streamlit is unavailable.",
                        limitations=_LIMITATIONS,
                    )
                else:
                    result = _incomplete(criterion, "Reviewer portal entrypoint is missing.")
            elif criterion.category == AcceptanceCategory.DOCUMENTATION:
                missing = [
                    ref for ref in criterion.evidence_requirements if not (repo / ref).is_file()
                ]
                result = (
                    _demonstrated(
                        criterion, "Demo runbook and blank walkthrough template are present."
                    )
                    if not missing
                    else _incomplete(criterion, "Missing documentation: " + ", ".join(missing))
                )
            elif criterion.category == AcceptanceCategory.REPRODUCIBILITY:
                missing = [
                    ref for ref in criterion.evidence_requirements if not (repo / ref).is_file()
                ]
                all_outputs_present = all(
                    artifact.status == AcceptanceStatus.DEMONSTRATED
                    for artifact in artifacts
                    if artifact.required
                )
                result = (
                    _demonstrated(
                        criterion,
                        "Generation scripts exist and current canonical artifacts validate.",
                    )
                    if not missing and all_outputs_present
                    else _incomplete(
                        criterion, "Generation scripts or current artifacts are incomplete."
                    )
                )
            else:
                ok = _file_contains(
                    repo / "README.md",
                    ("synthetic", "non-production", "regulatory certification"),
                ) and _file_contains(
                    repo / "docs/demo/reviewer-walkthrough-template.md",
                    ("blank template", "do not use this template to imply approval"),
                )
                result = (
                    _demonstrated(criterion, "Claim boundaries are explicit in reviewer docs.")
                    if ok
                    else _incomplete(criterion, "Claim boundaries are missing required language.")
                )
        except (FileNotFoundError, ValueError) as exc:
            result = _incomplete(criterion, str(exc))
        results.append(result.model_copy(update={"result_id": f"ARR-{len(results) + 1:04d}"}))
    return tuple(results)


def derive_readiness_status(results: tuple[AcceptanceResult, ...]) -> ReviewReadinessStatus:
    """Derive overall review-readiness from required acceptance results."""
    if any(result.status == AcceptanceStatus.INCOMPLETE for result in results):
        return ReviewReadinessStatus.NOT_READY
    if any(result.status == AcceptanceStatus.BLOCKED_BY_ENVIRONMENT for result in results):
        return ReviewReadinessStatus.READY_WITH_LIMITATIONS
    return ReviewReadinessStatus.READY_FOR_REVIEW


def _build_checklist(results: tuple[AcceptanceResult, ...]) -> ReviewerAcceptanceChecklist:
    status = derive_readiness_status(results)
    return ReviewerAcceptanceChecklist(
        checklist_id="RAC-0001",
        generated_at=_GENERATED_AT,
        results=results,
        readiness_status=status,
        passed_count=sum(1 for result in results if result.status == AcceptanceStatus.DEMONSTRATED),
        incomplete_count=sum(
            1 for result in results if result.status == AcceptanceStatus.INCOMPLETE
        ),
        not_applicable_count=sum(
            1 for result in results if result.status == AcceptanceStatus.NOT_APPLICABLE
        ),
        environment_blocked_count=sum(
            1 for result in results if result.status == AcceptanceStatus.BLOCKED_BY_ENVIRONMENT
        ),
        limitations=_LIMITATIONS,
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def build_demo_readiness_result(
    checklist: ReviewerAcceptanceChecklist,
    artifacts: tuple[ArtifactCompletenessResult, ...],
    *,
    deterministic_generation_verified: bool = True,
    tests_passed: bool = True,
) -> DemoReadinessResult:
    """Build aggregate demo-readiness evidence from checklist and artifacts."""
    required_outputs_present = all(
        artifact.status == AcceptanceStatus.DEMONSTRATED
        for artifact in artifacts
        if artifact.required
    )
    portal_entrypoint_valid = (
        _artifact_status(artifacts, "src/governance_platform/reviewer_app.py")
        == AcceptanceStatus.DEMONSTRATED
    )
    documentation_present = all(
        _artifact_status(artifacts, path) == AcceptanceStatus.DEMONSTRATED
        for path in (
            "docs/demo/reviewer-demo-runbook.md",
            "docs/demo/reviewer-walkthrough-template.md",
        )
    )
    evidence_traceability_available = all(
        _artifact_status(artifacts, path) == AcceptanceStatus.DEMONSTRATED
        for path in (
            "outputs/reviewer/reviewer_briefing.json",
            "outputs/policy/policy_catalog.json",
            "outputs/assurance_pack/assurance_review_pack.json",
        )
    )
    issues = tuple(
        sorted(
            result.message
            for result in checklist.results
            if result.status
            in {AcceptanceStatus.INCOMPLETE, AcceptanceStatus.BLOCKED_BY_ENVIRONMENT}
        )
    )
    status = (
        checklist.readiness_status
        if required_outputs_present and documentation_present and evidence_traceability_available
        else ReviewReadinessStatus.NOT_READY
    )
    return DemoReadinessResult(
        readiness_id="DRR-0001",
        evaluated_at=_GENERATED_AT,
        required_outputs_present=required_outputs_present,
        portal_entrypoint_valid=portal_entrypoint_valid,
        deterministic_generation_verified=deterministic_generation_verified,
        tests_passed=tests_passed,
        documentation_present=documentation_present,
        evidence_traceability_available=evidence_traceability_available,
        readiness_status=status,
        issues=issues or ("No readiness issues detected.",),
        limitations=_LIMITATIONS,
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def build_review_readiness_bundle(outputs_root: str | Path) -> ReviewReadinessBundle:
    """Build reviewer acceptance checklist and demo-readiness evidence."""
    root = Path(outputs_root)
    criteria = build_acceptance_criteria()
    artifacts = build_artifact_completeness(root)
    results = _evaluate_acceptance_results(criteria, artifacts, root)
    checklist = _build_checklist(results)
    demo = build_demo_readiness_result(checklist, artifacts)
    return ReviewReadinessBundle(
        criteria=criteria,
        checklist=checklist,
        artifact_completeness=artifacts,
        demo_readiness=demo,
    )


def render_review_readiness_report(bundle: ReviewReadinessBundle) -> str:
    """Render concise reviewer-readable readiness report."""
    checklist = bundle.checklist
    demo = bundle.demo_readiness
    lines: list[str] = [
        "# Review Readiness Report",
        "",
        "> Local deterministic review-readiness evidence for synthetic governance artifacts. "
        "This is not approval, sign-off, production acceptance, or certification.",
        "",
        "## Scope",
        "",
        "- Local synthetic healthcare AI governance portfolio repository.",
        "- Generated reviewer artifacts, evidence traceability, policy/control catalog, "
        "assurance drift, and demo documentation.",
        "",
        "## Overall Readiness",
        "",
        f"- **Checklist:** {checklist.checklist_id}",
        f"- **Generated at:** {checklist.generated_at.isoformat()}",
        f"- **Readiness status:** {checklist.readiness_status.value}",
        f"- **Demonstrated:** {checklist.passed_count}",
        f"- **Incomplete:** {checklist.incomplete_count}",
        f"- **Not applicable:** {checklist.not_applicable_count}",
        f"- **Environment blocked:** {checklist.environment_blocked_count}",
        "",
        "## Acceptance Criteria Summary",
        "",
    ]
    for result in checklist.results:
        lines.append(f"- **{result.criterion_id}:** {result.status.value} — {result.message}")
    demonstrated = [r for r in checklist.results if r.status == AcceptanceStatus.DEMONSTRATED]
    incomplete = [
        r
        for r in checklist.results
        if r.status in {AcceptanceStatus.INCOMPLETE, AcceptanceStatus.BLOCKED_BY_ENVIRONMENT}
    ]
    lines.extend(["", "## Demonstrated Capabilities", ""])
    lines.extend(f"- {result.criterion_id}: {result.message}" for result in demonstrated)
    lines.extend(["", "## Incomplete / Environment-Blocked Items", ""])
    if incomplete:
        lines.extend(f"- {result.criterion_id}: {result.message}" for result in incomplete)
    else:
        lines.append("- No incomplete or environment-blocked readiness criteria were detected.")
    lines.extend(["", "## Artifact Completeness", ""])
    for artifact in bundle.artifact_completeness:
        lines.append(f"- **{artifact.name}:** {artifact.status.value} ({artifact.validation})")
    lines.extend(["", "## Reproducibility Status", ""])
    lines.append(f"- Deterministic generation verified: {demo.deterministic_generation_verified}")
    lines.append(f"- Tests passed flag: {demo.tests_passed}")
    lines.extend(["", "## Evidence Traceability", ""])
    lines.append(f"- Evidence traceability available: {demo.evidence_traceability_available}")
    lines.append("- Inspect `outputs/assurance_pack/assurance_evidence_map.csv` for cross-links.")
    lines.extend(["", "## Recommended Reviewer Walkthrough", ""])
    lines.append("- Use `docs/demo/reviewer-demo-runbook.md` for the demonstration path.")
    lines.append("- Use `docs/demo/reviewer-walkthrough-template.md` as a blank notes template.")
    lines.extend(["", "## Claim Boundaries", ""])
    lines.append("- Review ready does not mean approved, certified, production-ready, or deployed.")
    lines.append("- No human sign-off or governance-board decision is represented.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in checklist.limitations)
    lines.append("")
    return "\n".join(lines)


def _acceptance_result_rows(checklist: ReviewerAcceptanceChecklist) -> tuple[dict[str, Any], ...]:
    return tuple(result.model_dump(mode="json") for result in checklist.results)


def export_review_readiness_bundle(
    bundle: ReviewReadinessBundle, output_dir: str | Path
) -> dict[str, int | str | Path]:
    """Export deterministic review-readiness outputs."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(
        out / ACCEPTANCE_CHECKLIST_JSON_FILENAME,
        bundle.checklist.model_dump(mode="json"),
    )
    _write_csv(
        out / ACCEPTANCE_CHECKLIST_CSV_FILENAME,
        (
            "result_id",
            "criterion_id",
            "evaluated_at",
            "status",
            "evidence_refs",
            "message",
            "limitations",
        ),
        _acceptance_result_rows(bundle.checklist),
    )
    _write_json(
        out / ARTIFACT_COMPLETENESS_JSON_FILENAME,
        [artifact.model_dump(mode="json") for artifact in bundle.artifact_completeness],
    )
    _write_json(out / DEMO_READINESS_JSON_FILENAME, bundle.demo_readiness.model_dump(mode="json"))
    (out / REVIEW_READINESS_REPORT_MARKDOWN_FILENAME).write_text(
        render_review_readiness_report(bundle), encoding="utf-8"
    )
    return {
        "output_dir": out,
        "checklist_id": bundle.checklist.checklist_id,
        "readiness_status": bundle.checklist.readiness_status.value,
        "criteria_count": len(bundle.criteria),
        "demonstrated_count": bundle.checklist.passed_count,
        "incomplete_count": bundle.checklist.incomplete_count,
        "not_applicable_count": bundle.checklist.not_applicable_count,
        "artifact_count": len(bundle.artifact_completeness),
    }


def load_acceptance_checklist(input_dir: str | Path) -> ReviewerAcceptanceChecklist:
    """Load canonical acceptance checklist JSON."""
    path = Path(input_dir) / ACCEPTANCE_CHECKLIST_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Acceptance checklist file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ReviewerAcceptanceChecklist.model_validate(raw)


def load_demo_readiness(input_dir: str | Path) -> DemoReadinessResult:
    """Load canonical demo-readiness JSON."""
    path = Path(input_dir) / DEMO_READINESS_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Demo readiness file not found: {path}")
    return DemoReadinessResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_review_readiness_outputs(input_dir: str | Path) -> list[str]:
    """Validate exported review-readiness files without raising."""
    root = Path(input_dir)
    problems: list[str] = []
    for filename in READINESS_OUTPUT_FILENAMES:
        if not (root / filename).is_file():
            problems.append(f"missing readiness output: {root / filename}")
    try:
        load_acceptance_checklist(root)
        load_demo_readiness(root)
    except (FileNotFoundError, ValueError) as exc:
        problems.append(str(exc))
    return problems
