"""Deterministic assurance-history snapshots and drift comparison.

Milestone 10 compares explicit local snapshots of governance assessment state.
It does not use wall-clock telemetry, scheduling, alerting, remediation, or a
production history database.
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

from governance_platform.compliance.catalog import ControlCatalogEntry
from governance_platform.compliance.controls import default_control_definitions
from governance_platform.compliance.entities import ComplianceAssessment, ControlResult
from governance_platform.compliance.enums import (
    ComplianceEntityType,
    ControlSeverity,
    ControlStatus,
    FindingCode,
    GovernancePosture,
)
from governance_platform.compliance.evaluation import build_compliance_summary
from governance_platform.compliance.risk import (
    derive_posture,
    derive_risk_indicators,
    total_bounded_risk_score,
)

ASSURANCE_SNAPSHOTS_JSON_FILENAME = "assurance_snapshots.json"
ASSURANCE_COMPARISON_JSON_FILENAME = "assurance_comparison.json"
CONTROL_DRIFT_CSV_FILENAME = "control_drift.csv"
RISK_DRIFT_CSV_FILENAME = "risk_drift.csv"
ASSURANCE_DRIFT_SUMMARY_JSON_FILENAME = "assurance_drift_summary.json"
ASSURANCE_DRIFT_REPORT_MARKDOWN_FILENAME = "assurance_drift_report.md"

ASSURANCE_OUTPUT_FILENAMES: tuple[str, ...] = (
    ASSURANCE_SNAPSHOTS_JSON_FILENAME,
    ASSURANCE_COMPARISON_JSON_FILENAME,
    CONTROL_DRIFT_CSV_FILENAME,
    RISK_DRIFT_CSV_FILENAME,
    ASSURANCE_DRIFT_SUMMARY_JSON_FILENAME,
    ASSURANCE_DRIFT_REPORT_MARKDOWN_FILENAME,
)

_LIST_FIELD_SEPARATOR = ";"
_BASELINE_CAPTURED_AT = datetime(2025, 3, 15, 0, 0, 0)
_COMPARISON_CAPTURED_AT = datetime(2025, 3, 22, 0, 0, 0)
_COMPARISON_COMPARED_AT = datetime(2025, 3, 22, 0, 0, 0)


class DriftType(str, Enum):
    """Restrained deterministic drift taxonomy."""

    UNCHANGED = "unchanged"
    IMPROVED = "improved"
    DEGRADED = "degraded"
    NEW_FINDING = "new_finding"
    RESOLVED_FINDING = "resolved_finding"
    SEVERITY_INCREASED = "severity_increased"
    SEVERITY_DECREASED = "severity_decreased"
    POSTURE_IMPROVED = "posture_improved"
    POSTURE_DEGRADED = "posture_degraded"


class SnapshotControlResult(BaseModel):
    """Control-result state captured in an assurance snapshot."""

    model_config = {"frozen": True, "extra": "forbid"}

    result_id: str = Field(pattern=r"^CR-\d{4}$")
    control_id: str = Field(pattern=r"^CTRL-\d{4}$")
    entity_type: ComplianceEntityType
    entity_id: str = Field(min_length=1)
    status: ControlStatus
    severity: ControlSeverity
    finding_code: FindingCode
    evidence_refs: tuple[str, ...] = ()
    policy_ids: tuple[str, ...]
    control_objective: str = Field(min_length=1)
    reviewer_guidance: str = Field(min_length=1)

    @field_validator("policy_ids")
    @classmethod
    def _policy_ids_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("snapshot control result must include policy linkage")
        return value


class AssuranceSnapshot(BaseModel):
    """A deterministic local snapshot of compliance assurance state."""

    model_config = {"frozen": True, "extra": "forbid"}

    snapshot_id: str = Field(pattern=r"^AS-\d{4}$")
    captured_at: datetime
    assessment_id: str = Field(pattern=r"^CA-\d{4}$")
    posture: GovernancePosture
    bounded_risk_score: int = Field(ge=0, le=100)
    control_status_counts: dict[str, int]
    findings_by_severity: dict[str, int]
    findings_by_domain: dict[str, int]
    risk_indicator_count: int
    control_results: tuple[SnapshotControlResult, ...]
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @field_validator("source_refs", "limitations")
    @classmethod
    def _tuple_is_not_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("field must contain at least one value")
        return value

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> AssuranceSnapshot:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError(
                "assurance snapshot must preserve synthetic/local/non-production flags"
            )
        return self


class ControlDrift(BaseModel):
    """Drift for one control/entity result between two snapshots."""

    model_config = {"frozen": True, "extra": "forbid"}

    drift_id: str = Field(pattern=r"^CD-\d{4}$")
    control_id: str = Field(pattern=r"^CTRL-\d{4}$")
    policy_ids: tuple[str, ...]
    control_objective: str = Field(min_length=1)
    previous_status: str = Field(min_length=1)
    current_status: str = Field(min_length=1)
    previous_finding_code: str
    current_finding_code: str
    severity: ControlSeverity
    previous_severity: str
    current_severity: str
    drift_type: DriftType
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    evidence_requirement: str = Field(min_length=1)
    reviewer_guidance: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    @field_validator("policy_ids")
    @classmethod
    def _policy_ids_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("control drift must include policy linkage")
        return value


class RiskDrift(BaseModel):
    """Risk/category drift between two snapshots."""

    model_config = {"frozen": True, "extra": "forbid"}

    drift_id: str = Field(pattern=r"^RD-\d{4}$")
    category: str = Field(min_length=1)
    previous_score: int = Field(ge=0, le=100)
    current_score: int = Field(ge=0, le=100)
    score_delta: int
    severity: ControlSeverity
    drift_type: DriftType
    explanation: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()


class AssuranceComparison(BaseModel):
    """Deterministic comparison between two explicit assurance snapshots."""

    model_config = {"frozen": True, "extra": "forbid"}

    comparison_id: str = Field(pattern=r"^AC-\d{4}$")
    previous_snapshot_id: str = Field(pattern=r"^AS-\d{4}$")
    current_snapshot_id: str = Field(pattern=r"^AS-\d{4}$")
    compared_at: datetime
    previous_posture: GovernancePosture
    current_posture: GovernancePosture
    previous_bounded_risk_score: int = Field(ge=0, le=100)
    current_bounded_risk_score: int = Field(ge=0, le=100)
    risk_score_delta: int
    control_drifts: tuple[ControlDrift, ...]
    risk_drifts: tuple[RiskDrift, ...]
    posture_change: DriftType
    summary: dict[str, Any]
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @field_validator("summary", mode="before")
    @classmethod
    def _summary_domains_are_tuple(cls, value: dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, dict) and isinstance(value.get("changed_governance_domains"), list):
            return {
                **value,
                "changed_governance_domains": tuple(value["changed_governance_domains"]),
            }
        return value

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> AssuranceComparison:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError(
                "assurance comparison must preserve synthetic/local/non-production flags"
            )
        return self


class AssuranceHistory(BaseModel):
    """Small file-backed history abstraction for explicit local snapshots."""

    model_config = {"frozen": True, "extra": "forbid"}

    snapshots: tuple[AssuranceSnapshot, ...]

    @field_validator("snapshots")
    @classmethod
    def _snapshots_are_unique(
        cls, value: tuple[AssuranceSnapshot, ...]
    ) -> tuple[AssuranceSnapshot, ...]:
        ids = [snapshot.snapshot_id for snapshot in value]
        duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate assurance snapshot id(s): {', '.join(duplicates)}")
        return value

    def ordered_snapshots(self) -> tuple[AssuranceSnapshot, ...]:
        """Return snapshots ordered by explicit timestamp, then ID."""
        return tuple(sorted(self.snapshots, key=lambda item: (item.captured_at, item.snapshot_id)))

    def snapshot_by_id(self, snapshot_id: str) -> AssuranceSnapshot:
        """Return a snapshot by ID or raise a clear error."""
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        raise KeyError(f"assurance snapshot not found: {snapshot_id}")

    def prior_current_pair(self) -> tuple[AssuranceSnapshot, AssuranceSnapshot]:
        """Return the deterministic prior/current pair from explicit timestamps."""
        ordered = self.ordered_snapshots()
        if len(ordered) < 2:
            raise ValueError("at least two assurance snapshots are required for comparison")
        return ordered[-2], ordered[-1]


class AssuranceHistoryBundle(BaseModel):
    """Validated in-memory assurance history export bundle."""

    model_config = {"frozen": True, "extra": "forbid"}

    history: AssuranceHistory
    comparison: AssuranceComparison


_LIMITATIONS: tuple[str, ...] = (
    "Assurance history is generated from explicit deterministic local snapshots only.",
    "The controlled comparison scenario is synthetic and does not represent production telemetry.",
    "No live monitoring, scheduled evaluation, alerting, remediation, or "
    "certification is provided.",
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


def _status_counts(results: tuple[ControlResult, ...]) -> dict[str, int]:
    counts = Counter(result.status.value for result in results)
    return {status.value: counts.get(status.value, 0) for status in ControlStatus}


def _catalog_by_control(
    control_catalog: tuple[ControlCatalogEntry, ...],
) -> dict[str, ControlCatalogEntry]:
    return {control.control_id: control for control in control_catalog}


def _snapshot_result(result: ControlResult, catalog: ControlCatalogEntry) -> SnapshotControlResult:
    return SnapshotControlResult(
        result_id=result.result_id,
        control_id=result.control_id,
        entity_type=result.entity_type,
        entity_id=result.entity_id,
        status=result.status,
        severity=result.severity,
        finding_code=result.finding_code,
        evidence_refs=result.evidence_refs,
        policy_ids=catalog.policy_ids,
        control_objective=catalog.objective,
        reviewer_guidance=catalog.reviewer_guidance,
    )


def build_assurance_snapshot(
    assessment: ComplianceAssessment,
    control_catalog: tuple[ControlCatalogEntry, ...],
    *,
    snapshot_id: str,
    captured_at: datetime,
    source_refs: tuple[str, ...] | None = None,
    limitations: tuple[str, ...] = _LIMITATIONS,
) -> AssuranceSnapshot:
    """Build a deterministic assurance snapshot from assessment and catalog state."""
    catalog_by_id = _catalog_by_control(control_catalog)
    missing_catalog = sorted(
        {result.control_id for result in assessment.control_results} - set(catalog_by_id)
    )
    if missing_catalog:
        raise ValueError(
            "control result(s) missing policy/catalog linkage: " + ", ".join(missing_catalog)
        )
    results = tuple(
        _snapshot_result(result, catalog_by_id[result.control_id])
        for result in sorted(
            assessment.control_results,
            key=lambda item: (
                item.control_id,
                item.entity_type.value,
                item.entity_id,
                item.result_id,
            ),
        )
    )
    return AssuranceSnapshot(
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        assessment_id=assessment.assessment_id,
        posture=assessment.posture,
        bounded_risk_score=total_bounded_risk_score(assessment.risk_indicators),
        control_status_counts=_status_counts(assessment.control_results),
        findings_by_severity=dict(sorted(assessment.summary.findings_by_severity.items())),
        findings_by_domain=dict(sorted(assessment.summary.findings_by_domain.items())),
        risk_indicator_count=len(assessment.risk_indicators),
        control_results=results,
        source_refs=source_refs
        or (
            "outputs/compliance/compliance_summary.json",
            "outputs/policy/control_catalog.json",
            "outputs/policy/control_evidence_traceability.csv",
        ),
        limitations=limitations,
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def build_controlled_comparison_assessment(
    assessment: ComplianceAssessment,
) -> ComplianceAssessment:
    """Return a small deterministic variant for assurance-drift demonstration."""
    updated_results: list[ControlResult] = []
    degraded_review_date = False
    resolved_readiness = False
    for result in assessment.control_results:
        if (
            not resolved_readiness
            and result.control_id == "CTRL-0014"
            and result.entity_id == "MD-0003"
            and result.status == ControlStatus.WARNING
        ):
            updated_results.append(
                result.model_copy(
                    update={
                        "status": ControlStatus.PASS,
                        "finding_code": FindingCode.CONTROL_PASSED,
                        "message": (
                            "Controlled Milestone 10 variant: high-risk model readiness review "
                            "is now tracked for MD-0003."
                        ),
                    }
                )
            )
            resolved_readiness = True
            continue
        if (
            not degraded_review_date
            and result.control_id == "CTRL-0005"
            and result.status == ControlStatus.PASS
        ):
            updated_results.append(
                result.model_copy(
                    update={
                        "status": ControlStatus.WARNING,
                        "finding_code": FindingCode.MISSING_REVIEW_DATE,
                        "message": (
                            "Controlled Milestone 10 variant: one approved active inventory "
                            "record requires review-date follow-up."
                        ),
                    }
                )
            )
            degraded_review_date = True
            continue
        updated_results.append(result)

    if not resolved_readiness or not degraded_review_date:
        raise ValueError("canonical assessment does not contain expected drift demo controls")

    results = tuple(sorted(updated_results, key=lambda result: result.result_id))
    controls = default_control_definitions()
    risk_indicators = derive_risk_indicators(
        results, controls, evaluated_at=assessment.evaluated_at
    )
    posture = derive_posture(results, risk_indicators)
    summary = build_compliance_summary(results, controls, posture)
    return assessment.model_copy(
        update={
            "assessment_id": "CA-0002",
            "control_results": results,
            "risk_indicators": risk_indicators,
            "posture": posture,
            "summary": summary,
            "limitations": (*assessment.limitations, _LIMITATIONS[1]),
        }
    )


def _control_key(result: SnapshotControlResult) -> tuple[str, str, str]:
    return (result.control_id, result.entity_type.value, result.entity_id)


def _severity_rank(severity: str) -> int:
    order = {
        ControlSeverity.LOW.value: 1,
        ControlSeverity.MEDIUM.value: 2,
        ControlSeverity.HIGH.value: 3,
        ControlSeverity.CRITICAL.value: 4,
        "missing": 0,
    }
    return order[severity]


def _status_rank(status: str) -> int:
    order = {
        "missing": -1,
        ControlStatus.PASS.value: 0,
        ControlStatus.WARNING.value: 1,
        ControlStatus.FAIL.value: 2,
    }
    return order[status]


def _control_drift_type(
    previous: SnapshotControlResult | None, current: SnapshotControlResult | None
) -> DriftType:
    if previous is None:
        return (
            DriftType.NEW_FINDING
            if current and current.status != ControlStatus.PASS
            else DriftType.DEGRADED
        )
    if current is None:
        return (
            DriftType.RESOLVED_FINDING
            if previous.status != ControlStatus.PASS
            else DriftType.IMPROVED
        )
    previous_status = previous.status.value
    current_status = current.status.value
    if previous_status == current_status and previous.finding_code == current.finding_code:
        if previous.severity == current.severity:
            return DriftType.UNCHANGED
        if _severity_rank(current.severity.value) > _severity_rank(previous.severity.value):
            return DriftType.SEVERITY_INCREASED
        return DriftType.SEVERITY_DECREASED
    if previous.status == ControlStatus.PASS and current.status != ControlStatus.PASS:
        return DriftType.NEW_FINDING
    if previous.status != ControlStatus.PASS and current.status == ControlStatus.PASS:
        return DriftType.RESOLVED_FINDING
    if _status_rank(current_status) > _status_rank(previous_status):
        return DriftType.DEGRADED
    if _status_rank(current_status) < _status_rank(previous_status):
        return DriftType.IMPROVED
    if _severity_rank(current.severity.value) > _severity_rank(previous.severity.value):
        return DriftType.SEVERITY_INCREASED
    if _severity_rank(current.severity.value) < _severity_rank(previous.severity.value):
        return DriftType.SEVERITY_DECREASED
    return (
        DriftType.DEGRADED
        if current.finding_code != FindingCode.CONTROL_PASSED
        else DriftType.IMPROVED
    )


def _representative_result(
    previous: SnapshotControlResult | None, current: SnapshotControlResult | None
) -> SnapshotControlResult:
    result = current or previous
    if result is None:
        raise ValueError("cannot build drift without a previous or current result")
    return result


def _control_explanation(
    drift_type: DriftType,
    previous: SnapshotControlResult | None,
    current: SnapshotControlResult | None,
) -> str:
    representative = _representative_result(previous, current)
    previous_status = previous.status.value if previous else "missing"
    current_status = current.status.value if current else "missing"
    return (
        f"{representative.control_id} for {representative.entity_type.value}:"
        f"{representative.entity_id} changed from {previous_status} to {current_status} "
        f"({drift_type.value})."
    )


def _first_requirement(control_catalog: ControlCatalogEntry | None) -> str:
    if control_catalog is None or not control_catalog.evidence_requirements:
        return "unmapped"
    return control_catalog.evidence_requirements[0].requirement_id


def _control_drifts(
    previous: AssuranceSnapshot,
    current: AssuranceSnapshot,
    control_catalog: tuple[ControlCatalogEntry, ...],
) -> tuple[ControlDrift, ...]:
    previous_by_key = {_control_key(result): result for result in previous.control_results}
    current_by_key = {_control_key(result): result for result in current.control_results}
    catalog_by_id = _catalog_by_control(control_catalog)
    drifts: list[ControlDrift] = []
    for key in sorted(set(previous_by_key) | set(current_by_key)):
        previous_result = previous_by_key.get(key)
        current_result = current_by_key.get(key)
        drift_type = _control_drift_type(previous_result, current_result)
        if drift_type == DriftType.UNCHANGED:
            continue
        representative = _representative_result(previous_result, current_result)
        catalog = catalog_by_id.get(representative.control_id)
        evidence_refs = tuple(
            sorted(
                set(previous_result.evidence_refs if previous_result else ())
                | set(current_result.evidence_refs if current_result else ())
            )
        )
        drifts.append(
            ControlDrift(
                drift_id=f"CD-{len(drifts) + 1:04d}",
                control_id=representative.control_id,
                policy_ids=representative.policy_ids,
                control_objective=representative.control_objective,
                previous_status=previous_result.status.value if previous_result else "missing",
                current_status=current_result.status.value if current_result else "missing",
                previous_finding_code=previous_result.finding_code.value if previous_result else "",
                current_finding_code=current_result.finding_code.value if current_result else "",
                severity=current_result.severity if current_result else previous_result.severity,
                previous_severity=previous_result.severity.value if previous_result else "missing",
                current_severity=current_result.severity.value if current_result else "missing",
                drift_type=drift_type,
                entity_type=representative.entity_type.value,
                entity_id=representative.entity_id,
                evidence_refs=evidence_refs,
                evidence_requirement=_first_requirement(catalog),
                reviewer_guidance=representative.reviewer_guidance,
                explanation=_control_explanation(drift_type, previous_result, current_result),
            )
        )
    return tuple(drifts)


def _non_pass_scores(snapshot: AssuranceSnapshot) -> dict[str, tuple[int, tuple[str, ...]]]:
    scores: dict[str, int] = {}
    refs: dict[str, set[str]] = {}
    for result in snapshot.control_results:
        if result.status == ControlStatus.PASS:
            continue
        category = result.policy_ids[0]
        score = {
            ControlSeverity.LOW: 1,
            ControlSeverity.MEDIUM: 3,
            ControlSeverity.HIGH: 5,
            ControlSeverity.CRITICAL: 8,
        }[result.severity]
        scores[category] = scores.get(category, 0) + score
        refs.setdefault(category, set()).update(result.evidence_refs)
    return {key: (scores[key], tuple(sorted(refs[key]))) for key in sorted(scores)}


def _risk_drift_type(previous_score: int, current_score: int) -> DriftType:
    if current_score > previous_score:
        return DriftType.DEGRADED
    if current_score < previous_score:
        return DriftType.IMPROVED
    return DriftType.UNCHANGED


def _risk_severity(delta: int) -> ControlSeverity:
    absolute = abs(delta)
    if absolute >= 8:
        return ControlSeverity.CRITICAL
    if absolute >= 5:
        return ControlSeverity.HIGH
    if absolute >= 3:
        return ControlSeverity.MEDIUM
    return ControlSeverity.LOW


def _risk_drifts(previous: AssuranceSnapshot, current: AssuranceSnapshot) -> tuple[RiskDrift, ...]:
    previous_scores = _non_pass_scores(previous)
    current_scores = _non_pass_scores(current)
    rows: list[RiskDrift] = []
    for category in sorted(set(previous_scores) | set(current_scores)):
        previous_score, previous_refs = previous_scores.get(category, (0, ()))
        current_score, current_refs = current_scores.get(category, (0, ()))
        delta = current_score - previous_score
        drift_type = _risk_drift_type(previous_score, current_score)
        if drift_type == DriftType.UNCHANGED:
            continue
        rows.append(
            RiskDrift(
                drift_id=f"RD-{len(rows) + 1:04d}",
                category=category,
                previous_score=previous_score,
                current_score=current_score,
                score_delta=delta,
                severity=_risk_severity(delta),
                drift_type=drift_type,
                explanation=(
                    f"{category} bounded risk contribution changed from "
                    f"{previous_score} to {current_score}."
                ),
                evidence_refs=tuple(sorted(set(previous_refs) | set(current_refs))),
            )
        )
    total_delta = current.bounded_risk_score - previous.bounded_risk_score
    if total_delta:
        rows.append(
            RiskDrift(
                drift_id=f"RD-{len(rows) + 1:04d}",
                category="total_bounded_risk_score",
                previous_score=previous.bounded_risk_score,
                current_score=current.bounded_risk_score,
                score_delta=total_delta,
                severity=_risk_severity(total_delta),
                drift_type=_risk_drift_type(
                    previous.bounded_risk_score, current.bounded_risk_score
                ),
                explanation=(
                    "Total bounded risk score changed from "
                    f"{previous.bounded_risk_score} to {current.bounded_risk_score}."
                ),
                evidence_refs=tuple(
                    sorted(
                        {ref for result in previous.control_results for ref in result.evidence_refs}
                        | {
                            ref
                            for result in current.control_results
                            for ref in result.evidence_refs
                        }
                    )
                ),
            )
        )
    return tuple(rows)


def _posture_rank(posture: GovernancePosture) -> int:
    return {
        GovernancePosture.HEALTHY: 0,
        GovernancePosture.ATTENTION_REQUIRED: 1,
        GovernancePosture.HIGH_RISK: 2,
    }[posture]


def _posture_change(previous: GovernancePosture, current: GovernancePosture) -> DriftType:
    if previous == current:
        return DriftType.UNCHANGED
    if _posture_rank(current) > _posture_rank(previous):
        return DriftType.POSTURE_DEGRADED
    return DriftType.POSTURE_IMPROVED


def _changed_domains(drifts: tuple[ControlDrift, ...]) -> tuple[str, ...]:
    domains: set[str] = set()
    for drift in drifts:
        policy_id = drift.policy_ids[0] if drift.policy_ids else ""
        if policy_id:
            domains.add(policy_id)
    return tuple(sorted(domains))


def compare_assurance_snapshots(
    previous: AssuranceSnapshot,
    current: AssuranceSnapshot,
    control_catalog: tuple[ControlCatalogEntry, ...],
    *,
    comparison_id: str = "AC-0001",
    compared_at: datetime = _COMPARISON_COMPARED_AT,
) -> AssuranceComparison:
    """Compare two explicit snapshots and return reviewer-facing drift."""
    if previous.snapshot_id == current.snapshot_id:
        raise ValueError("cannot compare a snapshot to itself")
    control_drifts = _control_drifts(previous, current, control_catalog)
    risk_drifts = _risk_drifts(previous, current)
    total_controls_compared = len(
        {
            (result.control_id, result.entity_type.value, result.entity_id)
            for result in previous.control_results
        }
        | {
            (result.control_id, result.entity_type.value, result.entity_id)
            for result in current.control_results
        }
    )
    summary = {
        "total_controls_compared": total_controls_compared,
        "unchanged_controls": total_controls_compared - len(control_drifts),
        "improved_controls": sum(
            1
            for drift in control_drifts
            if drift.drift_type in {DriftType.IMPROVED, DriftType.RESOLVED_FINDING}
        ),
        "degraded_controls": sum(
            1
            for drift in control_drifts
            if drift.drift_type in {DriftType.DEGRADED, DriftType.NEW_FINDING}
        ),
        "new_findings": sum(
            1 for drift in control_drifts if drift.drift_type == DriftType.NEW_FINDING
        ),
        "resolved_findings": sum(
            1 for drift in control_drifts if drift.drift_type == DriftType.RESOLVED_FINDING
        ),
        "severity_changes": sum(
            1
            for drift in control_drifts
            if drift.drift_type in {DriftType.SEVERITY_INCREASED, DriftType.SEVERITY_DECREASED}
        ),
        "risk_score_delta": current.bounded_risk_score - previous.bounded_risk_score,
        "posture_transition": f"{previous.posture.value}->{current.posture.value}",
        "changed_governance_domains": _changed_domains(control_drifts),
    }
    return AssuranceComparison(
        comparison_id=comparison_id,
        previous_snapshot_id=previous.snapshot_id,
        current_snapshot_id=current.snapshot_id,
        compared_at=compared_at,
        previous_posture=previous.posture,
        current_posture=current.posture,
        previous_bounded_risk_score=previous.bounded_risk_score,
        current_bounded_risk_score=current.bounded_risk_score,
        risk_score_delta=current.bounded_risk_score - previous.bounded_risk_score,
        control_drifts=control_drifts,
        risk_drifts=risk_drifts,
        posture_change=_posture_change(previous.posture, current.posture),
        summary=summary,
        limitations=_LIMITATIONS,
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def build_assurance_history_bundle(
    assessment: ComplianceAssessment,
    control_catalog: tuple[ControlCatalogEntry, ...],
) -> AssuranceHistoryBundle:
    """Build the canonical baseline plus controlled comparison history bundle."""
    baseline = build_assurance_snapshot(
        assessment,
        control_catalog,
        snapshot_id="AS-0001",
        captured_at=_BASELINE_CAPTURED_AT,
    )
    comparison_assessment = build_controlled_comparison_assessment(assessment)
    comparison_snapshot = build_assurance_snapshot(
        comparison_assessment,
        control_catalog,
        snapshot_id="AS-0002",
        captured_at=_COMPARISON_CAPTURED_AT,
        source_refs=(
            "outputs/compliance/compliance_summary.json",
            "outputs/policy/control_catalog.json",
            "controlled_variant:milestone_10_assurance_drift",
        ),
    )
    history = AssuranceHistory(snapshots=(baseline, comparison_snapshot))
    previous, current = history.prior_current_pair()
    comparison = compare_assurance_snapshots(previous, current, control_catalog)
    return AssuranceHistoryBundle(history=history, comparison=comparison)


def _control_drift_rows(drifts: tuple[ControlDrift, ...]) -> tuple[dict[str, object], ...]:
    return tuple(drift.model_dump(mode="json") for drift in drifts)


def _risk_drift_rows(drifts: tuple[RiskDrift, ...]) -> tuple[dict[str, object], ...]:
    return tuple(drift.model_dump(mode="json") for drift in drifts)


def render_assurance_drift_report(comparison: AssuranceComparison) -> str:
    """Render concise reviewer-facing assurance drift report."""
    lines: list[str] = [
        "# Assurance Drift Report",
        "",
        "> Local deterministic comparison of explicit synthetic assurance snapshots. This is "
        "not live monitoring, alerting, production observability, or regulatory certification.",
        "",
        f"- **Comparison ID:** {comparison.comparison_id}",
        f"- **Prior snapshot:** {comparison.previous_snapshot_id}",
        f"- **Current snapshot:** {comparison.current_snapshot_id}",
        f"- **Compared at:** {comparison.compared_at.isoformat()}",
        f"- **Posture transition:** {comparison.summary['posture_transition']}",
        f"- **Risk score delta:** {comparison.risk_score_delta}",
        "",
        "## Summary Metrics",
        "",
    ]
    for key, value in comparison.summary.items():
        lines.append(f"- **{key}:** {_csv_value(value)}")
    lines.extend(["", "## Control Changes", ""])
    if comparison.control_drifts:
        for drift in comparison.control_drifts:
            refs = ", ".join(drift.evidence_refs) if drift.evidence_refs else "none"
            lines.append(
                f"- **{drift.drift_id} {drift.control_id}:** {drift.drift_type.value}; "
                f"{drift.previous_status} -> {drift.current_status}; "
                f"policy {', '.join(drift.policy_ids)}; evidence {refs}"
            )
    else:
        lines.append("No changed controls were identified.")
    lines.extend(["", "## Risk Changes", ""])
    if comparison.risk_drifts:
        for drift in comparison.risk_drifts:
            lines.append(
                f"- **{drift.drift_id} {drift.category}:** {drift.previous_score} -> "
                f"{drift.current_score} ({drift.score_delta:+d}); {drift.drift_type.value}"
            )
    else:
        lines.append("No risk-score changes were identified.")
    lines.extend(["", "## Reviewer Interpretation", ""])
    lines.append(
        "- Treat drift rows as review prompts that link back to compliance results, policy "
        "catalog metadata, and evidence references."
    )
    lines.append(
        "- The controlled comparison snapshot is intentionally small so reviewers can inspect "
        "both resolved and new findings without changing canonical governance outputs."
    )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in comparison.limitations)
    lines.append("")
    return "\n".join(lines)


def export_assurance_history_bundle(bundle: AssuranceHistoryBundle, output_dir: str | Path) -> None:
    """Export assurance history artifacts in deterministic JSON/CSV/Markdown form."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    comparison = bundle.comparison

    _write_json(
        out / ASSURANCE_SNAPSHOTS_JSON_FILENAME,
        [snapshot.model_dump(mode="json") for snapshot in bundle.history.ordered_snapshots()],
    )
    _write_json(out / ASSURANCE_COMPARISON_JSON_FILENAME, comparison.model_dump(mode="json"))
    _write_csv(
        out / CONTROL_DRIFT_CSV_FILENAME,
        (
            "drift_id",
            "control_id",
            "policy_ids",
            "control_objective",
            "previous_status",
            "current_status",
            "previous_finding_code",
            "current_finding_code",
            "severity",
            "previous_severity",
            "current_severity",
            "drift_type",
            "entity_type",
            "entity_id",
            "evidence_refs",
            "evidence_requirement",
            "reviewer_guidance",
            "explanation",
        ),
        _control_drift_rows(comparison.control_drifts),
    )
    _write_csv(
        out / RISK_DRIFT_CSV_FILENAME,
        (
            "drift_id",
            "category",
            "previous_score",
            "current_score",
            "score_delta",
            "severity",
            "drift_type",
            "explanation",
            "evidence_refs",
        ),
        _risk_drift_rows(comparison.risk_drifts),
    )
    _write_json(out / ASSURANCE_DRIFT_SUMMARY_JSON_FILENAME, comparison.summary)
    (out / ASSURANCE_DRIFT_REPORT_MARKDOWN_FILENAME).write_text(
        render_assurance_drift_report(comparison), encoding="utf-8"
    )


