"""Streamlit entrypoint for the local governance reviewer portal.

Run from the repository root:

    streamlit run src/governance_platform/reviewer_app.py

This is a local portfolio/demo interface over generated synthetic outputs. It
does not provide authentication, editing, approval actions, live monitoring,
Power BI/Fabric deployment, or production hosting.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import streamlit as st  # noqa: E402

from governance_platform.reviewer import (  # noqa: E402
    MissingGeneratedOutputError,
    drillthrough_by_evidence_ref,
    drillthrough_by_grant,
    drillthrough_by_project,
    drillthrough_by_request,
    evidence_reference_rows,
    filter_rows,
    kpi_prefix_rows,
    kpi_value,
    load_reviewer_state,
    rejection_reason_rows,
    status_counts,
    synthetic_boundary_text,
    unique_values,
)


def _format_metric(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        if 0 <= value <= 1:
            return f"{value:.1%}"
        return f"{value:.2f}"
    return str(value)


def _metric_grid(items: tuple[tuple[str, Any], ...], *, columns: int = 4) -> None:
    cols = st.columns(columns)
    for index, (label, value) in enumerate(items):
        cols[index % columns].metric(label, _format_metric(value))


def _chart_counts(title: str, counts: dict[str, int]) -> None:
    st.subheader(title)
    if not counts:
        st.caption("No records match the current filters.")
        return
    st.bar_chart(
        [{"category": key, "count": value} for key, value in counts.items()],
        x="category",
        y="count",
    )


def _table(rows: tuple[dict[str, Any], ...], *, empty: str) -> None:
    if rows:
        st.caption(f"{len(rows)} record(s)")
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption(empty)


def _select_filter(label: str, values: tuple[Any, ...]) -> Any:
    return st.selectbox(label, ("All", *values))


def _select_optional(label: str, values: tuple[Any, ...]) -> Any | None:
    if not values:
        st.caption(f"No {label.lower()} records available.")
        return None
    return st.selectbox(label, values)


def _overview_page(state) -> None:
    st.header("Executive Governance Overview")
    st.caption(synthetic_boundary_text())
    _metric_grid(
        (
            ("Posture", kpi_value(state, "overall_governance_posture")),
            ("Bounded risk score", kpi_value(state, "bounded_risk_score")),
            ("Controls passed", kpi_value(state, "controls_passed")),
            ("Warnings", kpi_value(state, "control_warnings")),
            ("Failures", kpi_value(state, "control_failures")),
            ("Datasets", kpi_value(state, "total_datasets")),
            ("Models", kpi_value(state, "total_models")),
            ("Research projects", kpi_value(state, "total_research_projects")),
            ("Access requests", kpi_value(state, "total_access_requests")),
            ("Rejected requests", kpi_value(state, "rejected_access_requests")),
            ("Active grants", kpi_value(state, "active_grants")),
            ("Audit complete", kpi_value(state, "audit_completeness_status")),
            ("Evidence complete", kpi_value(state, "evidence_completeness_status")),
        )
    )
    left, right = st.columns(2)
    with left:
        _chart_counts(
            "Control Findings By Severity",
            {
                "low": kpi_value(state, "findings_severity_low"),
                "medium": kpi_value(state, "findings_severity_medium"),
                "high": kpi_value(state, "findings_severity_high"),
                "critical": kpi_value(state, "findings_severity_critical"),
            },
        )
    with right:
        _chart_counts(
            "Grant Lifecycle Status", status_counts(state.grant_rows, "status_as_of_evaluation")
        )


def _data_model_page(state) -> None:
    st.header("Data & Model Governance")
    dataset_approval = _select_filter(
        "Dataset approval status", unique_values(state.dataset_rows, "approval_status")
    )
    dataset_sensitivity = _select_filter(
        "Dataset sensitivity", unique_values(state.dataset_rows, "sensitivity_classification")
    )
    research_allowed = _select_filter(
        "Research use allowed", unique_values(state.dataset_rows, "research_use_allowed")
    )
    dataset_search = st.text_input(
        "Dataset search", placeholder="Filter by dataset id, name, owner"
    )
    dataset_rows = filter_rows(
        state.dataset_rows,
        equals={
            "approval_status": dataset_approval,
            "sensitivity_classification": dataset_sensitivity,
            "research_use_allowed": research_allowed,
        },
    )
    if dataset_search:
        dataset_rows = tuple(
            row
            for row in dataset_rows
            if dataset_search.lower() in " ".join(str(value) for value in row.values()).lower()
        )
    _chart_counts(
        "Datasets By Sensitivity", status_counts(dataset_rows, "sensitivity_classification")
    )
    _table(
        dataset_rows,
        empty="No datasets match the selected filters.",
    )

    st.divider()
    model_risk = _select_filter("Model risk tier", unique_values(state.model_rows, "risk_tier"))
    model_approval = _select_filter(
        "Model approval status", unique_values(state.model_rows, "approval_status")
    )
    model_search = st.text_input("Model search", placeholder="Filter by model id, name, owner")
    model_rows = filter_rows(
        state.model_rows, equals={"risk_tier": model_risk, "approval_status": model_approval}
    )
    if model_search:
        model_rows = tuple(
            row
            for row in model_rows
            if model_search.lower() in " ".join(str(value) for value in row.values()).lower()
        )
    _chart_counts("Models By Risk Tier", status_counts(model_rows, "risk_tier"))
    _table(model_rows, empty="No models match the selected filters.")


def _research_access_page(state) -> None:
    st.header("Research & Access Governance")
    _metric_grid(
        (
            ("Total requests", kpi_value(state, "total_access_requests")),
            ("Approved requests", kpi_value(state, "approved_access_requests")),
            ("Rejected requests", kpi_value(state, "rejected_access_requests")),
            ("Approval rate", kpi_value(state, "access_approval_rate")),
            ("Active grants", kpi_value(state, "active_grants")),
            ("Expired grants", kpi_value(state, "expired_grants")),
            ("Revoked grants", kpi_value(state, "revoked_grants")),
        )
    )
    _chart_counts("Access Request Status", status_counts(state.request_rows, "status"))
    _chart_counts(
        "Rejected-Access Reasons",
        {row["reason"]: row["count"] for row in rejection_reason_rows(state)},
    )

    st.subheader("Research Projects")
    project_status = _select_filter(
        "Project approval status", unique_values(state.project_rows, "approval_status")
    )
    project_search = st.text_input(
        "Project search", placeholder="Filter by project id, title, owner"
    )
    project_rows = filter_rows(state.project_rows, equals={"approval_status": project_status})
    if project_search:
        project_rows = tuple(
            row
            for row in project_rows
            if project_search.lower() in " ".join(str(value) for value in row.values()).lower()
        )
    _table(project_rows, empty="No projects match the selected filters.")

    st.subheader("Access Requests")
    request_status = _select_filter("Request status", unique_values(state.request_rows, "status"))
    request_rows = filter_rows(state.request_rows, equals={"status": request_status})
    _table(request_rows, empty="No access requests match the selected filters.")

    st.subheader("Grants")
    grant_status = _select_filter(
        "Grant status", unique_values(state.grant_rows, "status_as_of_evaluation")
    )
    grant_rows = filter_rows(state.grant_rows, equals={"status_as_of_evaluation": grant_status})
    _table(grant_rows, empty="No grants match the selected filters.")

    st.subheader("Drill-through")
    drill_type = st.radio("Review by", ("Research project", "Request", "Grant"), horizontal=True)
    if drill_type == "Research project":
        selected = _select_optional(
            "Research project", unique_values(state.project_rows, "research_project_id")
        )
        if selected is None:
            return
        drill = drillthrough_by_project(state, selected)
    elif drill_type == "Request":
        selected = _select_optional("Request", unique_values(state.request_rows, "request_id"))
        if selected is None:
            return
        drill = drillthrough_by_request(state, selected)
    else:
        selected = _select_optional("Grant", unique_values(state.grant_rows, "grant_id"))
        if selected is None:
            return
        drill = drillthrough_by_grant(state, selected)
    for label, rows in drill.items():
        st.markdown(f"**{label.replace('_', ' ').title()}**")
        _table(rows, empty=f"No {label.replace('_', ' ')} found for {selected}.")


def _audit_evidence_page(state) -> None:
    st.header("Audit & Evidence")
    _metric_grid(
        (
            ("Audit events", kpi_value(state, "total_audit_events")),
            ("Audit complete", kpi_value(state, "audit_completeness_status")),
            ("Evidence complete", kpi_value(state, "evidence_completeness_status")),
            ("Traceable chains", kpi_value(state, "traceable_correlation_chains")),
        )
    )
    event_type = _select_filter("Event type", unique_values(state.audit_event_rows, "event_type"))
    outcome = _select_filter("Outcome", unique_values(state.audit_event_rows, "outcome"))
    project = _select_filter(
        "Research project", unique_values(state.audit_event_rows, "research_project_id")
    )
    request = _select_filter("Request", unique_values(state.audit_event_rows, "request_id"))
    grant = _select_filter("Grant", unique_values(state.audit_event_rows, "grant_id"))
    audit_search = st.text_input(
        "Audit search", placeholder="Filter by event id, actor, entity, reason"
    )
    rows = filter_rows(
        state.audit_event_rows,
        equals={
            "event_type": event_type,
            "outcome": outcome,
            "research_project_id": project,
            "request_id": request,
            "grant_id": grant,
        },
    )
    if audit_search:
        rows = tuple(
            row
            for row in rows
            if audit_search.lower() in " ".join(str(value) for value in row.values()).lower()
        )
    _chart_counts("Audit Events By Type", status_counts(rows, "event_type"))
    _table(rows, empty="No audit events match the selected filters.")

    st.subheader("Evidence Pack Summary")
    st.write(
        {
            "evidence_pack_id": state.evidence_pack.evidence_pack_id,
            "generated_at": state.evidence_pack.generated_at.isoformat(),
            "scope": state.evidence_pack.scope,
            "complete": state.evidence_pack.completeness.complete,
            "problems": list(state.evidence_pack.completeness.problems),
        }
    )


def _compliance_risk_page(state) -> None:
    st.header("Compliance & Risk")
    _metric_grid(
        (
            ("Controls evaluated", kpi_value(state, "controls_evaluated")),
            ("Controls passed", kpi_value(state, "controls_passed")),
            ("Warnings", kpi_value(state, "control_warnings")),
            ("Failures", kpi_value(state, "control_failures")),
            ("Pass rate", kpi_value(state, "control_pass_rate")),
            ("Risk indicators", kpi_value(state, "risk_indicator_count")),
            ("Bounded risk score", kpi_value(state, "bounded_risk_score")),
            ("Posture", kpi_value(state, "overall_governance_posture")),
        )
    )
    left, right = st.columns(2)
    with left:
        severity_rows = kpi_prefix_rows(state, prefix="findings_severity_", label_name="severity")
        _chart_counts(
            "Findings By Severity",
            {row["severity"]: row["count"] for row in severity_rows},
        )
    with right:
        domain_rows = kpi_prefix_rows(state, prefix="findings_domain_", label_name="domain")
        _chart_counts("Findings By Domain", {row["domain"]: row["count"] for row in domain_rows})

    st.subheader("Control Results")
    control_status = _select_filter(
        "Control status", unique_values(state.control_result_rows, "status")
    )
    severity = _select_filter("Severity", unique_values(state.control_result_rows, "severity"))
    entity_type = _select_filter(
        "Entity type", unique_values(state.control_result_rows, "entity_type")
    )
    control_search = st.text_input(
        "Control search", placeholder="Filter by control id, entity id, finding, message"
    )
    control_rows = filter_rows(
        state.control_result_rows,
        equals={"status": control_status, "severity": severity, "entity_type": entity_type},
    )
    if control_search:
        control_rows = tuple(
            row
            for row in control_rows
            if control_search.lower() in " ".join(str(value) for value in row.values()).lower()
        )
    _table(control_rows, empty="No control results match the selected filters.")

    st.subheader("Risk Indicators")
    risk_severity = _select_filter(
        "Risk severity", unique_values(state.risk_indicator_rows, "severity")
    )
    risk_category = _select_filter(
        "Risk category", unique_values(state.risk_indicator_rows, "category")
    )
    risk_rows = filter_rows(
        state.risk_indicator_rows, equals={"severity": risk_severity, "category": risk_category}
    )
    _table(risk_rows, empty="No risk indicators match the selected filters.")

    st.subheader("Evidence Reference Drill-through")
    evidence_rows = evidence_reference_rows(state)
    evidence_ref = _select_optional(
        "Evidence reference", unique_values(evidence_rows, "evidence_ref")
    )
    if evidence_ref is None:
        return
    _table(
        filter_rows(evidence_rows, equals={"evidence_ref": evidence_ref}),
        empty="No evidence reference rows match the selected reference.",
    )
    drill = drillthrough_by_evidence_ref(state, evidence_ref)
    for label, rows in drill.items():
        if label == "evidence_references":
            continue
        st.markdown(f"**{label.replace('_', ' ').title()}**")
        _table(rows, empty=f"No {label.replace('_', ' ')} found for {evidence_ref}.")


def main() -> None:
    st.set_page_config(page_title="Governance Reviewer Portal", layout="wide")
    st.title("Governance Reviewer Portal")
    try:
        state = load_reviewer_state()
    except MissingGeneratedOutputError as exc:
        st.error("Required generated governance outputs are missing.")
        st.code(str(exc), language="text")
        return

    st.sidebar.caption(f"Snapshot: {state.reporting_snapshot.snapshot_id}")
    st.sidebar.caption(f"Generated: {state.reporting_snapshot.generated_at.isoformat()}")
    page = st.sidebar.radio(
        "Section",
        (
            "Executive Governance Overview",
            "Data & Model Governance",
            "Research & Access Governance",
            "Audit & Evidence",
            "Compliance & Risk",
        ),
    )

    if page == "Executive Governance Overview":
        _overview_page(state)
    elif page == "Data & Model Governance":
        _data_model_page(state)
    elif page == "Research & Access Governance":
        _research_access_page(state)
    elif page == "Audit & Evidence":
        _audit_evidence_page(state)
    else:
        _compliance_risk_page(state)


if __name__ == "__main__":
    main()
