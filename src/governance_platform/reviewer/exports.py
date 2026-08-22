"""Deterministic reviewer handoff exports.

The functions in this module package existing generated governance outputs for
portable review. They do not re-evaluate controls, make access decisions, or
duplicate source-of-truth governance logic.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.reviewer.data import (
    ReviewerState,
    drillthrough_by_project,
    evidence_reference_rows,
    filter_rows,
    kpi_value,
)

REVIEWER_BRIEFING_JSON_FILENAME = "reviewer_briefing.json"
REVIEWER_BRIEFING_MARKDOWN_FILENAME = "reviewer_briefing.md"
REVIEWER_KPIS_CSV_FILENAME = "reviewer_kpis.csv"
REVIEWER_FINDINGS_CSV_FILENAME = "reviewer_findings.csv"
REVIEWER_EVIDENCE_INDEX_CSV_FILENAME = "reviewer_evidence_index.csv"
REVIEWER_FILTERED_VIEWS_CSV_FILENAME = "reviewer_filtered_views.csv"
REVIEWER_FILTERED_VIEWS_MARKDOWN_FILENAME = "reviewer_filtered_views.md"

REVIEWER_OUTPUT_FILENAMES: tuple[str, ...] = (
    REVIEWER_BRIEFING_JSON_FILENAME,
    REVIEWER_BRIEFING_MARKDOWN_FILENAME,
    REVIEWER_KPIS_CSV_FILENAME,
    REVIEWER_FINDINGS_CSV_FILENAME,
    REVIEWER_EVIDENCE_INDEX_CSV_FILENAME,
    REVIEWER_FILTERED_VIEWS_CSV_FILENAME,
    REVIEWER_FILTERED_VIEWS_MARKDOWN_FILENAME,
)

_LIST_FIELD_SEPARATOR = ";"


class ReviewerFinding(BaseModel):
    """One concise finding surfaced in the reviewer briefing."""

    model_config = {"frozen": True, "extra": "forbid"}

    source_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()


class ReviewerBriefing(BaseModel):
    """A concise, portable reviewer briefing over generated governance outputs."""

    model_config = {"frozen": True, "extra": "forbid"}

    briefing_id: str = Field(pattern=r"^RB-\d{4}$")
    generated_at: datetime
    snapshot_id: str = Field(pattern=r"^RS-\d{4}$")
    evidence_pack_id: str = Field(pattern=r"^EVP-\d{4}$")
    compliance_assessment_id: str = Field(pattern=r"^CA-\d{4}$")
    governance_posture: str = Field(min_length=1)
    bounded_risk_score: int = Field(ge=0, le=100)
    inventory_metrics: dict[str, Any]
    access_metrics: dict[str, Any]
    audit_evidence_metrics: dict[str, Any]
    compliance_risk_metrics: dict[str, Any]
    notable_findings: tuple[ReviewerFinding, ...]
    key_evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @field_validator("key_evidence_refs", "limitations")
    @classmethod
    def _tuple_is_not_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("field must contain at least one value")
        return value

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> ReviewerBriefing:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError("reviewer briefing must preserve synthetic/local/non-production flags")
        return self


class EvidenceIndexEntry(BaseModel):
    """A reviewer-friendly evidence-reference mapping."""

    model_config = {"frozen": True, "extra": "forbid"}

    evidence_ref: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    source_plane: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_file: str = Field(min_length=1)


class FilteredReviewerView(BaseModel):
    """A named deterministic reviewer export view."""

    model_config = {"frozen": True, "extra": "forbid"}

    view_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rows: tuple[dict[str, Any], ...]


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple | list):
        return _LIST_FIELD_SEPARATOR.join(str(item) for item in value)
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _split_refs(value: Any) -> tuple[str, ...]:
    if value in ("", None):
        return ()
    if isinstance(value, tuple | list):
        return tuple(str(item) for item in value if str(item))
    return tuple(ref.strip() for ref in str(value).split(";") if ref.strip())


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, columns: tuple[str, ...], rows: tuple[dict[str, object], ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row.get(column, "")) for column in columns])


def _metric_group(state: ReviewerState, metric_names: tuple[str, ...]) -> dict[str, Any]:
    return {name: kpi_value(state, name) for name in metric_names}


def build_reviewer_findings(state: ReviewerState) -> tuple[dict[str, Any], ...]:
    """Return concise warning/failure and risk-indicator rows for reviewer handoff."""
    rows: list[dict[str, Any]] = []
    for result in state.control_result_rows:
        if result["status"] == "pass":
            continue
        rows.append(
            {
                "source_type": "control_result",
                "source_id": result["result_id"],
                "entity_type": result["entity_type"],
                "entity_id": result["entity_id"],
                "status": result["status"],
                "severity": result["severity"],
                "finding_code": result["finding_code"],
                "summary": result["message"],
                "evidence_refs": result["evidence_refs"],
            }
        )
    for indicator in state.risk_indicator_rows:
        rows.append(
            {
                "source_type": "risk_indicator",
                "source_id": indicator["indicator_id"],
                "entity_type": indicator["entity_type"],
                "entity_id": indicator["entity_id"],
                "status": indicator["category"],
                "severity": indicator["severity"],
                "finding_code": indicator["category"],
                "summary": indicator["rationale"],
                "evidence_refs": indicator["evidence_refs"],
            }
        )
    return tuple(
        sorted(rows, key=lambda row: (row["severity"], row["source_type"], row["source_id"]))
    )


def build_reviewer_briefing(state: ReviewerState) -> ReviewerBriefing:
    """Build the deterministic reviewer briefing model."""
    findings = tuple(
        ReviewerFinding(
            source_type=row["source_type"],
            source_id=row["source_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            status=row["status"],
            severity=row["severity"],
            summary=row["summary"],
            evidence_refs=_split_refs(row["evidence_refs"]),
        )
        for row in build_reviewer_findings(state)
    )
    finding_refs = sorted(
        {ref for finding in findings for ref in finding.evidence_refs}
        | {f"evidence_pack:{state.evidence_pack.evidence_pack_id}", "audit_events"}
    )

    return ReviewerBriefing(
        briefing_id="RB-0001",
        generated_at=state.reporting_snapshot.generated_at,
        snapshot_id=state.reporting_snapshot.snapshot_id,
        evidence_pack_id=state.evidence_pack.evidence_pack_id,
        compliance_assessment_id=state.compliance_assessment.assessment_id,
        governance_posture=kpi_value(state, "overall_governance_posture"),
        bounded_risk_score=kpi_value(state, "bounded_risk_score"),
        inventory_metrics=_metric_group(
            state,
            (
                "total_datasets",
                "approved_datasets",
                "all_datasets_synthetic_only",
                "total_models",
                "models_risk_tier_high",
                "total_research_projects",
            ),
        ),
        access_metrics=_metric_group(
            state,
            (
                "total_access_requests",
                "approved_access_requests",
                "rejected_access_requests",
                "active_grants",
                "expired_grants",
                "revoked_grants",
            ),
        ),
        audit_evidence_metrics=_metric_group(
            state,
            (
                "total_audit_events",
                "audit_completeness_status",
                "evidence_completeness_status",
                "traceable_correlation_chains",
            ),
        ),
        compliance_risk_metrics=_metric_group(
            state,
            (
                "controls_evaluated",
                "controls_passed",
                "control_warnings",
                "control_failures",
                "control_pass_rate",
                "risk_indicator_count",
                "bounded_risk_score",
            ),
        ),
        notable_findings=findings,
        key_evidence_refs=tuple(finding_refs),
        limitations=tuple(state.reporting_snapshot.limitations),
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def build_reviewer_kpi_rows(state: ReviewerState) -> tuple[dict[str, Any], ...]:
    """Return KPI rows for reviewer export."""
    return tuple(
        {
            "metric_id": metric.metric_id,
            "metric_name": metric.metric_name,
            "metric_domain": metric.metric_domain.value,
            "value": metric.value,
            "unit": metric.unit.value,
            "as_of": metric.as_of.isoformat(),
            "source_refs": ";".join(metric.source_refs),
            "description": metric.description,
        }
        for metric in state.kpis
    )


def _source_entry(
    evidence_ref: str,
    *,
    evidence_type: str,
    source_plane: str,
    entity_type: str,
    entity_id: str,
    description: str,
    source_file: str,
) -> EvidenceIndexEntry:
    return EvidenceIndexEntry(
        evidence_ref=evidence_ref,
        evidence_type=evidence_type,
        source_plane=source_plane,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        source_file=source_file,
    )


def build_reviewer_evidence_index(state: ReviewerState) -> tuple[EvidenceIndexEntry, ...]:
    """Build a deterministic evidence-reference index from existing identifiers."""
    entries: dict[str, EvidenceIndexEntry] = {}

    def add(entry: EvidenceIndexEntry) -> None:
        entries[entry.evidence_ref] = entry

    add(
        _source_entry(
            "inventory_portfolio",
            evidence_type="source_output",
            source_plane="inventory",
            entity_type="portfolio",
            entity_id="inventory_portfolio",
            description="Canonical synthetic dataset, model, and research-project inventory.",
            source_file="outputs/inventory/inventory_portfolio.json",
        )
    )
    add(
        _source_entry(
            "access_control_state",
            evidence_type="source_output",
            source_plane="access",
            entity_type="portfolio",
            entity_id="access_control_state",
            description="Canonical access request, decision, and grant state.",
            source_file="outputs/access/access_control_state.json",
        )
    )
    add(
        _source_entry(
            "audit_events",
            evidence_type="source_output",
            source_plane="audit",
            entity_type="audit_log",
            entity_id="audit_events",
            description="Canonical append-only audit event log.",
            source_file="outputs/evidence/audit_events.json",
        )
    )
    add(
        _source_entry(
            "audit_log:audit_events",
            evidence_type="source_output",
            source_plane="audit",
            entity_type="audit_log",
            entity_id="audit_events",
            description="Compliance evidence reference for the canonical audit event log.",
            source_file="outputs/evidence/audit_events.json",
        )
    )
    add(
        _source_entry(
            "control_results",
            evidence_type="source_output",
            source_plane="compliance",
            entity_type="control_results",
            entity_id="control_results",
            description="Canonical deterministic compliance control results.",
            source_file="outputs/compliance/control_results.json",
        )
    )
    add(
        _source_entry(
            "risk_indicators",
            evidence_type="source_output",
            source_plane="compliance",
            entity_type="risk_indicators",
            entity_id="risk_indicators",
            description="Bounded risk indicators derived from non-passing control results.",
            source_file="outputs/compliance/risk_indicators.json",
        )
    )
    add(
        _source_entry(
            "portfolio:synthetic_governance_state",
            evidence_type="source_output",
            source_plane="inventory",
            entity_type="portfolio",
            entity_id="synthetic_governance_state",
            description="Compliance evidence reference for the synthetic governance portfolio.",
            source_file="outputs/inventory/inventory_portfolio.json",
        )
    )
    add(
        _source_entry(
            f"evidence_pack:{state.evidence_pack.evidence_pack_id}",
            evidence_type="evidence_pack",
            source_plane="audit",
            entity_type="evidence_pack",
            entity_id=state.evidence_pack.evidence_pack_id,
            description="Reviewer-readable evidence pack over inventory, access, and audit state.",
            source_file="outputs/evidence/evidence_pack.json",
        )
    )
    add(
        _source_entry(
            f"compliance_assessment:{state.compliance_assessment.assessment_id}",
            evidence_type="compliance_assessment",
            source_plane="compliance",
            entity_type="compliance_assessment",
            entity_id=state.compliance_assessment.assessment_id,
            description="Canonical compliance assessment summary.",
            source_file="outputs/compliance/compliance_summary.json",
        )
    )
    add(
        _source_entry(
            "adr:0001",
            evidence_type="architecture_decision",
            source_plane="governance",
            entity_type="adr",
            entity_id="0001",
            description="Architecture decision record for synthetic-data-only boundaries.",
            source_file="docs/architecture/decisions/0001-synthetic-data-only.md",
        )
    )

    for dataset in state.dataset_rows:
        add(
            _source_entry(
                f"dataset:{dataset['dataset_id']}",
                evidence_type="entity_reference",
                source_plane="inventory",
                entity_type="dataset",
                entity_id=dataset["dataset_id"],
                description=dataset["name"],
                source_file="outputs/inventory/inventory_portfolio.json",
            )
        )
    for model in state.model_rows:
        add(
            _source_entry(
                f"model:{model['model_id']}",
                evidence_type="entity_reference",
                source_plane="inventory",
                entity_type="model",
                entity_id=model["model_id"],
                description=model["name"],
                source_file="outputs/inventory/inventory_portfolio.json",
            )
        )
    for project in state.project_rows:
        add(
            _source_entry(
                f"research_project:{project['research_project_id']}",
                evidence_type="entity_reference",
                source_plane="inventory",
                entity_type="research_project",
                entity_id=project["research_project_id"],
                description=project["title"],
                source_file="outputs/inventory/inventory_portfolio.json",
            )
        )
    for request in state.request_rows:
        add(
            _source_entry(
                f"access_request:{request['request_id']}",
                evidence_type="entity_reference",
                source_plane="access",
                entity_type="access_request",
                entity_id=request["request_id"],
                description=request["purpose"],
                source_file="outputs/access/access_control_state.json",
            )
        )
    for decision in state.decision_rows:
        add(
            _source_entry(
                f"approval_decision:{decision['decision_id']}",
                evidence_type="entity_reference",
                source_plane="access",
                entity_type="approval_decision",
                entity_id=decision["decision_id"],
                description=decision["decision_reason"],
                source_file="outputs/access/access_control_state.json",
            )
        )
    for grant in state.grant_rows:
        add(
            _source_entry(
                f"access_grant:{grant['grant_id']}",
                evidence_type="entity_reference",
                source_plane="access",
                entity_type="access_grant",
                entity_id=grant["grant_id"],
                description=f"{grant['status_as_of_evaluation']} grant for {grant['request_id']}",
                source_file="outputs/access/access_control_state.json",
            )
        )
    for event in state.audit_event_rows:
        add(
            _source_entry(
                f"audit_event:{event['event_id']}",
                evidence_type="entity_reference",
                source_plane="audit",
                entity_type="audit_event",
                entity_id=event["event_id"],
                description=f"{event['event_type']} for {event['entity_id']}",
                source_file="outputs/evidence/audit_events.json",
            )
        )

    referenced = {
        ref for row in evidence_reference_rows(state) for ref in _split_refs(row["evidence_ref"])
    } | {ref for metric in state.kpis for ref in metric.source_refs}
    missing = sorted(ref for ref in referenced if ref not in entries)
    if missing:
        raise ValueError(f"evidence reference(s) could not be indexed: {', '.join(missing)}")

    return tuple(entries[key] for key in sorted(entries))


def unresolved_evidence_refs(
    state: ReviewerState, index: tuple[EvidenceIndexEntry, ...] | None = None
) -> tuple[str, ...]:
    """Return evidence references used by reviewer outputs but absent from the index."""
    index_refs = {entry.evidence_ref for entry in (index or build_reviewer_evidence_index(state))}
    used_refs = {
        ref for row in evidence_reference_rows(state) for ref in _split_refs(row["evidence_ref"])
    } | {ref for metric in state.kpis for ref in metric.source_refs}
    return tuple(sorted(used_refs - index_refs))


def build_filtered_reviewer_views(state: ReviewerState) -> tuple[FilteredReviewerView, ...]:
    """Build common deterministic reviewer views without proliferating output files."""
    warning_controls = tuple(
        row for row in state.control_result_rows if row["status"] in {"warning", "fail"}
    )
    selected_control_id = warning_controls[0]["result_id"] if warning_controls else ""
    selected_project_id = "RP-0001"

    return (
        FilteredReviewerView(
            view_name="high_risk_models",
            description="Models with risk_tier=high.",
            rows=filter_rows(state.model_rows, equals={"risk_tier": "high"}),
        ),
        FilteredReviewerView(
            view_name="pending_or_rejected_research_projects",
            description="Research projects with pending or rejected approval status.",
            rows=tuple(
                row
                for row in state.project_rows
                if row["approval_status"] in {"pending", "rejected"}
            ),
        ),
        FilteredReviewerView(
            view_name="rejected_access_requests",
            description="Access requests rejected by deterministic eligibility checks.",
            rows=filter_rows(state.request_rows, equals={"status": "rejected"}),
        ),
        FilteredReviewerView(
            view_name="revoked_or_expired_grants",
            description="Access grants revoked or expired as of the fixed evaluation instant.",
            rows=tuple(
                row
                for row in state.grant_rows
                if row["status_as_of_evaluation"] in {"revoked", "expired"}
            ),
        ),
        FilteredReviewerView(
            view_name="warning_or_failed_controls",
            description="Compliance control results requiring reviewer attention.",
            rows=warning_controls,
        ),
        FilteredReviewerView(
            view_name="high_severity_risk_indicators",
            description="Risk indicators with high or critical severity.",
            rows=tuple(
                row for row in state.risk_indicator_rows if row["severity"] in {"high", "critical"}
            ),
        ),
        FilteredReviewerView(
            view_name=f"audit_events_for_{selected_project_id}",
            description=f"Audit events for research project {selected_project_id}.",
            rows=drillthrough_by_project(state, selected_project_id)["audit_events"],
        ),
        FilteredReviewerView(
            view_name=f"evidence_references_for_{selected_control_id or 'no_control'}",
            description="Evidence references for the first warning/failed control result.",
            rows=(
                filter_rows(
                    evidence_reference_rows(state),
                    equals={"source_type": "control_result", "source_id": selected_control_id},
                )
                if selected_control_id
                else ()
            ),
        ),
    )


def _row_identity(row: dict[str, Any]) -> tuple[str, str]:
    identity_fields = (
        ("control_result", "result_id"),
        ("risk_indicator", "indicator_id"),
        ("audit_event", "event_id"),
        ("access_grant", "grant_id"),
        ("access_request", "request_id"),
        ("model", "model_id"),
        ("research_project", "research_project_id"),
        ("dataset", "dataset_id"),
        ("evidence_reference", "evidence_ref"),
    )
    for entity_type, field in identity_fields:
        if row.get(field):
            return entity_type, str(row[field])
    if row.get("entity_type") and row.get("entity_id"):
        return str(row["entity_type"]), str(row["entity_id"])
    return str(row.get("entity_type", "")), str(row.get("entity_id", ""))


def _row_summary(row: dict[str, Any]) -> str:
    if row.get("grant_id"):
        status = row.get("status_as_of_evaluation", row.get("status", ""))
        return f"{status} grant for {row['request_id']}"
    return str(
        row.get("name")
        or row.get("title")
        or row.get("purpose")
        or row.get("message")
        or row.get("rationale")
        or row.get("event_type")
        or row.get("summary")
        or row.get("status")
        or ""
    )


def flatten_filtered_view_rows(
    views: tuple[FilteredReviewerView, ...],
) -> tuple[dict[str, object], ...]:
    """Flatten named reviewer views into a compact CSV shape."""
    flattened: list[dict[str, object]] = []
    for view in views:
        for index, row in enumerate(view.rows, start=1):
            entity_type, entity_id = _row_identity(row)
            flattened.append(
                {
                    "view_name": view.view_name,
                    "row_number": index,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "status": row.get("status")
                    or row.get("approval_status")
                    or row.get("status_as_of_evaluation")
                    or row.get("outcome")
                    or "",
                    "severity": row.get("severity", ""),
                    "summary": _row_summary(row),
                    "evidence_refs": row.get("evidence_refs", ""),
                }
            )
    return tuple(flattened)


def render_reviewer_briefing_markdown(briefing: ReviewerBriefing) -> str:
    """Render reviewer briefing Markdown from the validated briefing model."""
    lines: list[str] = [
        "# Reviewer Briefing Bundle",
        "",
        "> Local deterministic reviewer handoff over synthetic generated outputs only. No "
        "production hosting, authentication, live tenant integration, or regulatory "
        "certification is represented.",
        "",
        f"- **Briefing ID:** {briefing.briefing_id}",
        f"- **Generated at:** {briefing.generated_at.isoformat()}",
        f"- **Reporting snapshot:** {briefing.snapshot_id}",
        f"- **Governance posture:** {briefing.governance_posture}",
        f"- **Bounded risk score:** {briefing.bounded_risk_score}",
        "",
    ]

    sections = (
        ("Inventory", briefing.inventory_metrics),
        ("Access Control", briefing.access_metrics),
        ("Audit & Evidence", briefing.audit_evidence_metrics),
        ("Compliance & Risk", briefing.compliance_risk_metrics),
    )
    for title, metrics in sections:
        lines.extend([f"## {title}", ""])
        lines.extend(f"- **{name}:** {value}" for name, value in metrics.items())
        lines.append("")

    lines.extend(["## Notable Findings", ""])
    if briefing.notable_findings:
        for finding in briefing.notable_findings:
            refs = ", ".join(finding.evidence_refs) if finding.evidence_refs else "none"
            lines.append(
                f"- **{finding.source_id}** ({finding.status}/{finding.severity}) "
                f"{finding.entity_type}:{finding.entity_id} — {finding.summary} "
                f"[evidence: {refs}]"
            )
    else:
        lines.append("No warning or failed controls and no risk indicators are present.")
    lines.append("")

    lines.extend(["## Key Evidence References", ""])
    lines.extend(f"- {ref}" for ref in briefing.key_evidence_refs)
    lines.append("")

    lines.extend(["## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in briefing.limitations)
    lines.append("")
    return "\n".join(lines)


def render_filtered_views_markdown(views: tuple[FilteredReviewerView, ...]) -> str:
    """Render compact Markdown for deterministic filtered reviewer views."""
    lines = [
        "# Filtered Reviewer Views",
        "",
        "> Saved local reviewer views over generated synthetic governance outputs.",
        "",
    ]
    for view in views:
        lines.extend([f"## {view.view_name}", "", view.description, ""])
        if not view.rows:
            lines.extend(["No rows matched this deterministic view.", ""])
            continue
        for row in view.rows:
            _, row_id = _row_identity(row)
            summary = _row_summary(row)
            lines.append(f"- **{row_id}:** {summary}")
        lines.append("")
    return "\n".join(lines)


def export_reviewer_bundle(
    state: ReviewerState, output_dir: str | Path
) -> dict[str, Path | int | str]:
    """Write deterministic reviewer handoff outputs and return export metadata."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    briefing = build_reviewer_briefing(state)
    kpi_rows = build_reviewer_kpi_rows(state)
    finding_rows = build_reviewer_findings(state)
    evidence_index = build_reviewer_evidence_index(state)
    views = build_filtered_reviewer_views(state)
    flattened_views = flatten_filtered_view_rows(views)

    _write_json(out / REVIEWER_BRIEFING_JSON_FILENAME, briefing.model_dump(mode="json"))
    (out / REVIEWER_BRIEFING_MARKDOWN_FILENAME).write_text(
        render_reviewer_briefing_markdown(briefing), encoding="utf-8"
    )
    _write_csv(
        out / REVIEWER_KPIS_CSV_FILENAME,
        (
            "metric_id",
            "metric_name",
            "metric_domain",
            "value",
            "unit",
            "as_of",
            "source_refs",
            "description",
        ),
        kpi_rows,
    )
    _write_csv(
        out / REVIEWER_FINDINGS_CSV_FILENAME,
        (
            "source_type",
            "source_id",
            "entity_type",
            "entity_id",
            "status",
            "severity",
            "finding_code",
            "summary",
            "evidence_refs",
        ),
        finding_rows,
    )
    _write_csv(
        out / REVIEWER_EVIDENCE_INDEX_CSV_FILENAME,
        (
            "evidence_ref",
            "evidence_type",
            "source_plane",
            "entity_type",
            "entity_id",
            "description",
            "source_file",
        ),
        tuple(entry.model_dump(mode="json") for entry in evidence_index),
    )
    _write_csv(
        out / REVIEWER_FILTERED_VIEWS_CSV_FILENAME,
        (
            "view_name",
            "row_number",
            "entity_type",
            "entity_id",
            "status",
            "severity",
            "summary",
            "evidence_refs",
        ),
        flattened_views,
    )
    (out / REVIEWER_FILTERED_VIEWS_MARKDOWN_FILENAME).write_text(
        render_filtered_views_markdown(views), encoding="utf-8"
    )

    return {
        "output_dir": out,
        "briefing_id": briefing.briefing_id,
        "kpi_count": len(kpi_rows),
        "finding_count": len(finding_rows),
        "evidence_ref_count": len(evidence_index),
        "filtered_view_count": len(views),
        "filtered_view_row_count": len(flattened_views),
    }


def load_reviewer_briefing(input_dir: str | Path) -> ReviewerBriefing:
    """Load and validate the canonical reviewer briefing JSON."""
    path = Path(input_dir) / REVIEWER_BRIEFING_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Reviewer briefing file not found: {path}")
    return ReviewerBriefing.model_validate(json.loads(path.read_text(encoding="utf-8")))


def validate_reviewer_bundle(input_dir: str | Path) -> list[str]:
    """Validate reviewer bundle files without raising."""
    root = Path(input_dir)
    problems: list[str] = []
    for filename in REVIEWER_OUTPUT_FILENAMES:
        if not (root / filename).is_file():
            problems.append(f"missing reviewer output: {root / filename}")

    try:
        load_reviewer_briefing(root)
    except (FileNotFoundError, ValueError) as exc:
        problems.append(str(exc))

    return problems
