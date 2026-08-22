from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.access import (
    REFERENCE_EVALUATION_TIME,
    export_access_state,
    generate_access_control_state,
)
from governance_platform.audit import (
    build_audit_summary,
    build_evidence_pack,
    export_audit_log,
    export_audit_summary,
    export_evidence_pack,
    generate_audit_log,
)
from governance_platform.compliance import (
    AssuranceHistory,
    AssuranceSnapshot,
    ControlSeverity,
    DriftType,
    GovernancePosture,
    build_assurance_history_bundle,
    build_assurance_snapshot,
    build_controlled_comparison_assessment,
    build_policy_catalog_bundle,
    compare_assurance_snapshots,
    evaluate_compliance,
    export_assurance_history_bundle,
    export_compliance_assessment,
    export_policy_catalog_bundle,
    load_assurance_comparison,
    load_assurance_history,
    load_compliance_assessment,
    load_control_catalog,
    validate_assurance_history_files,
)
from governance_platform.inventory import export_portfolio, generate_portfolio
from governance_platform.reporting import build_reporting_snapshot, export_reporting_snapshot
from governance_platform.reviewer import (
    build_reviewer_evidence_index,
    load_reviewer_assurance_state,
    load_reviewer_state,
)

EVIDENCE_GENERATED_AT = datetime(2025, 3, 20)
COMPLIANCE_EVALUATED_AT = datetime(2025, 3, 15)
REPORTING_GENERATED_AT = datetime(2025, 3, 21)


def _write_outputs(root):
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    evidence_pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=EVIDENCE_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    compliance = evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=COMPLIANCE_EVALUATED_AT,
    )
    reporting = build_reporting_snapshot(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        compliance,
        snapshot_id="RS-0001",
        generated_at=REPORTING_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )

    export_portfolio(inventory, root / "inventory")
    export_access_state(
        access_state,
        inventory,
        evaluated_at=REFERENCE_EVALUATION_TIME,
        output_dir=root / "access",
    )
    export_audit_log(audit_log, root / "evidence")
    export_audit_summary(build_audit_summary(audit_log, access_state), root / "evidence")
    export_evidence_pack(evidence_pack, root / "evidence")
    export_compliance_assessment(compliance, root / "compliance")
    export_reporting_snapshot(reporting, root / "reporting")
    return compliance


@pytest.fixture()
def assurance_context(tmp_path):
    _write_outputs(tmp_path)
    assessment = load_compliance_assessment(tmp_path / "compliance")
    reviewer_state = load_reviewer_state(tmp_path)
    known_refs = {entry.evidence_ref for entry in build_reviewer_evidence_index(reviewer_state)}
    policy_bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    export_policy_catalog_bundle(policy_bundle, tmp_path / "policy")
    return tmp_path, assessment, load_control_catalog(tmp_path / "policy")


