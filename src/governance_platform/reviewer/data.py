"""UI-facing data access for the local governance reviewer portal.

This module reads canonical generated outputs and prepares deterministic,
reviewer-friendly rows. It contains no Streamlit dependency, so filtering and
drill-through behavior can be tested without exercising UI internals.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from governance_platform.access import AccessControlService, load_access_state
from governance_platform.audit import load_audit_log, load_evidence_pack
from governance_platform.compliance import (
    load_assurance_comparison,
    load_assurance_history,
    load_compliance_assessment,
    load_control_catalog,
    load_policy_assurance_summary,
    load_policy_catalog,
)
from governance_platform.inventory import load_portfolio
from governance_platform.reporting import GovernanceKPI, ReportingSnapshot, load_reporting_snapshot

REQUIRED_GENERATION_COMMANDS: tuple[str, ...] = (
    "python3 scripts/generate_inventory.py",
    "python3 scripts/generate_access.py",
    "python3 scripts/generate_evidence.py",
    "python3 scripts/generate_compliance.py",
    "python3 scripts/generate_reporting.py",
)


class MissingGeneratedOutputError(FileNotFoundError):
    """Raised when canonical generated outputs needed by the portal are absent."""

    def __init__(self, missing_paths: tuple[Path, ...]) -> None:
        self.missing_paths = missing_paths
        missing = ", ".join(str(path) for path in missing_paths)
        commands = "\n".join(REQUIRED_GENERATION_COMMANDS)
        super().__init__(
            "Reviewer portal outputs are missing. Missing path(s): "
            f"{missing}. Generate them with:\n{commands}"
        )


@dataclass(frozen=True)
class ReviewerState:
    """Loaded source-of-truth outputs and flattened reviewer rows."""

    outputs_root: Path
    inventory: Any
    access_state: Any
    audit_log: Any
    evidence_pack: Any
    compliance_assessment: Any
    reporting_snapshot: ReportingSnapshot
    kpis: tuple[GovernanceKPI, ...]
    dataset_rows: tuple[dict[str, Any], ...]
    model_rows: tuple[dict[str, Any], ...]
    project_rows: tuple[dict[str, Any], ...]
    request_rows: tuple[dict[str, Any], ...]
    decision_rows: tuple[dict[str, Any], ...]
    grant_rows: tuple[dict[str, Any], ...]
    audit_event_rows: tuple[dict[str, Any], ...]
    control_result_rows: tuple[dict[str, Any], ...]
    risk_indicator_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ReviewerPolicyState:
    """Loaded policy/control catalog rows for the reviewer portal."""

    policy_rows: tuple[dict[str, Any], ...]
    control_rows: tuple[dict[str, Any], ...]
    traceability_rows: tuple[dict[str, Any], ...]
    assurance_summary: Any


@dataclass(frozen=True)
class ReviewerAssuranceState:
    """Loaded assurance-history rows for the reviewer portal."""

    snapshot_rows: tuple[dict[str, Any], ...]
    control_drift_rows: tuple[dict[str, Any], ...]
    risk_drift_rows: tuple[dict[str, Any], ...]
    comparison: Any


@dataclass(frozen=True)
class ReviewerAssurancePackState:
    """Loaded integrated assurance review pack rows for the reviewer portal."""

    pack: Any
    priority_finding_rows: tuple[dict[str, Any], ...]
    reviewer_action_rows: tuple[dict[str, Any], ...]
    evidence_map_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ReviewerReadinessState:
    """Loaded review-readiness rows for the reviewer portal."""

    checklist: Any
    demo_readiness: Any
    acceptance_result_rows: tuple[dict[str, Any], ...]
    artifact_rows: tuple[dict[str, Any], ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_outputs_root() -> Path:
    """Return the repository's default generated-output root."""
    return _repo_root() / "outputs"


