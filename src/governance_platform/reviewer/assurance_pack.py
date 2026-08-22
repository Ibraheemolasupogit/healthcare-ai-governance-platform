"""Integrated assurance review pack over canonical reviewer outputs.

Milestone 11 aggregates existing generated governance artifacts for handoff.
It does not evaluate controls, score risk, generate evidence, or calculate
assurance drift.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.compliance import (
    AssuranceComparison,
    ControlCatalogEntry,
    ControlSeverity,
    ControlStatus,
    PolicyAssuranceSummary,
    PolicyDefinition,
)
from governance_platform.reviewer.data import ReviewerState
from governance_platform.reviewer.exports import (
    EvidenceIndexEntry,
    ReviewerBriefing,
    build_reviewer_evidence_index,
    load_reviewer_briefing,
)

ASSURANCE_REVIEW_PACK_JSON_FILENAME = "assurance_review_pack.json"
PRIORITY_FINDINGS_CSV_FILENAME = "priority_findings.csv"
REVIEWER_ACTIONS_CSV_FILENAME = "reviewer_actions.csv"
ASSURANCE_EVIDENCE_MAP_CSV_FILENAME = "assurance_evidence_map.csv"
ASSURANCE_REVIEW_PACK_MARKDOWN_FILENAME = "assurance_review_pack.md"

ASSURANCE_PACK_OUTPUT_FILENAMES: tuple[str, ...] = (
    ASSURANCE_REVIEW_PACK_JSON_FILENAME,
    PRIORITY_FINDINGS_CSV_FILENAME,
    REVIEWER_ACTIONS_CSV_FILENAME,
    ASSURANCE_EVIDENCE_MAP_CSV_FILENAME,
    ASSURANCE_REVIEW_PACK_MARKDOWN_FILENAME,
)

_LIST_FIELD_SEPARATOR = ";"
_GENERATED_AT = datetime(2025, 3, 23, 0, 0, 0)
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "": 4}
_STATUS_RANK = {"fail": 0, "warning": 1, "risk_indicator": 2, "resolved": 3, "pass": 4}
_DRIFT_RANK = {
    "degraded": 0,
    "new_finding": 1,
    "severity_increased": 2,
    "improved": 3,
    "resolved_finding": 4,
    "unchanged": 5,
    "": 6,
}


class ReviewerActionPriority(str, Enum):
    """Reviewer action priority labels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PriorityFinding(BaseModel):
    """One reviewer-prioritized finding with policy/control/evidence/drift links."""

    model_config = {"frozen": True, "extra": "forbid"}

    finding_id: str = Field(pattern=r"^PF-\d{4}$")
    title: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    status: str = Field(min_length=1)
    control_id: str
    policy_ids: tuple[str, ...] = ()
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence_refs: tuple[str, ...]
    drift_status: str = ""
    drift_id: str = ""
    reviewer_location: str = Field(min_length=1)
    reviewer_guidance: str = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("priority findings must include evidence references")
        return value


class ReviewerAction(BaseModel):
    """A reviewer next step, not a remediation workflow."""

    model_config = {"frozen": True, "extra": "forbid"}

    action_id: str = Field(pattern=r"^RA-\d{4}$")
    priority: ReviewerActionPriority
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    related_control_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...]
    reviewer_location: str = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("reviewer actions must include evidence references")
        return value


class AssuranceReviewPack(BaseModel):
    """Concise integrated assurance review package."""

    model_config = {"frozen": True, "extra": "forbid"}

    pack_id: str = Field(pattern=r"^ARP-\d{4}$")
    generated_at: datetime
    scope: str = Field(min_length=1)
    governance_posture: str = Field(min_length=1)
    bounded_risk_score: int = Field(ge=0, le=100)
    inventory_summary: dict[str, Any]
    access_summary: dict[str, Any]
    audit_summary: dict[str, Any]
    compliance_summary: dict[str, Any]
    policy_summary: dict[str, Any]
    assurance_drift_summary: dict[str, Any]
    priority_findings: tuple[PriorityFinding, ...]
    evidence_index: tuple[dict[str, Any], ...]
    reviewer_actions: tuple[ReviewerAction, ...]
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

    @field_validator("assurance_drift_summary", mode="before")
    @classmethod
    def _drift_summary_domains_are_tuple(cls, value: dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, dict) and isinstance(value.get("changed_governance_domains"), list):
            return {
                **value,
                "changed_governance_domains": tuple(value["changed_governance_domains"]),
            }
        return value

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> AssuranceReviewPack:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError(
                "assurance review pack must preserve synthetic/local/non-production flags"
            )
        return self


