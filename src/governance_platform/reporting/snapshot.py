"""Deterministic reporting KPI derivation over existing governance state."""

from __future__ import annotations

from datetime import datetime

from governance_platform.access import (
    AccessControlPortfolio,
    AccessReviewSummary,
    build_access_summary,
)
from governance_platform.audit import (
    AuditLog,
    EvidencePack,
    build_audit_summary,
    check_completeness,
)
from governance_platform.compliance import ComplianceAssessment, ControlSeverity
from governance_platform.inventory import (
    ApprovalStatus,
    InventoryPortfolio,
    RiskTier,
    SensitivityClassification,
)
from governance_platform.inventory import (
    build_summary as build_inventory_summary,
)
from governance_platform.reporting.entities import GovernanceKPI, MetricValue, ReportingSnapshot
from governance_platform.reporting.enums import MetricUnit, ReportingMetricDomain

REPORTING_LIMITATIONS: tuple[str, ...] = (
    "This is a local deterministic reporting snapshot over synthetic governance state.",
    "No Microsoft Fabric workspace, Power BI report, semantic model deployment, or live refresh "
    "exists.",
    "No Snowflake, Purview, Entra ID, Salesforce, alerting, or real-time monitoring integration "
    "exists.",
    "Reporting metrics are derived from existing local state and do not assert regulatory "
    "certification.",
)


def _kpi(
    *,
    metric_name: str,
    metric_domain: ReportingMetricDomain,
    value: MetricValue,
    unit: MetricUnit,
    as_of: datetime,
    source_refs: tuple[str, ...],
    description: str,
) -> GovernanceKPI:
    return GovernanceKPI(
        metric_id="KPI-0000",
        metric_name=metric_name,
        metric_domain=metric_domain,
        value=value,
        unit=unit,
        as_of=as_of,
        source_refs=source_refs,
        description=description,
    )


def _with_metric_ids(metrics: tuple[GovernanceKPI, ...]) -> tuple[GovernanceKPI, ...]:
    return tuple(
        metric.model_copy(update={"metric_id": f"KPI-{index:04d}"})
        for index, metric in enumerate(metrics, start=1)
    )


def _inventory_metrics(
    inventory: InventoryPortfolio, *, as_of: datetime
) -> tuple[GovernanceKPI, ...]:
    summary = build_inventory_summary(inventory)
    metrics: list[GovernanceKPI] = [
        _kpi(
            metric_name="total_datasets",
            metric_domain=ReportingMetricDomain.INVENTORY_POSTURE,
            value=summary.entity_counts.datasets,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("inventory_portfolio",),
            description="Total datasets registered in the synthetic inventory.",
        ),
        _kpi(
            metric_name="approved_datasets",
            metric_domain=ReportingMetricDomain.DATASET_GOVERNANCE,
            value=summary.dataset_approval_status[ApprovalStatus.APPROVED.value],
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("inventory_portfolio",),
            description="Datasets with approval_status=approved.",
        ),
        _kpi(
            metric_name="all_datasets_synthetic_only",
            metric_domain=ReportingMetricDomain.DATASET_GOVERNANCE,
            value=summary.all_datasets_synthetic_only,
            unit=MetricUnit.BOOLEAN,
            as_of=as_of,
            source_refs=("inventory_portfolio", "adr:0001"),
            description="Whether every dataset asserts contains_synthetic_data_only=true.",
        ),
    ]
    for sensitivity in SensitivityClassification:
        metrics.append(
            _kpi(
                metric_name=f"datasets_sensitivity_{sensitivity.value}",
                metric_domain=ReportingMetricDomain.DATASET_GOVERNANCE,
                value=summary.dataset_sensitivity_classification[sensitivity.value],
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("inventory_portfolio",),
                description=f"Datasets classified as {sensitivity.value}.",
            )
        )
    metrics.extend(
        [
            _kpi(
                metric_name="total_models",
                metric_domain=ReportingMetricDomain.MODEL_GOVERNANCE,
                value=summary.entity_counts.models,
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("inventory_portfolio",),
                description="Total AI/ML models registered in the synthetic inventory.",
            ),
        ]
    )
    for risk_tier in RiskTier:
        metrics.append(
            _kpi(
                metric_name=f"models_risk_tier_{risk_tier.value}",
                metric_domain=ReportingMetricDomain.MODEL_GOVERNANCE,
                value=summary.model_risk_tier[risk_tier.value],
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("inventory_portfolio",),
                description=f"Models classified as {risk_tier.value} risk.",
            )
        )
    metrics.append(
        _kpi(
            metric_name="total_research_projects",
            metric_domain=ReportingMetricDomain.RESEARCH_GOVERNANCE,
            value=summary.entity_counts.research_projects,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("inventory_portfolio",),
            description="Total research projects registered in the synthetic inventory.",
        )
    )
    for approval_status in ApprovalStatus:
        metrics.append(
            _kpi(
                metric_name=f"projects_approval_state_{approval_status.value}",
                metric_domain=ReportingMetricDomain.RESEARCH_GOVERNANCE,
                value=summary.research_project_approval_status[approval_status.value],
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("inventory_portfolio",),
                description=f"Research projects with approval_status={approval_status.value}.",
            )
        )
    return tuple(metrics)