def test_assurance_snapshot_model_validation(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    snapshot = build_assurance_snapshot(
        assessment,
        catalog,
        snapshot_id="AS-0001",
        captured_at=datetime(2025, 3, 15),
    )

    assert isinstance(snapshot, AssuranceSnapshot)
    assert snapshot.snapshot_id == "AS-0001"
    assert snapshot.posture == GovernancePosture.ATTENTION_REQUIRED
    assert snapshot.bounded_risk_score == 3
    assert snapshot.synthetic_data_only is True
    with pytest.raises(ValidationError):
        snapshot.snapshot_id = "changed"  # type: ignore[misc]


def test_history_rejects_duplicate_snapshot_ids(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    snapshot = build_assurance_snapshot(
        assessment,
        catalog,
        snapshot_id="AS-0001",
        captured_at=datetime(2025, 3, 15),
    )

    with pytest.raises(ValidationError, match="duplicate assurance snapshot"):
        AssuranceHistory(snapshots=(snapshot, snapshot))


def test_history_orders_snapshots_by_explicit_timestamp(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    first = build_assurance_snapshot(
        assessment,
        catalog,
        snapshot_id="AS-0001",
        captured_at=datetime(2025, 3, 15),
    )
    second = build_assurance_snapshot(
        assessment,
        catalog,
        snapshot_id="AS-0002",
        captured_at=datetime(2025, 3, 22),
    )
    history = AssuranceHistory(snapshots=(second, first))

    assert [snapshot.snapshot_id for snapshot in history.ordered_snapshots()] == [
        "AS-0001",
        "AS-0002",
    ]
    assert history.prior_current_pair() == (first, second)


def test_controlled_comparison_has_resolved_and_new_findings(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    bundle = build_assurance_history_bundle(assessment, catalog)
    comparison = bundle.comparison

    assert comparison.previous_snapshot_id == "AS-0001"
    assert comparison.current_snapshot_id == "AS-0002"
    assert comparison.previous_bounded_risk_score == 3
    assert comparison.current_bounded_risk_score == 1
    assert comparison.risk_score_delta == -2
    assert comparison.posture_change == DriftType.UNCHANGED
    assert comparison.summary["resolved_findings"] == 1
    assert comparison.summary["new_findings"] == 1
    assert any(
        drift.control_id == "CTRL-0014"
        and drift.entity_id == "MD-0003"
        and drift.drift_type == DriftType.RESOLVED_FINDING
        for drift in comparison.control_drifts
    )
    assert any(
        drift.control_id == "CTRL-0005" and drift.drift_type == DriftType.NEW_FINDING
        for drift in comparison.control_drifts
    )


def test_control_drift_retains_policy_and_evidence_linkage(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    comparison = build_assurance_history_bundle(assessment, catalog).comparison
    readiness = next(
        drift for drift in comparison.control_drifts if drift.control_id == "CTRL-0014"
    )

    assert readiness.policy_ids == ("POL-0008",)
    assert readiness.evidence_requirement == "ER-CTRL-0014-01"
    assert "model:MD-0003" in readiness.evidence_refs
    assert readiness.control_objective
    assert readiness.reviewer_guidance


def test_risk_drift_identifies_category_and_total_delta(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    comparison = build_assurance_history_bundle(assessment, catalog).comparison

    assert any(
        drift.category == "POL-0008"
        and drift.previous_score == 3
        and drift.current_score == 0
        and drift.drift_type == DriftType.IMPROVED
        for drift in comparison.risk_drifts
    )
    assert any(
        drift.category == "POL-0009"
        and drift.previous_score == 0
        and drift.current_score == 1
        and drift.drift_type == DriftType.DEGRADED
        for drift in comparison.risk_drifts
    )
    assert any(
        drift.category == "total_bounded_risk_score" and drift.score_delta == -2
        for drift in comparison.risk_drifts
    )


def test_missing_control_handling_reports_changed_absent_result(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    baseline = build_assurance_snapshot(
        assessment,
        catalog,
        snapshot_id="AS-0001",
        captured_at=datetime(2025, 3, 15),
    )
    current = baseline.model_copy(
        update={
            "snapshot_id": "AS-0002",
            "captured_at": datetime(2025, 3, 22),
            "control_results": baseline.control_results[1:],
        }
    )

    comparison = compare_assurance_snapshots(baseline, current, catalog)

    assert any(drift.current_status == "missing" for drift in comparison.control_drifts)


def test_severity_change_is_classified(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    baseline = build_assurance_snapshot(
        build_controlled_comparison_assessment(assessment),
        catalog,
        snapshot_id="AS-0001",
        captured_at=datetime(2025, 3, 15),
    )
    changed_result = baseline.control_results[0].model_copy(
        update={"severity": ControlSeverity.LOW}
    )
    current = baseline.model_copy(
        update={
            "snapshot_id": "AS-0002",
            "captured_at": datetime(2025, 3, 22),
            "control_results": (changed_result, *baseline.control_results[1:]),
        }
    )

    comparison = compare_assurance_snapshots(baseline, current, catalog)

    assert any(
        drift.drift_type in {DriftType.SEVERITY_INCREASED, DriftType.SEVERITY_DECREASED}
        for drift in comparison.control_drifts
    )


def test_posture_transition_is_classified(assurance_context) -> None:
    _, assessment, catalog = assurance_context
    baseline = build_assurance_snapshot(
        assessment,
        catalog,
        snapshot_id="AS-0001",
        captured_at=datetime(2025, 3, 15),
    )
    current = baseline.model_copy(
        update={
            "snapshot_id": "AS-0002",
            "captured_at": datetime(2025, 3, 22),
            "posture": GovernancePosture.HIGH_RISK,
            "bounded_risk_score": 30,
        }
    )

    comparison = compare_assurance_snapshots(baseline, current, catalog)

    assert comparison.posture_change == DriftType.POSTURE_DEGRADED
    assert comparison.summary["posture_transition"] == "attention_required->high_risk"


def test_assurance_export_reload_and_validation(assurance_context, tmp_path) -> None:
    _, assessment, catalog = assurance_context
    bundle = build_assurance_history_bundle(assessment, catalog)
    out = tmp_path / "assurance"

    export_assurance_history_bundle(bundle, out)

    assert validate_assurance_history_files(out) == []
    assert load_assurance_history(out).ordered_snapshots() == bundle.history.ordered_snapshots()
    assert load_assurance_comparison(out) == bundle.comparison
    assert (
        (out / "assurance_drift_report.md")
        .read_text(encoding="utf-8")
        .startswith("# Assurance Drift Report")
    )


def test_assurance_exports_are_byte_identical(assurance_context, tmp_path) -> None:
    _, assessment, catalog = assurance_context
    bundle = build_assurance_history_bundle(assessment, catalog)
    first = tmp_path / "first"
    second = tmp_path / "second"

    export_assurance_history_bundle(bundle, first)
    export_assurance_history_bundle(bundle, second)

    first_files = sorted(path.name for path in first.iterdir())
    assert first_files == sorted(path.name for path in second.iterdir())
    for filename in first_files:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_reviewer_assurance_data_loading(assurance_context) -> None:
    root, assessment, catalog = assurance_context
    bundle = build_assurance_history_bundle(assessment, catalog)
    export_assurance_history_bundle(bundle, root / "assurance")

    assurance_state = load_reviewer_assurance_state(root)

    assert len(assurance_state.snapshot_rows) == 2
    assert len(assurance_state.control_drift_rows) == len(bundle.comparison.control_drifts)
    assert len(assurance_state.risk_drift_rows) == len(bundle.comparison.risk_drifts)
    assert assurance_state.comparison.synthetic_data_only is True