class AssuranceReviewPackBundle(BaseModel):
    """Validated in-memory assurance pack export bundle."""

    model_config = {"frozen": True, "extra": "forbid"}

    pack: AssuranceReviewPack
    evidence_map_rows: tuple[dict[str, Any], ...]


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


def _split_refs(value: Any) -> tuple[str, ...]:
    if value in ("", None):
        return ()
    if isinstance(value, tuple | list):
        return tuple(str(item) for item in value if str(item))
    return tuple(ref.strip() for ref in str(value).split(";") if ref.strip())


def _control_by_id(
    controls: tuple[ControlCatalogEntry, ...],
) -> dict[str, ControlCatalogEntry]:
    return {control.control_id: control for control in controls}


def _policy_by_id(policies: tuple[PolicyDefinition, ...]) -> dict[str, PolicyDefinition]:
    return {policy.policy_id: policy for policy in policies}


def _drift_by_control_entity(comparison: AssuranceComparison) -> dict[tuple[str, str, str], Any]:
    return {
        (drift.control_id, drift.entity_type, drift.entity_id): drift
        for drift in comparison.control_drifts
    }


def _matching_current_control(
    state: ReviewerState, risk_indicator: dict[str, Any]
) -> dict[str, Any] | None:
    refs = set(_split_refs(risk_indicator.get("evidence_refs")))
    for result in state.control_result_rows:
        if result["status"] == "pass":
            continue
        if result["entity_type"] == risk_indicator["entity_type"] and (
            result["entity_id"] == risk_indicator["entity_id"]
            or refs.intersection(_split_refs(result.get("evidence_refs")))
        ):
            return result
    return None


def _finding_sort_key(finding: PriorityFinding) -> tuple[int, int, int, str, str]:
    return (
        _STATUS_RANK.get(finding.status, 9),
        _DRIFT_RANK.get(finding.drift_status, 9),
        _SEVERITY_RANK.get(finding.severity, 9),
        finding.control_id,
        finding.finding_id,
    )


def _reviewer_location_for_control(result_id: str) -> str:
    return f"Compliance & Risk -> Control Results -> {result_id}"