def _access_metrics(summary: AccessReviewSummary, *, as_of: datetime) -> tuple[GovernanceKPI, ...]:
    total = summary.total_requests
    approved = summary.request_status["approved"]
    rejected = summary.request_status["rejected"]
    approval_rate = round(approved / total, 4) if total else 0
    metrics: list[GovernanceKPI] = [
        _kpi(
            metric_name="total_access_requests",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=total,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Total access requests in the deterministic access-control state.",
        ),
        _kpi(
            metric_name="approved_access_requests",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=approved,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Access requests finalized with status=approved.",
        ),
        _kpi(
            metric_name="rejected_access_requests",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=rejected,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Access requests finalized with status=rejected.",
        ),
        _kpi(
            metric_name="access_approval_rate",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=approval_rate,
            unit=MetricUnit.PERCENT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Approved requests divided by total requests.",
        ),
        _kpi(
            metric_name="active_grants",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=summary.grant_status.active,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Grants active at the supplied evaluation timestamp.",
        ),
        _kpi(
            metric_name="expired_grants",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=summary.grant_status.expired,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Issued grants whose expiry is before the evaluation timestamp.",
        ),
        _kpi(
            metric_name="revoked_grants",
            metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
            value=summary.grant_status.revoked,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("access_control_state",),
            description="Grants explicitly revoked in the access-control state.",
        ),
    ]
    for reason, count in summary.rejection_reason_categories.items():
        metrics.append(
            _kpi(
                metric_name=f"rejection_reason_{reason}",
                metric_domain=ReportingMetricDomain.ACCESS_CONTROL,
                value=count,
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("access_control_state", "inventory_portfolio"),
                description=f"Rejected-request eligibility findings for {reason}.",
            )
        )
    return tuple(metrics)


def _audit_metrics(
    audit_log: AuditLog,
    evidence_pack: EvidencePack,
    access_state: AccessControlPortfolio,
    inventory: InventoryPortfolio,
    *,
    as_of: datetime,
) -> tuple[GovernanceKPI, ...]:
    summary = build_audit_summary(audit_log, access_state)
    completeness_problems = check_completeness(audit_log, inventory, access_state)
    metrics: list[GovernanceKPI] = [
        _kpi(
            metric_name="total_audit_events",
            metric_domain=ReportingMetricDomain.AUDIT_EVIDENCE,
            value=summary.total_events,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=("audit_events",),
            description="Total audit events in the deterministic audit log.",
        )
    ]
    for event_type, count in summary.events_by_type.items():
        metrics.append(
            _kpi(
                metric_name=f"audit_events_type_{event_type}",
                metric_domain=ReportingMetricDomain.AUDIT_EVIDENCE,
                value=count,
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("audit_events",),
                description=f"Audit events with event_type={event_type}.",
            )
        )
    metrics.extend(
        [
            _kpi(
                metric_name="audit_completeness_status",
                metric_domain=ReportingMetricDomain.AUDIT_EVIDENCE,
                value=not completeness_problems,
                unit=MetricUnit.BOOLEAN,
                as_of=as_of,
                source_refs=("audit_events", "access_control_state", "inventory_portfolio"),
                description="Whether audit completeness checks report no missing evidence.",
            ),
            _kpi(
                metric_name="evidence_completeness_status",
                metric_domain=ReportingMetricDomain.AUDIT_EVIDENCE,
                value=evidence_pack.completeness.complete,
                unit=MetricUnit.BOOLEAN,
                as_of=as_of,
                source_refs=(f"evidence_pack:{evidence_pack.evidence_pack_id}",),
                description="Whether the generated evidence pack reports complete evidence.",
            ),
            _kpi(
                metric_name="traceable_correlation_chains",
                metric_domain=ReportingMetricDomain.AUDIT_EVIDENCE,
                value=len(evidence_pack.correlation_groups),
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=("audit_events", f"evidence_pack:{evidence_pack.evidence_pack_id}"),
                description="Correlation groups represented in the evidence pack.",
            ),
        ]
    )
    return tuple(metrics)


