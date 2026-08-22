from datetime import datetime

from governance_platform.access import (
    REFERENCE_EVALUATION_TIME,
    generate_access_control_state,
)
from governance_platform.audit import build_evidence_pack, generate_audit_log
from governance_platform.compliance import GovernancePosture, evaluate_compliance
from governance_platform.inventory import generate_portfolio
from governance_platform.reporting import (
    MetricUnit,
    ReportingMetricDomain,
    build_reporting_snapshot,
    unresolved_source_refs,
)

GENERATED_AT = datetime(2025, 3, 21)
EVIDENCE_AT = datetime(2025, 3, 20)
COMPLIANCE_AT = datetime(2025, 3, 15)


def _snapshot():
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    evidence_pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=EVIDENCE_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    compliance = evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=COMPLIANCE_AT,
    )
    snapshot = build_reporting_snapshot(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        compliance,
        snapshot_id="RS-0001",
        generated_at=GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    return snapshot, inventory, access_state, audit_log, evidence_pack, compliance


def _metrics_by_name(snapshot):
    return {metric.metric_name: metric for metric in snapshot.all_metrics}


def test_snapshot_metric_calculations_cover_inventory_access_audit_compliance_and_risk() -> None:
    snapshot, *_ = _snapshot()
    metrics = _metrics_by_name(snapshot)

    assert metrics["total_datasets"].value == 6
    assert metrics["approved_datasets"].value == 5
    assert metrics["datasets_sensitivity_confidential"].value == 4
    assert metrics["total_models"].value == 5
    assert metrics["models_risk_tier_high"].value == 1
    assert metrics["total_research_projects"].value == 4
    assert metrics["projects_approval_state_approved"].value == 2

    assert metrics["total_access_requests"].value == 10
    assert metrics["approved_access_requests"].value == 3
    assert metrics["rejected_access_requests"].value == 7
    assert metrics["access_approval_rate"].value == 0.3
    assert metrics["active_grants"].value == 1
    assert metrics["expired_grants"].value == 1
    assert metrics["revoked_grants"].value == 1
    assert metrics["rejection_reason_research_use_not_allowed"].value == 2

    assert metrics["total_audit_events"].value == 37
    assert metrics["audit_events_type_access_rejected"].value == 7
    assert metrics["audit_completeness_status"].value is True
    assert metrics["evidence_completeness_status"].value is True
    assert metrics["traceable_correlation_chains"].value == 11

    assert metrics["controls_evaluated"].value == 52
    assert metrics["controls_passed"].value == 51
    assert metrics["control_warnings"].value == 1
    assert metrics["control_failures"].value == 0
    assert metrics["control_pass_rate"].value == 0.9808
    assert metrics["findings_domain_responsible_ai_readiness"].value == 1
    assert metrics["findings_severity_medium"].value == 1

    assert metrics["risk_indicator_count"].value == 1
    assert metrics["bounded_risk_score"].value == 3
    assert metrics["risk_indicators_severity_medium"].value == 1
    assert metrics["overall_governance_posture"].value == "attention_required"
    assert snapshot.posture == GovernancePosture.ATTENTION_REQUIRED


def test_snapshot_metric_ordering_and_domains_are_deterministic() -> None:
    first, *_ = _snapshot()
    second, *_ = _snapshot()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [metric.metric_id for metric in first.all_metrics] == [
        f"KPI-{index:04d}" for index in range(1, len(first.all_metrics) + 1)
    ]
    assert first.inventory_metrics[0].metric_domain == ReportingMetricDomain.INVENTORY_POSTURE
    assert first.risk_metrics[-1].metric_domain == ReportingMetricDomain.GOVERNANCE_POSTURE


def test_source_references_resolve_for_canonical_snapshot() -> None:
    snapshot, inventory, access_state, audit_log, evidence_pack, compliance = _snapshot()

    assert (
        unresolved_source_refs(
            snapshot, inventory, access_state, audit_log, evidence_pack, compliance
        )
        == ()
    )


def test_source_reference_integrity_reports_unknown_reference() -> None:
    snapshot, inventory, access_state, audit_log, evidence_pack, compliance = _snapshot()
    broken_metric = snapshot.inventory_metrics[0].model_copy(
        update={"source_refs": ("dataset:DS-9999",)}
    )
    broken_snapshot = snapshot.model_copy(
        update={"inventory_metrics": (broken_metric, *snapshot.inventory_metrics[1:])}
    )

    assert unresolved_source_refs(
        broken_snapshot, inventory, access_state, audit_log, evidence_pack, compliance
    ) == ("dataset:DS-9999",)


def test_snapshot_preserves_synthetic_data_safeguard_metric() -> None:
    snapshot, *_ = _snapshot()
    metric = _metrics_by_name(snapshot)["all_datasets_synthetic_only"]

    assert metric.value is True
    assert metric.unit == MetricUnit.BOOLEAN
    assert "adr:0001" in metric.source_refs