def required_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Canonical files the reviewer portal expects to exist."""
    root = Path(outputs_root)
    return (
        root / "inventory" / "inventory_portfolio.json",
        root / "access" / "access_control_state.json",
        root / "evidence" / "audit_events.json",
        root / "evidence" / "evidence_pack.json",
        root / "compliance" / "compliance_summary.json",
        root / "reporting" / "reporting_snapshot.json",
    )


def missing_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return required generated files absent from ``outputs_root``."""
    return tuple(path for path in required_output_paths(outputs_root) if not path.is_file())


def required_policy_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Canonical policy catalog files the optional portal page expects."""
    root = Path(outputs_root)
    return (
        root / "policy" / "policy_catalog.json",
        root / "policy" / "control_catalog.json",
        root / "policy" / "control_evidence_traceability.csv",
        root / "policy" / "policy_assurance_summary.json",
    )


def missing_policy_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return missing policy catalog files under ``outputs_root``."""
    return tuple(path for path in required_policy_output_paths(outputs_root) if not path.is_file())


def required_assurance_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Canonical assurance-history files the optional portal page expects."""
    root = Path(outputs_root)
    return (
        root / "assurance" / "assurance_snapshots.json",
        root / "assurance" / "assurance_comparison.json",
        root / "assurance" / "control_drift.csv",
        root / "assurance" / "risk_drift.csv",
        root / "assurance" / "assurance_drift_summary.json",
    )


def missing_assurance_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return missing assurance-history files under ``outputs_root``."""
    return tuple(
        path for path in required_assurance_output_paths(outputs_root) if not path.is_file()
    )


def required_assurance_pack_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Canonical integrated assurance pack files the optional portal page expects."""
    root = Path(outputs_root)
    return (
        root / "assurance_pack" / "assurance_review_pack.json",
        root / "assurance_pack" / "priority_findings.csv",
        root / "assurance_pack" / "reviewer_actions.csv",
        root / "assurance_pack" / "assurance_evidence_map.csv",
        root / "assurance_pack" / "assurance_review_pack.md",
    )


def missing_assurance_pack_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return missing integrated assurance pack files under ``outputs_root``."""
    return tuple(
        path for path in required_assurance_pack_output_paths(outputs_root) if not path.is_file()
    )