def _compliance_metrics(
    assessment: ComplianceAssessment, *, as_of: datetime
) -> tuple[GovernanceKPI, ...]:
    summary = assessment.summary
    metrics: list[GovernanceKPI] = [
        _kpi(
            metric_name="controls_evaluated",
            metric_domain=ReportingMetricDomain.COMPLIANCE,
            value=summary.total_controls_evaluated,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Total control results evaluated in the compliance assessment.",
        ),
        _kpi(
            metric_name="controls_passed",
            metric_domain=ReportingMetricDomain.COMPLIANCE,
            value=summary.passed_controls,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Control results with status=pass.",
        ),
        _kpi(
            metric_name="control_warnings",
            metric_domain=ReportingMetricDomain.COMPLIANCE,
            value=summary.warning_controls,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Control results with status=warning.",
        ),
        _kpi(
            metric_name="control_failures",
            metric_domain=ReportingMetricDomain.COMPLIANCE,
            value=summary.failed_controls,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Control results with status=fail.",
        ),
        _kpi(
            metric_name="control_pass_rate",
            metric_domain=ReportingMetricDomain.COMPLIANCE,
            value=summary.pass_rate,
            unit=MetricUnit.PERCENT,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Passing control results divided by total control results.",
        ),
    ]
    for domain, count in summary.findings_by_domain.items():
        metrics.append(
            _kpi(
                metric_name=f"findings_domain_{domain}",
                metric_domain=ReportingMetricDomain.COMPLIANCE,
                value=count,
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
                description=f"Warning or failed control findings in domain {domain}.",
            )
        )
    for severity, count in summary.findings_by_severity.items():
        metrics.append(
            _kpi(
                metric_name=f"findings_severity_{severity}",
                metric_domain=ReportingMetricDomain.COMPLIANCE,
                value=count,
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
                description=f"Warning or failed control findings with severity {severity}.",
            )
        )
    return tuple(metrics)


def _risk_metrics(
    assessment: ComplianceAssessment, *, as_of: datetime
) -> tuple[GovernanceKPI, ...]:
    summary = assessment.summary
    metrics: list[GovernanceKPI] = [
        _kpi(
            metric_name="risk_indicator_count",
            metric_domain=ReportingMetricDomain.RISK,
            value=summary.number_of_risk_indicators,
            unit=MetricUnit.COUNT,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Risk indicators derived from non-passing compliance findings.",
        ),
        _kpi(
            metric_name="bounded_risk_score",
            metric_domain=ReportingMetricDomain.RISK,
            value=summary.total_bounded_risk_score,
            unit=MetricUnit.SCORE,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Total bounded risk score from the compliance assessment.",
        ),
    ]
    for severity in ControlSeverity:
        metrics.append(
            _kpi(
                metric_name=f"risk_indicators_severity_{severity.value}",
                metric_domain=ReportingMetricDomain.RISK,
                value=sum(
                    1 for indicator in assessment.risk_indicators if indicator.severity == severity
                ),
                unit=MetricUnit.COUNT,
                as_of=as_of,
                source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
                description=f"Risk indicators with severity {severity.value}.",
            )
        )
    metrics.append(
        _kpi(
            metric_name="overall_governance_posture",
            metric_domain=ReportingMetricDomain.GOVERNANCE_POSTURE,
            value=assessment.posture.value,
            unit=MetricUnit.STATUS,
            as_of=as_of,
            source_refs=(f"compliance_assessment:{assessment.assessment_id}",),
            description="Overall posture from the compliance assessment.",
        )
    )
    return tuple(metrics)


def build_reporting_snapshot(
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
    audit_log: AuditLog,
    evidence_pack: EvidencePack,
    compliance_assessment: ComplianceAssessment,
    *,
    snapshot_id: str,
    generated_at: datetime,
    evaluated_at: datetime,
) -> ReportingSnapshot:
    """Build a deterministic reporting snapshot from existing governance state."""
    access_summary = build_access_summary(access_state, inventory, evaluated_at=evaluated_at)
    raw_inventory = _inventory_metrics(inventory, as_of=evaluated_at)
    raw_access = _access_metrics(access_summary, as_of=evaluated_at)
    raw_audit = _audit_metrics(
        audit_log, evidence_pack, access_state, inventory, as_of=evaluated_at
    )
    raw_compliance = _compliance_metrics(compliance_assessment, as_of=evaluated_at)
    raw_risk = _risk_metrics(compliance_assessment, as_of=evaluated_at)

    all_metrics = _with_metric_ids(
        (*raw_inventory, *raw_access, *raw_audit, *raw_compliance, *raw_risk)
    )
    inventory_count = len(raw_inventory)
    access_count = len(raw_access)
    audit_count = len(raw_audit)
    compliance_count = len(raw_compliance)

    inventory_metrics = all_metrics[:inventory_count]
    access_metrics = all_metrics[inventory_count : inventory_count + access_count]
    audit_start = inventory_count + access_count
    audit_metrics = all_metrics[audit_start : audit_start + audit_count]
    compliance_start = audit_start + audit_count
    compliance_metrics = all_metrics[compliance_start : compliance_start + compliance_count]
    risk_metrics = all_metrics[compliance_start + compliance_count :]

    return ReportingSnapshot(
        snapshot_id=snapshot_id,
        generated_at=generated_at,
        inventory_metrics=inventory_metrics,
        access_metrics=access_metrics,
        audit_metrics=audit_metrics,
        compliance_metrics=compliance_metrics,
        risk_metrics=risk_metrics,
        posture=compliance_assessment.posture,
        limitations=REPORTING_LIMITATIONS,
    )