def build_priority_findings(
    state: ReviewerState,
    controls: tuple[ControlCatalogEntry, ...],
    comparison: AssuranceComparison,
) -> tuple[PriorityFinding, ...]:
    """Build deterministic priority findings from current findings and drift outputs."""
    controls_by_id = _control_by_id(controls)
    drift_lookup = _drift_by_control_entity(comparison)
    findings: list[PriorityFinding] = []
    seen_drift_ids: set[str] = set()

    for result in state.control_result_rows:
        if result["status"] == ControlStatus.PASS.value:
            continue
        control = controls_by_id[result["control_id"]]
        drift = drift_lookup.get((result["control_id"], result["entity_type"], result["entity_id"]))
        findings.append(
            PriorityFinding(
                finding_id="PF-0000",
                title=f"{result['control_id']} {result['status']} for {result['entity_id']}",
                domain=control.control_domain.value,
                severity=result["severity"],
                status=result["status"],
                control_id=result["control_id"],
                policy_ids=control.policy_ids,
                entity_type=result["entity_type"],
                entity_id=result["entity_id"],
                rationale=result["message"],
                evidence_refs=_split_refs(result["evidence_refs"]),
                drift_status=drift.drift_type.value if drift else "",
                drift_id=drift.drift_id if drift else "",
                reviewer_location=_reviewer_location_for_control(result["result_id"]),
                reviewer_guidance=control.reviewer_guidance,
            )
        )
        if drift:
            seen_drift_ids.add(drift.drift_id)

    for indicator in state.risk_indicator_rows:
        matched = _matching_current_control(state, indicator)
        control_id = matched["control_id"] if matched else ""
        control = controls_by_id.get(control_id)
        drift = (
            drift_lookup.get((control_id, indicator["entity_type"], indicator["entity_id"]))
            if control_id
            else None
        )
        findings.append(
            PriorityFinding(
                finding_id="PF-0000",
                title=f"{indicator['indicator_id']} bounded risk indicator",
                domain=indicator["category"],
                severity=indicator["severity"],
                status="risk_indicator",
                control_id=control_id,
                policy_ids=control.policy_ids if control else (),
                entity_type=indicator["entity_type"],
                entity_id=indicator["entity_id"],
                rationale=indicator["rationale"],
                evidence_refs=_split_refs(indicator["evidence_refs"]),
                drift_status=drift.drift_type.value if drift else "",
                drift_id=drift.drift_id if drift else "",
                reviewer_location=(
                    f"Compliance & Risk -> Risk Indicators -> {indicator['indicator_id']}"
                ),
                reviewer_guidance=(
                    control.reviewer_guidance
                    if control
                    else "Inspect the linked risk indicator and evidence references."
                ),
            )
        )
        if drift:
            seen_drift_ids.add(drift.drift_id)

    for drift in comparison.control_drifts:
        if drift.drift_id in seen_drift_ids:
            continue
        status = (
            "resolved" if drift.current_status == ControlStatus.PASS.value else drift.current_status
        )
        if drift.current_status != ControlStatus.PASS.value:
            title = f"{drift.control_id} {drift.drift_type.value} for {drift.entity_id}"
        else:
            title = f"{drift.control_id} resolved for {drift.entity_id}"
        findings.append(
            PriorityFinding(
                finding_id="PF-0000",
                title=title,
                domain=drift.policy_ids[0],
                severity=drift.severity.value,
                status=status,
                control_id=drift.control_id,
                policy_ids=drift.policy_ids,
                entity_type=drift.entity_type,
                entity_id=drift.entity_id,
                rationale=drift.explanation,
                evidence_refs=drift.evidence_refs,
                drift_status=drift.drift_type.value,
                drift_id=drift.drift_id,
                reviewer_location=(
                    f"Assurance History / Drift -> Changed Controls -> {drift.drift_id}"
                ),
                reviewer_guidance=drift.reviewer_guidance,
            )
        )

    ordered = sorted(findings, key=_finding_sort_key)
    return tuple(
        finding.model_copy(update={"finding_id": f"PF-{index:04d}"})
        for index, finding in enumerate(ordered, start=1)
    )


def _action_priority(finding: PriorityFinding) -> ReviewerActionPriority:
    if finding.status == ControlStatus.FAIL.value or finding.severity in {
        ControlSeverity.CRITICAL.value,
        ControlSeverity.HIGH.value,
    }:
        return ReviewerActionPriority.HIGH
    if finding.status in {ControlStatus.WARNING.value, "risk_indicator"}:
        return ReviewerActionPriority.MEDIUM
    return ReviewerActionPriority.LOW