def load_assurance_history(input_dir: str | Path) -> AssuranceHistory:
    """Load canonical assurance snapshot history JSON."""
    path = Path(input_dir) / ASSURANCE_SNAPSHOTS_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Assurance snapshots file not found: {path}")
    return AssuranceHistory(
        snapshots=tuple(
            AssuranceSnapshot.model_validate(item)
            for item in json.loads(path.read_text(encoding="utf-8"))
        )
    )


def load_assurance_comparison(input_dir: str | Path) -> AssuranceComparison:
    """Load canonical assurance comparison JSON."""
    path = Path(input_dir) / ASSURANCE_COMPARISON_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Assurance comparison file not found: {path}")
    return AssuranceComparison.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_assurance_history_files(input_dir: str | Path) -> list[str]:
    """Validate exported assurance history files without raising."""
    root = Path(input_dir)
    problems: list[str] = []
    for filename in ASSURANCE_OUTPUT_FILENAMES:
        if not (root / filename).is_file():
            problems.append(f"missing assurance output: {root / filename}")
    try:
        history = load_assurance_history(root)
        comparison = load_assurance_comparison(root)
        previous, current = history.prior_current_pair()
        if comparison.previous_snapshot_id != previous.snapshot_id:
            problems.append("comparison previous snapshot does not match ordered history")
        if comparison.current_snapshot_id != current.snapshot_id:
            problems.append("comparison current snapshot does not match ordered history")
    except (FileNotFoundError, ValueError) as exc:
        problems.append(str(exc))
    return problems