def required_readiness_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Canonical review-readiness files the optional portal page expects."""
    root = Path(outputs_root)
    return (
        root / "readiness" / "acceptance_checklist.json",
        root / "readiness" / "acceptance_checklist.csv",
        root / "readiness" / "artifact_completeness.json",
        root / "readiness" / "demo_readiness.json",
        root / "readiness" / "review_readiness_report.md",
    )


def missing_readiness_output_paths(outputs_root: str | Path) -> tuple[Path, ...]:
    """Return missing review-readiness files under ``outputs_root``."""
    return tuple(
        path for path in required_readiness_output_paths(outputs_root) if not path.is_file()
    )


def _value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, tuple | list):
        return "; ".join(str(_value(item)) for item in value)
    if hasattr(value, "value"):
        return value.value
    return value


def _model_row(record: Any) -> dict[str, Any]:
    return {key: _value(value) for key, value in record.model_dump(mode="python").items()}


def _grant_status(grant: Any, evaluated_at: datetime) -> str:
    if AccessControlService.is_grant_active(grant, evaluated_at):
        return "active"
    if grant.status.value == "revoked":
        return "revoked"
    return "expired"


def _as_of(snapshot: ReportingSnapshot) -> datetime:
    metrics = snapshot.all_metrics
    return metrics[0].as_of if metrics else snapshot.generated_at


def load_reviewer_state(outputs_root: str | Path | None = None) -> ReviewerState:
    """Load all canonical generated outputs for the local reviewer portal."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = missing_output_paths(root)
    if missing:
        raise MissingGeneratedOutputError(missing)

    inventory = load_portfolio(root / "inventory")
    access_state = load_access_state(root / "access")
    audit_log = load_audit_log(root / "evidence")
    evidence_pack = load_evidence_pack(root / "evidence")
    compliance_assessment = load_compliance_assessment(root / "compliance")
    reporting_snapshot = load_reporting_snapshot(root / "reporting")
    evaluated_at = _as_of(reporting_snapshot)

    decisions_by_request = {decision.request_id: decision for decision in access_state.decisions}
    request_rows = []
    for request in sorted(access_state.requests, key=lambda item: item.request_id):
        row = _model_row(request)
        decision = decisions_by_request.get(request.request_id)
        row["decision_id"] = decision.decision_id if decision else ""
        row["decision"] = decision.decision.value if decision else ""
        row["decision_reason"] = decision.decision_reason if decision else ""
        request_rows.append(row)

    grant_rows = []
    for grant in sorted(access_state.grants, key=lambda item: item.grant_id):
        row = _model_row(grant)
        row["status_as_of_evaluation"] = _grant_status(grant, evaluated_at)
        grant_rows.append(row)

    return ReviewerState(
        outputs_root=root,
        inventory=inventory,
        access_state=access_state,
        audit_log=audit_log,
        evidence_pack=evidence_pack,
        compliance_assessment=compliance_assessment,
        reporting_snapshot=reporting_snapshot,
        kpis=reporting_snapshot.all_metrics,
        dataset_rows=tuple(
            _model_row(item) for item in sorted(inventory.datasets, key=lambda d: d.dataset_id)
        ),
        model_rows=tuple(
            _model_row(item) for item in sorted(inventory.models, key=lambda m: m.model_id)
        ),
        project_rows=tuple(
            _model_row(item)
            for item in sorted(inventory.research_projects, key=lambda p: p.research_project_id)
        ),
        request_rows=tuple(request_rows),
        decision_rows=tuple(
            _model_row(item) for item in sorted(access_state.decisions, key=lambda d: d.decision_id)
        ),
        grant_rows=tuple(grant_rows),
        audit_event_rows=tuple(_model_row(item) for item in audit_log.events_in_order()),
        control_result_rows=tuple(
            _model_row(item) for item in compliance_assessment.control_results
        ),
        risk_indicator_rows=tuple(
            _model_row(item) for item in compliance_assessment.risk_indicators
        ),
    )


def load_reviewer_policy_state(outputs_root: str | Path | None = None) -> ReviewerPolicyState:
    """Load generated policy catalog outputs for the optional reviewer page."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = missing_policy_output_paths(root)
    if missing:
        raise MissingGeneratedOutputError(missing)

    policies = load_policy_catalog(root / "policy")
    controls = load_control_catalog(root / "policy")
    summary = load_policy_assurance_summary(root / "policy")
    traceability_path = root / "policy" / "control_evidence_traceability.csv"
    with traceability_path.open(newline="", encoding="utf-8") as fh:
        traceability_rows = tuple(dict(row) for row in csv.DictReader(fh))

    return ReviewerPolicyState(
        policy_rows=tuple(policy.model_dump(mode="json") for policy in policies),
        control_rows=tuple(control.model_dump(mode="json") for control in controls),
        traceability_rows=traceability_rows,
        assurance_summary=summary,
    )


def load_reviewer_assurance_state(
    outputs_root: str | Path | None = None,
) -> ReviewerAssuranceState:
    """Load generated assurance-history outputs for the optional reviewer page."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = missing_assurance_output_paths(root)
    if missing:
        raise MissingGeneratedOutputError(missing)

    history = load_assurance_history(root / "assurance")
    comparison = load_assurance_comparison(root / "assurance")
    with (root / "assurance" / "control_drift.csv").open(newline="", encoding="utf-8") as fh:
        control_rows = tuple(dict(row) for row in csv.DictReader(fh))
    with (root / "assurance" / "risk_drift.csv").open(newline="", encoding="utf-8") as fh:
        risk_rows = tuple(dict(row) for row in csv.DictReader(fh))

    return ReviewerAssuranceState(
        snapshot_rows=tuple(
            {
                "snapshot_id": snapshot.snapshot_id,
                "captured_at": snapshot.captured_at.isoformat(),
                "assessment_id": snapshot.assessment_id,
                "posture": snapshot.posture.value,
                "bounded_risk_score": snapshot.bounded_risk_score,
                "risk_indicator_count": snapshot.risk_indicator_count,
                "control_status_counts": "; ".join(
                    f"{key}={value}" for key, value in snapshot.control_status_counts.items()
                ),
                "source_refs": "; ".join(snapshot.source_refs),
            }
            for snapshot in history.ordered_snapshots()
        ),
        control_drift_rows=control_rows,
        risk_drift_rows=risk_rows,
        comparison=comparison,
    )