def build_reviewer_actions(findings: tuple[PriorityFinding, ...]) -> tuple[ReviewerAction, ...]:
    """Build concise review-only next steps from priority findings."""
    actions: list[ReviewerAction] = []
    for finding in findings:
        if finding.status == "resolved":
            title = f"Inspect resolved drift for {finding.control_id}"
            description = (
                "Confirm the resolved finding is reflected in the assurance drift report and "
                "linked evidence references."
            )
            location = f"Assurance History / Drift -> Changed Controls -> {finding.drift_id}"
        elif finding.control_id == "CTRL-0014":
            title = "Confirm responsible-AI readiness evidence"
            description = (
                "Inspect the high-risk model readiness control, model evidence, and policy "
                "catalog guidance before accepting the current posture."
            )
            location = finding.reviewer_location
        elif finding.control_id:
            title = f"Review {finding.control_id} evidence"
            description = (
                "Inspect the linked control result, policy catalog row, evidence references, "
                "and any assurance drift context."
            )
            location = finding.reviewer_location
        else:
            title = f"Inspect {finding.finding_id} evidence"
            description = "Inspect the linked evidence references and related risk indicator."
            location = finding.reviewer_location
        actions.append(
            ReviewerAction(
                action_id=f"RA-{len(actions) + 1:04d}",
                priority=_action_priority(finding),
                title=title,
                description=description,
                related_control_ids=(finding.control_id,) if finding.control_id else (),
                evidence_refs=finding.evidence_refs,
                reviewer_location=location,
            )
        )
    return tuple(actions)


def _limited_evidence_index(
    findings: tuple[PriorityFinding, ...],
    evidence_index: tuple[EvidenceIndexEntry, ...],
) -> tuple[dict[str, Any], ...]:
    used_refs = {ref for finding in findings for ref in finding.evidence_refs}
    by_ref = {entry.evidence_ref: entry for entry in evidence_index}
    return tuple(by_ref[ref].model_dump(mode="json") for ref in sorted(used_refs) if ref in by_ref)


def build_assurance_evidence_map(
    pack: AssuranceReviewPack,
    evidence_index: tuple[EvidenceIndexEntry, ...],
) -> tuple[dict[str, Any], ...]:
    """Build compact finding-to-evidence traceability rows."""
    by_ref = {entry.evidence_ref: entry for entry in evidence_index}
    rows: list[dict[str, Any]] = []
    for finding in pack.priority_findings:
        for evidence_ref in finding.evidence_refs:
            entry = by_ref.get(evidence_ref)
            if entry is None:
                raise ValueError(
                    f"assurance pack evidence reference does not resolve: {evidence_ref}"
                )
            for policy_id in finding.policy_ids or ("",):
                rows.append(
                    {
                        "finding_id": finding.finding_id,
                        "control_id": finding.control_id,
                        "policy_id": policy_id,
                        "entity_id": finding.entity_id,
                        "evidence_ref": evidence_ref,
                        "source_plane": entry.source_plane,
                        "source_file": entry.source_file,
                        "drift_id": finding.drift_id,
                        "reviewer_location": finding.reviewer_location,
                    }
                )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row["finding_id"],
                row["control_id"],
                row["policy_id"],
                row["evidence_ref"],
            ),
        )
    )


