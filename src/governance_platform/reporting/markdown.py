"""Markdown rendering for executive governance reporting snapshots."""

from __future__ import annotations

from governance_platform.reporting.entities import GovernanceKPI, ReportingSnapshot


def _metric(metrics: tuple[GovernanceKPI, ...], name: str) -> GovernanceKPI:
    for metric in metrics:
        if metric.metric_name == name:
            return metric
    raise KeyError(f"metric not found: {name}")


def _line(metrics: tuple[GovernanceKPI, ...], name: str, label: str) -> str:
    metric = _metric(metrics, name)
    return f"- **{label}:** {metric.value}"


def render_executive_summary_markdown(snapshot: ReportingSnapshot) -> str:
    """Render a concise executive summary from a reporting snapshot."""
    all_metrics = snapshot.all_metrics
    lines: list[str] = []
    lines.append("# Executive Governance Summary")
    lines.append("")
    lines.append(
        "> Local deterministic reporting over synthetic governance state. No Fabric or Power BI "
        "deployment exists."
    )
    lines.append("")
    lines.append(f"- **Snapshot ID:** {snapshot.snapshot_id}")
    lines.append(f"- **Generated at:** {snapshot.generated_at.isoformat()}")
    lines.append(f"- **Metrics as of:** {all_metrics[0].as_of.isoformat()}")
    lines.append(f"- **Governance posture:** {snapshot.posture.value}")
    lines.append("")

    lines.append("## Inventory")
    lines.append("")
    lines.append(_line(all_metrics, "total_datasets", "Total datasets"))
    lines.append(_line(all_metrics, "approved_datasets", "Approved datasets"))
    lines.append(_line(all_metrics, "all_datasets_synthetic_only", "All datasets synthetic only"))
    lines.append(_line(all_metrics, "total_models", "Total models"))
    lines.append(_line(all_metrics, "models_risk_tier_high", "High-risk models"))
    lines.append(_line(all_metrics, "total_research_projects", "Research projects"))
    lines.append("")

    lines.append("## Access")
    lines.append("")
    lines.append(_line(all_metrics, "total_access_requests", "Total requests"))
    lines.append(_line(all_metrics, "approved_access_requests", "Approved requests"))
    lines.append(_line(all_metrics, "rejected_access_requests", "Rejected requests"))
    lines.append(_line(all_metrics, "access_approval_rate", "Approval rate"))
    lines.append(_line(all_metrics, "active_grants", "Active grants"))
    lines.append(_line(all_metrics, "expired_grants", "Expired grants"))
    lines.append(_line(all_metrics, "revoked_grants", "Revoked grants"))
    lines.append("")

    lines.append("## Audit and Evidence")
    lines.append("")
    lines.append(_line(all_metrics, "total_audit_events", "Audit events"))
    lines.append(_line(all_metrics, "audit_completeness_status", "Audit completeness"))
    lines.append(_line(all_metrics, "evidence_completeness_status", "Evidence completeness"))
    lines.append(_line(all_metrics, "traceable_correlation_chains", "Traceable chains"))
    lines.append("")

    lines.append("## Compliance and Risk")
    lines.append("")
    lines.append(_line(all_metrics, "controls_evaluated", "Controls evaluated"))
    lines.append(_line(all_metrics, "controls_passed", "Controls passed"))
    lines.append(_line(all_metrics, "control_warnings", "Warnings"))
    lines.append(_line(all_metrics, "control_failures", "Failures"))
    lines.append(_line(all_metrics, "control_pass_rate", "Control pass rate"))
    lines.append(_line(all_metrics, "risk_indicator_count", "Risk indicators"))
    lines.append(_line(all_metrics, "bounded_risk_score", "Bounded risk score"))
    lines.append("")

    warnings = _metric(all_metrics, "control_warnings").value
    failures = _metric(all_metrics, "control_failures").value
    lines.append("## Notable Findings")
    lines.append("")
    if warnings == 0 and failures == 0:
        lines.append("No warning or failed control results are present in the reporting snapshot.")
    else:
        lines.append(
            f"The reporting snapshot includes {warnings} warning control result(s) and "
            f"{failures} failed control result(s), sourced from the compliance assessment."
        )
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.extend(f"- {limitation}" for limitation in snapshot.limitations)
    lines.append("")
    return "\n".join(lines)