def load_reviewer_assurance_pack_state(
    outputs_root: str | Path | None = None,
) -> ReviewerAssurancePackState:
    """Load generated integrated assurance pack outputs for the optional reviewer page."""
    from governance_platform.reviewer.assurance_pack import load_assurance_review_pack

    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = missing_assurance_pack_output_paths(root)
    if missing:
        raise MissingGeneratedOutputError(missing)

    pack = load_assurance_review_pack(root / "assurance_pack")
    with (root / "assurance_pack" / "priority_findings.csv").open(
        newline="", encoding="utf-8"
    ) as fh:
        priority_rows = tuple(dict(row) for row in csv.DictReader(fh))
    with (root / "assurance_pack" / "reviewer_actions.csv").open(
        newline="", encoding="utf-8"
    ) as fh:
        action_rows = tuple(dict(row) for row in csv.DictReader(fh))
    with (root / "assurance_pack" / "assurance_evidence_map.csv").open(
        newline="", encoding="utf-8"
    ) as fh:
        evidence_rows = tuple(dict(row) for row in csv.DictReader(fh))

    return ReviewerAssurancePackState(
        pack=pack,
        priority_finding_rows=priority_rows,
        reviewer_action_rows=action_rows,
        evidence_map_rows=evidence_rows,
    )


def load_reviewer_readiness_state(
    outputs_root: str | Path | None = None,
) -> ReviewerReadinessState:
    """Load generated review-readiness outputs for the optional reviewer page."""
    from governance_platform.reviewer.readiness import (
        load_acceptance_checklist,
        load_demo_readiness,
    )

    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = missing_readiness_output_paths(root)
    if missing:
        raise MissingGeneratedOutputError(missing)

    readiness_root = root / "readiness"
    checklist = load_acceptance_checklist(readiness_root)
    demo_readiness = load_demo_readiness(readiness_root)
    with (readiness_root / "acceptance_checklist.csv").open(newline="", encoding="utf-8") as fh:
        acceptance_rows = tuple(dict(row) for row in csv.DictReader(fh))
    artifact_rows = tuple(
        json.loads((readiness_root / "artifact_completeness.json").read_text(encoding="utf-8"))
    )

    return ReviewerReadinessState(
        checklist=checklist,
        demo_readiness=demo_readiness,
        acceptance_result_rows=acceptance_rows,
        artifact_rows=artifact_rows,
    )


def kpi_by_name(state: ReviewerState, metric_name: str) -> GovernanceKPI:
    """Return a KPI by stable metric name."""
    for metric in state.kpis:
        if metric.metric_name == metric_name:
            return metric
    raise KeyError(f"KPI not found: {metric_name}")


def kpi_value(state: ReviewerState, metric_name: str) -> Any:
    """Return a KPI value by stable metric name."""
    return kpi_by_name(state, metric_name).value


def unique_values(rows: tuple[dict[str, Any], ...], field: str) -> tuple[Any, ...]:
    """Return stable non-empty unique values for a filter field."""
    return tuple(sorted({row[field] for row in rows if row.get(field) not in ("", None)}))