def build_assurance_review_pack(
    state: ReviewerState,
    briefing: ReviewerBriefing,
    policies: tuple[PolicyDefinition, ...],
    controls: tuple[ControlCatalogEntry, ...],
    policy_summary: PolicyAssuranceSummary,
    comparison: AssuranceComparison,
    *,
    evidence_index: tuple[EvidenceIndexEntry, ...] | None = None,
) -> AssuranceReviewPackBundle:
    """Build the integrated assurance review pack from canonical source outputs."""
    evidence_entries = evidence_index or build_reviewer_evidence_index(state)
    findings = build_priority_findings(state, controls, comparison)
    actions = build_reviewer_actions(findings)
    policy_by_id = _policy_by_id(policies)
    source_refs = (
        "outputs/reviewer/reviewer_briefing.json",
        "outputs/reviewer/reviewer_evidence_index.csv",
        "outputs/policy/policy_catalog.json",
        "outputs/policy/control_catalog.json",
        "outputs/policy/control_evidence_traceability.csv",
        "outputs/assurance/assurance_comparison.json",
    )
    pack = AssuranceReviewPack(
        pack_id="ARP-0001",
        generated_at=_GENERATED_AT,
        scope=(
            "Integrated local assurance review over generated synthetic governance outputs, "
            "policy/control catalog, evidence index, and assurance drift."
        ),
        governance_posture=briefing.governance_posture,
        bounded_risk_score=briefing.bounded_risk_score,
        inventory_summary=briefing.inventory_metrics,
        access_summary=briefing.access_metrics,
        audit_summary=briefing.audit_evidence_metrics,
        compliance_summary=briefing.compliance_risk_metrics,
        policy_summary={
            "policy_count": policy_summary.policy_count,
            "control_count": policy_summary.control_count,
            "evidence_requirement_count": policy_summary.evidence_requirement_count,
            "traceability_row_count": policy_summary.traceability_row_count,
            "current_warning_results": policy_summary.evaluation_status_counts.get("warning", 0),
            "current_failed_results": policy_summary.evaluation_status_counts.get("fail", 0),
            "affected_policy_names": {
                policy_id: policy_by_id[policy_id].name
                for finding in findings
                for policy_id in finding.policy_ids
                if policy_id in policy_by_id
            },
        },
        assurance_drift_summary={
            **comparison.summary,
            "comparison_id": comparison.comparison_id,
            "previous_snapshot_id": comparison.previous_snapshot_id,
            "current_snapshot_id": comparison.current_snapshot_id,
            "posture_change": comparison.posture_change.value,
            "control_drift_count": len(comparison.control_drifts),
            "risk_drift_count": len(comparison.risk_drifts),
        },
        priority_findings=findings,
        evidence_index=_limited_evidence_index(findings, evidence_entries),
        reviewer_actions=actions,
        source_refs=source_refs,
        limitations=(
            *briefing.limitations,
            "Integrated assurance pack is reviewer handoff only, not remediation execution.",
            "No live monitoring, workflow automation, notifications, or external "
            "integrations exist.",
        ),
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )
    evidence_map = build_assurance_evidence_map(pack, evidence_entries)
    return AssuranceReviewPackBundle(pack=pack, evidence_map_rows=evidence_map)


def render_assurance_review_pack_markdown(pack: AssuranceReviewPack) -> str:
    """Render a concise reviewer-readable assurance review pack."""
    lines: list[str] = [
        "# Assurance Review Pack",
        "",
        "> Local deterministic assurance handoff over generated synthetic outputs only. This is "
        "not live monitoring, workflow automation, remediation, or regulatory certification.",
        "",
        "## Executive Summary",
        "",
        f"- **Pack ID:** {pack.pack_id}",
        f"- **Generated at:** {pack.generated_at.isoformat()}",
        f"- **Governance posture:** {pack.governance_posture}",
        f"- **Bounded risk score:** {pack.bounded_risk_score}",
        f"- **Priority findings:** {len(pack.priority_findings)}",
        f"- **Reviewer actions:** {len(pack.reviewer_actions)}",
        "",
        "## Current Governance Posture",
        "",
        f"- Posture: {pack.governance_posture}",
        f"- Bounded risk score: {pack.bounded_risk_score}",
        f"- Control warnings: {pack.compliance_summary.get('control_warnings', 0)}",
        f"- Control failures: {pack.compliance_summary.get('control_failures', 0)}",
        "",
        "## Key Metrics",
        "",
    ]
    for group in _summary_groups_from_pack(pack):
        lines.extend(f"- **{key}:** {value}" for key, value in group.items())
    lines.extend(["", "## Priority Findings", ""])
    if pack.priority_findings:
        for finding in pack.priority_findings:
            refs = ", ".join(finding.evidence_refs)
            policies = ", ".join(finding.policy_ids) if finding.policy_ids else "none"
            drift = finding.drift_id or "none"
            lines.append(
                f"- **{finding.finding_id}:** {finding.title} "
                f"({finding.status}/{finding.severity}); control {finding.control_id or 'none'}; "
                f"policies {policies}; drift {drift}; evidence {refs}"
            )
    else:
        lines.append("No priority findings were derived from current source outputs.")
    lines.extend(["", "## Policy & Control Coverage", ""])
    for key, value in pack.policy_summary.items():
        if key != "affected_policy_names":
            lines.append(f"- **{key}:** {_csv_value(value)}")
    lines.extend(["", "## Evidence Traceability", ""])
    for entry in pack.evidence_index:
        lines.append(
            f"- **{entry['evidence_ref']}:** {entry['source_plane']} -> {entry['source_file']}"
        )
    lines.extend(["", "## Assurance Drift", ""])
    for key, value in pack.assurance_drift_summary.items():
        lines.append(f"- **{key}:** {_csv_value(value)}")
    lines.extend(["", "## Reviewer Actions", ""])
    for action in pack.reviewer_actions:
        lines.append(
            f"- **{action.action_id} ({action.priority.value}):** {action.title} — "
            f"{action.description}"
        )
    lines.extend(["", "## Source Artifacts", ""])
    lines.extend(f"- {source_ref}" for source_ref in pack.source_refs)
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in pack.limitations)
    lines.append("")
    return "\n".join(lines)


