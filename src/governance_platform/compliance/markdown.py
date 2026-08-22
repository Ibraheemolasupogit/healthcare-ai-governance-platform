"""Markdown rendering for deterministic compliance assessments."""

from __future__ import annotations

from governance_platform.compliance.entities import ComplianceAssessment
from governance_platform.compliance.risk import (
    ATTENTION_REQUIRED_SCORE_THRESHOLD,
    HIGH_RISK_FAILURE_THRESHOLD,
    HIGH_RISK_SCORE_THRESHOLD,
    MAX_TOTAL_RISK_SCORE,
    SEVERITY_SCORES,
)


def _dict_table(rows: dict[str, int]) -> str:
    lines = ["| Value | Count |", "| --- | --- |"]
    lines.extend(f"| {key} | {count} |" for key, count in rows.items())
    return "\n".join(lines)


def render_governance_posture_markdown(assessment: ComplianceAssessment) -> str:
    """Render ``assessment`` as a reviewer-readable governance posture report."""
    summary = assessment.summary
    lines: list[str] = []
    lines.append("# Governance Posture Assessment")
    lines.append("")
    lines.append(
        "> Local, deterministic governance simulation. This is not regulatory certification, "
        "live monitoring, or production policy enforcement."
    )
    lines.append("")
    lines.append(f"- **Assessment ID:** {assessment.assessment_id}")
    lines.append(
        f"- **Evaluation timestamp:** {assessment.evaluated_at.isoformat()} "
        "(explicitly supplied, not read from the system clock)"
    )
    lines.append(f"- **Scope:** {assessment.scope}")
    lines.append("")

    lines.append("## Summary metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Controls evaluated | {summary.total_controls_evaluated} |")
    lines.append(f"| Passed controls | {summary.passed_controls} |")
    lines.append(f"| Warnings | {summary.warning_controls} |")
    lines.append(f"| Failures | {summary.failed_controls} |")
    lines.append(f"| Pass rate | {summary.pass_rate:.2%} |")
    lines.append(f"| Risk indicators | {summary.number_of_risk_indicators} |")
    lines.append(
        f"| Total bounded risk score | {summary.total_bounded_risk_score}/{MAX_TOTAL_RISK_SCORE} |"
    )
    lines.append(f"| Overall posture | {assessment.posture.value} |")
    lines.append("")

    lines.append("## Posture thresholds")
    lines.append("")
    lines.append("| Posture | Deterministic threshold |")
    lines.append("| --- | --- |")
    lines.append("| healthy | No warnings or failures. |")
    lines.append(
        "| attention_required | Any warning/failure, or bounded score "
        f">= {ATTENTION_REQUIRED_SCORE_THRESHOLD}. |"
    )
    lines.append(
        "| high_risk | Any critical failure, "
        f">= {HIGH_RISK_FAILURE_THRESHOLD} failures, or bounded score "
        f">= {HIGH_RISK_SCORE_THRESHOLD}. |"
    )
    lines.append("")

    lines.append("## Risk score method")
    lines.append("")
    lines.append("| Severity | Score |")
    lines.append("| --- | --- |")
    for severity, score in SEVERITY_SCORES.items():
        lines.append(f"| {severity.value} | {score} |")
    lines.append("")
    lines.append(
        "Only warning and failed control results create risk indicators. The total score is capped "
        f"at {MAX_TOTAL_RISK_SCORE}; it is not predictive modelling."
    )
    lines.append("")

    lines.append("## Findings by severity")
    lines.append("")
    lines.append(_dict_table(summary.findings_by_severity))
    lines.append("")

    lines.append("## Findings by domain")
    lines.append("")
    lines.append(_dict_table(summary.findings_by_domain))
    lines.append("")

    lines.append("## Risk indicators")
    lines.append("")
    if assessment.risk_indicators:
        lines.append("| Indicator | Entity | Category | Severity | Score | Rationale |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for indicator in assessment.risk_indicators:
            lines.append(
                f"| {indicator.indicator_id} | {indicator.entity_type.value}:"
                f"{indicator.entity_id} | {indicator.category.value} | "
                f"{indicator.severity.value} | {indicator.score} | {indicator.rationale} |"
            )
    else:
        lines.append("No risk indicators were derived.")
    lines.append("")

    lines.append("## Evidence references")
    lines.append("")
    evidence_refs = sorted(
        {ref for result in assessment.control_results for ref in result.evidence_refs}
    )
    if evidence_refs:
        lines.extend(f"- {ref}" for ref in evidence_refs)
    else:
        lines.append("No evidence references recorded.")
    lines.append("")

    lines.append("## Non-passing control results")
    lines.append("")
    non_passing = [result for result in assessment.control_results if result.status.value != "pass"]
    if non_passing:
        lines.append("| Result | Control | Status | Severity | Entity | Finding |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for result in non_passing:
            lines.append(
                f"| {result.result_id} | {result.control_id} | {result.status.value} | "
                f"{result.severity.value} | {result.entity_type.value}:{result.entity_id} | "
                f"{result.finding_code.value}: {result.message} |"
            )
    else:
        lines.append("All evaluated controls passed.")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.extend(f"- {limitation}" for limitation in assessment.limitations)
    lines.append("")
    return "\n".join(lines)