def filter_rows(
    rows: tuple[dict[str, Any], ...],
    *,
    equals: dict[str, Any] | None = None,
    contains: dict[str, str] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Filter reviewer rows by exact values and case-insensitive substring matches."""
    equals = equals or {}
    contains = contains or {}
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if any(
            value not in ("", None, "All") and row.get(field) != value
            for field, value in equals.items()
        ):
            continue
        if any(
            needle and needle.lower() not in str(row.get(field, "")).lower()
            for field, needle in contains.items()
        ):
            continue
        filtered.append(row)
    return tuple(filtered)


def status_counts(rows: tuple[dict[str, Any], ...], field: str) -> dict[str, int]:
    """Return deterministic counts for a row field."""
    counts = Counter(
        str(row.get(field, "")) for row in rows if row.get(field, "") not in ("", None)
    )
    return {key: counts[key] for key in sorted(counts)}


def rejection_reason_rows(state: ReviewerState) -> tuple[dict[str, Any], ...]:
    """Return reviewer rows for non-zero rejected-access reason metrics."""
    rows = []
    for metric in state.kpis:
        if not metric.metric_name.startswith("rejection_reason_") or metric.value == 0:
            continue
        rows.append(
            {
                "reason": metric.metric_name.removeprefix("rejection_reason_"),
                "count": metric.value,
                "source_refs": "; ".join(metric.source_refs),
            }
        )
    return tuple(rows)


def kpi_prefix_rows(
    state: ReviewerState, *, prefix: str, label_name: str = "category"
) -> tuple[dict[str, Any], ...]:
    """Return KPI rows whose metric names share ``prefix``."""
    rows = []
    for metric in state.kpis:
        if not metric.metric_name.startswith(prefix):
            continue
        rows.append(
            {
                label_name: metric.metric_name.removeprefix(prefix),
                "count": metric.value,
                "source_refs": "; ".join(metric.source_refs),
            }
        )
    return tuple(rows)


def _split_refs(value: Any) -> tuple[str, ...]:
    if value in ("", None):
        return ()
    if isinstance(value, tuple | list):
        return tuple(str(item) for item in value if str(item))
    return tuple(ref.strip() for ref in str(value).split(";") if ref.strip())


def evidence_reference_rows(state: ReviewerState) -> tuple[dict[str, Any], ...]:
    """Return flattened evidence references from compliance and risk outputs."""
    rows: list[dict[str, Any]] = []
    for result in state.control_result_rows:
        for evidence_ref in _split_refs(result.get("evidence_refs")):
            rows.append(
                {
                    "evidence_ref": evidence_ref,
                    "source_type": "control_result",
                    "source_id": result["result_id"],
                    "entity_type": result["entity_type"],
                    "entity_id": result["entity_id"],
                    "status": result["status"],
                    "severity": result["severity"],
                    "finding_code": result["finding_code"],
                    "summary": result["message"],
                }
            )
    for indicator in state.risk_indicator_rows:
        for evidence_ref in _split_refs(indicator.get("evidence_refs")):
            rows.append(
                {
                    "evidence_ref": evidence_ref,
                    "source_type": "risk_indicator",
                    "source_id": indicator["indicator_id"],
                    "entity_type": indicator["entity_type"],
                    "entity_id": indicator["entity_id"],
                    "status": indicator["category"],
                    "severity": indicator["severity"],
                    "finding_code": indicator["category"],
                    "summary": indicator["rationale"],
                }
            )
    return tuple(
        sorted(rows, key=lambda row: (row["evidence_ref"], row["source_type"], row["source_id"]))
    )


def drillthrough_by_evidence_ref(state: ReviewerState, evidence_ref: str) -> dict[str, Any]:
    """Return source records connected to a selected evidence reference."""
    ref_type, _, ref_id = evidence_ref.partition(":")
    related: dict[str, Any] = {
        "evidence_references": filter_rows(
            evidence_reference_rows(state), equals={"evidence_ref": evidence_ref}
        ),
        "control_results": tuple(
            row
            for row in state.control_result_rows
            if evidence_ref in _split_refs(row.get("evidence_refs"))
        ),
        "risk_indicators": tuple(
            row
            for row in state.risk_indicator_rows
            if evidence_ref in _split_refs(row.get("evidence_refs"))
        ),
    }

    if ref_type == "dataset":
        related["datasets"] = filter_rows(state.dataset_rows, equals={"dataset_id": ref_id})
    elif ref_type == "model":
        related["models"] = filter_rows(state.model_rows, equals={"model_id": ref_id})
    elif ref_type == "access_grant":
        related.update(drillthrough_by_grant(state, ref_id))
    elif ref_type == "access_request":
        related.update(drillthrough_by_request(state, ref_id))
    elif ref_type == "approval_decision":
        decision = filter_rows(state.decision_rows, equals={"decision_id": ref_id})
        request_id = decision[0]["request_id"] if decision else ""
        related["decision"] = decision
        related["request"] = filter_rows(state.request_rows, equals={"request_id": request_id})
    elif ref_type == "audit_event":
        related["audit_events"] = filter_rows(state.audit_event_rows, equals={"event_id": ref_id})
    elif ref_type == "evidence_pack":
        related["evidence_pack"] = (
            {
                "evidence_pack_id": state.evidence_pack.evidence_pack_id,
                "generated_at": state.evidence_pack.generated_at.isoformat(),
                "scope": state.evidence_pack.scope,
                "complete": state.evidence_pack.completeness.complete,
                "problems": "; ".join(state.evidence_pack.completeness.problems),
            },
        )

    return related


def drillthrough_by_project(state: ReviewerState, research_project_id: str) -> dict[str, Any]:
    """Return related records for a selected research project."""
    return {
        "project": filter_rows(
            state.project_rows, equals={"research_project_id": research_project_id}
        ),
        "requests": filter_rows(
            state.request_rows, equals={"research_project_id": research_project_id}
        ),
        "grants": filter_rows(
            state.grant_rows, equals={"research_project_id": research_project_id}
        ),
        "audit_events": filter_rows(
            state.audit_event_rows, equals={"research_project_id": research_project_id}
        ),
    }


def drillthrough_by_request(state: ReviewerState, request_id: str) -> dict[str, Any]:
    """Return related records for a selected access request."""
    return {
        "request": filter_rows(state.request_rows, equals={"request_id": request_id}),
        "decision": filter_rows(state.decision_rows, equals={"request_id": request_id}),
        "grants": filter_rows(state.grant_rows, equals={"request_id": request_id}),
        "audit_events": filter_rows(state.audit_event_rows, equals={"request_id": request_id}),
    }


def drillthrough_by_grant(state: ReviewerState, grant_id: str) -> dict[str, Any]:
    """Return related records for a selected access grant."""
    grant_rows = filter_rows(state.grant_rows, equals={"grant_id": grant_id})
    request_id = grant_rows[0]["request_id"] if grant_rows else ""
    return {
        "grant": grant_rows,
        "request": filter_rows(state.request_rows, equals={"request_id": request_id}),
        "audit_events": filter_rows(state.audit_event_rows, equals={"grant_id": grant_id}),
        "control_results": tuple(
            row
            for row in state.control_result_rows
            if row.get("entity_id") == grant_id
            or f"access_grant:{grant_id}" in row.get("evidence_refs", "")
        ),
    }


def synthetic_boundary_text() -> str:
    """Short UI-safe statement of the local/synthetic implementation boundary."""
    return (
        "Local deterministic reviewer portal over synthetic generated outputs only. "
        "No real patient data, production access enforcement, Fabric/Power BI deployment, "
        "live monitoring, or regulatory certification is represented."
    )