def _summary_groups_from_pack(pack: AssuranceReviewPack) -> tuple[dict[str, Any], ...]:
    return (
        pack.inventory_summary,
        pack.access_summary,
        pack.audit_summary,
        pack.compliance_summary,
    )


def export_assurance_review_pack_bundle(
    bundle: AssuranceReviewPackBundle, output_dir: str | Path
) -> dict[str, int | str | Path]:
    """Export the integrated assurance review pack."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pack = bundle.pack

    _write_json(out / ASSURANCE_REVIEW_PACK_JSON_FILENAME, pack.model_dump(mode="json"))
    _write_csv(
        out / PRIORITY_FINDINGS_CSV_FILENAME,
        (
            "finding_id",
            "title",
            "domain",
            "severity",
            "status",
            "control_id",
            "policy_ids",
            "entity_type",
            "entity_id",
            "rationale",
            "evidence_refs",
            "drift_status",
            "drift_id",
            "reviewer_location",
            "reviewer_guidance",
        ),
        tuple(finding.model_dump(mode="json") for finding in pack.priority_findings),
    )
    _write_csv(
        out / REVIEWER_ACTIONS_CSV_FILENAME,
        (
            "action_id",
            "priority",
            "title",
            "description",
            "related_control_ids",
            "evidence_refs",
            "reviewer_location",
        ),
        tuple(action.model_dump(mode="json") for action in pack.reviewer_actions),
    )
    _write_csv(
        out / ASSURANCE_EVIDENCE_MAP_CSV_FILENAME,
        (
            "finding_id",
            "control_id",
            "policy_id",
            "entity_id",
            "evidence_ref",
            "source_plane",
            "source_file",
            "drift_id",
            "reviewer_location",
        ),
        bundle.evidence_map_rows,
    )
    (out / ASSURANCE_REVIEW_PACK_MARKDOWN_FILENAME).write_text(
        render_assurance_review_pack_markdown(pack), encoding="utf-8"
    )
    return {
        "output_dir": out,
        "pack_id": pack.pack_id,
        "priority_finding_count": len(pack.priority_findings),
        "reviewer_action_count": len(pack.reviewer_actions),
        "evidence_map_row_count": len(bundle.evidence_map_rows),
    }


def load_assurance_review_pack(input_dir: str | Path) -> AssuranceReviewPack:
    """Load canonical assurance review pack JSON."""
    path = Path(input_dir) / ASSURANCE_REVIEW_PACK_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Assurance review pack file not found: {path}")
    return AssuranceReviewPack.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_assurance_review_pack(input_dir: str | Path) -> list[str]:
    """Validate assurance review pack files without raising."""
    root = Path(input_dir)
    problems: list[str] = []
    for filename in ASSURANCE_PACK_OUTPUT_FILENAMES:
        if not (root / filename).is_file():
            problems.append(f"missing assurance pack output: {root / filename}")
    try:
        load_assurance_review_pack(root)
    except (FileNotFoundError, ValueError) as exc:
        problems.append(str(exc))
    return problems


def load_reviewer_briefing_for_pack(outputs_root: str | Path) -> ReviewerBriefing:
    """Load the reviewer briefing from the standard output root."""
    return load_reviewer_briefing(Path(outputs_root) / "reviewer")
