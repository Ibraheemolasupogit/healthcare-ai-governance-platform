from datetime import datetime

import pytest

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
from governance_platform.compliance import evaluate_compliance, export_compliance_assessment
from governance_platform.inventory import export_portfolio, generate_portfolio
from governance_platform.reporting import build_reporting_snapshot, export_reporting_snapshot
from governance_platform.reviewer import (
    MissingGeneratedOutputError,
    drillthrough_by_evidence_ref,
    drillthrough_by_grant,
    drillthrough_by_project,
    drillthrough_by_request,
    evidence_reference_rows,
    filter_rows,
    kpi_by_name,
    kpi_prefix_rows,
    kpi_value,
    load_reviewer_state,
    missing_output_paths,
    rejection_reason_rows,
    status_counts,
    synthetic_boundary_text,
    unique_values,
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


@pytest.fixture()
def reviewer_state(tmp_path):
    _write_outputs(tmp_path)
    return load_reviewer_state(tmp_path)


def test_load_reviewer_state_reads_canonical_outputs(reviewer_state) -> None:
    assert reviewer_state.reporting_snapshot.snapshot_id == "RS-0001"
    assert len(reviewer_state.dataset_rows) == 6
    assert len(reviewer_state.model_rows) == 5
    assert len(reviewer_state.project_rows) == 4
    assert len(reviewer_state.request_rows) == 10
    assert len(reviewer_state.grant_rows) == 3
    assert len(reviewer_state.audit_event_rows) == 37
    assert len(reviewer_state.control_result_rows) == 52
    assert len(reviewer_state.kpis) == 72


def test_missing_output_handling_reports_generation_commands(tmp_path) -> None:
    missing = missing_output_paths(tmp_path)

    assert missing
    with pytest.raises(MissingGeneratedOutputError) as exc:
        load_reviewer_state(tmp_path)
    message = str(exc.value)
    assert "python3 scripts/generate_reporting.py" in message
    assert "inventory_portfolio.json" in message


def test_kpi_lookup_and_prefix_rows(reviewer_state) -> None:
    assert kpi_value(reviewer_state, "bounded_risk_score") == 3
    assert kpi_by_name(reviewer_state, "overall_governance_posture").value == "attention_required"

    severity_rows = kpi_prefix_rows(
        reviewer_state, prefix="findings_severity_", label_name="severity"
    )
    assert {row["severity"]: row["count"] for row in severity_rows}["medium"] == 1


def test_filtering_helpers_and_status_aggregation_are_stable(reviewer_state) -> None:
    approved_datasets = filter_rows(
        reviewer_state.dataset_rows, equals={"approval_status": "approved"}
    )
    clinical = filter_rows(reviewer_state.dataset_rows, contains={"name": "clinical"})

    assert len(approved_datasets) == 5
    assert len(clinical) == 1
    assert unique_values(reviewer_state.grant_rows, "status_as_of_evaluation") == (
        "active",
        "expired",
        "revoked",
    )
    assert status_counts(reviewer_state.grant_rows, "status_as_of_evaluation") == {
        "active": 1,
        "expired": 1,
        "revoked": 1,
    }


def test_project_request_and_grant_drillthrough(reviewer_state) -> None:
    project = drillthrough_by_project(reviewer_state, "RP-0001")
    request = drillthrough_by_request(reviewer_state, "AR-0001")
    grant = drillthrough_by_grant(reviewer_state, "AG-0001")

    assert len(project["requests"]) >= 1
    assert request["decision"][0]["decision_id"] == "AD-0001"
    assert grant["grant"][0]["request_id"] == "AR-0001"
    assert any(row["event_type"] == "grant_created" for row in grant["audit_events"])
    assert any("access_grant:AG-0001" in row["evidence_refs"] for row in grant["control_results"])


def test_evidence_reference_index_and_drillthrough(reviewer_state) -> None:
    rows = evidence_reference_rows(reviewer_state)
    model_reference = drillthrough_by_evidence_ref(reviewer_state, "model:MD-0003")
    grant_reference = drillthrough_by_evidence_ref(reviewer_state, "access_grant:AG-0001")

    assert rows == tuple(
        sorted(rows, key=lambda row: (row["evidence_ref"], row["source_type"], row["source_id"]))
    )
    assert any(row["result_id"] == "CR-0034" for row in model_reference["control_results"])
    assert model_reference["models"][0]["model_id"] == "MD-0003"
    assert grant_reference["grant"][0]["grant_id"] == "AG-0001"
    assert any(row["event_type"] == "grant_created" for row in grant_reference["audit_events"])


def test_rejection_reason_rows_are_reporting_backed(reviewer_state) -> None:
    rows = rejection_reason_rows(reviewer_state)
    reasons = {row["reason"]: row["count"] for row in rows}

    assert reasons["unknown_research_project"] == 1
    assert reasons["research_use_not_allowed"] == 2
    assert all("access_control_state" in row["source_refs"] for row in rows)


def test_reviewer_rows_are_deterministically_sorted(reviewer_state) -> None:
    assert [row["dataset_id"] for row in reviewer_state.dataset_rows] == sorted(
        row["dataset_id"] for row in reviewer_state.dataset_rows
    )
    assert [row["event_id"] for row in reviewer_state.audit_event_rows][:2] == [
        "AE-0001",
        "AE-0002",
    ]
    assert [metric.metric_id for metric in reviewer_state.kpis] == [
        f"KPI-{index:04d}" for index in range(1, len(reviewer_state.kpis) + 1)
    ]


def test_synthetic_data_safeguards_are_visible(reviewer_state) -> None:
    assert all(row["contains_synthetic_data_only"] is True for row in reviewer_state.dataset_rows)
    assert kpi_value(reviewer_state, "all_datasets_synthetic_only") is True
    assert "No real patient data" in synthetic_boundary_text()
