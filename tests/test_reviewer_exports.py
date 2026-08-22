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
    ReviewerBriefing,
    build_filtered_reviewer_views,
    build_reviewer_briefing,
    build_reviewer_evidence_index,
    build_reviewer_findings,
    export_reviewer_bundle,
    flatten_filtered_view_rows,
    load_reviewer_briefing,
    load_reviewer_state,
    unresolved_evidence_refs,
    validate_reviewer_bundle,
)
from governance_platform.reviewer.smoke import run_core_smoke_checks

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


def test_reviewer_briefing_model_and_synthetic_boundaries(reviewer_state) -> None:
    briefing = build_reviewer_briefing(reviewer_state)

    assert isinstance(briefing, ReviewerBriefing)
    assert briefing.briefing_id == "RB-0001"
    assert briefing.snapshot_id == "RS-0001"
    assert briefing.governance_posture == "attention_required"
    assert briefing.bounded_risk_score == 3
    assert briefing.synthetic_data_only is True
    assert briefing.local_only is True
    assert briefing.non_production is True
    assert "all_datasets_synthetic_only" in briefing.inventory_metrics
    assert any(finding.source_id == "CR-0034" for finding in briefing.notable_findings)


def test_reviewer_briefing_rejects_missing_claim_boundaries(reviewer_state) -> None:
    raw = build_reviewer_briefing(reviewer_state).model_dump(mode="python")
    raw["synthetic_data_only"] = False

    with pytest.raises(ValueError, match="synthetic/local/non-production"):
        ReviewerBriefing.model_validate(raw)


def test_filtered_reviewer_views_are_deterministic_and_reviewer_useful(reviewer_state) -> None:
    views = build_filtered_reviewer_views(reviewer_state)
    by_name = {view.view_name: view for view in views}
    flattened = flatten_filtered_view_rows(views)

    assert tuple(view.view_name for view in views) == (
        "high_risk_models",
        "pending_or_rejected_research_projects",
        "rejected_access_requests",
        "revoked_or_expired_grants",
        "warning_or_failed_controls",
        "high_severity_risk_indicators",
        "audit_events_for_RP-0001",
        "evidence_references_for_CR-0034",
    )
    assert by_name["high_risk_models"].rows[0]["model_id"] == "MD-0003"
    assert by_name["rejected_access_requests"].rows[0]["request_id"] == "AR-0002"
    assert by_name["revoked_or_expired_grants"].rows[0]["grant_id"] == "AG-0002"
    assert by_name["warning_or_failed_controls"].rows[0]["result_id"] == "CR-0034"
    assert by_name["high_severity_risk_indicators"].rows == ()
    assert any(row["view_name"] == "audit_events_for_RP-0001" for row in flattened)
    assert any(
        row["view_name"] == "rejected_access_requests" and row["entity_id"] == "AR-0002"
        for row in flattened
    )


def test_evidence_index_covers_used_references_and_is_stably_ordered(reviewer_state) -> None:
    index = build_reviewer_evidence_index(reviewer_state)
    refs = [entry.evidence_ref for entry in index]

    assert refs == sorted(refs)
    assert unresolved_evidence_refs(reviewer_state, index) == ()
    assert "model:MD-0003" in refs
    assert "access_grant:AG-0001" in refs
    assert "approval_decision:AD-0001" in refs
    assert "evidence_pack:EVP-0001" in refs
    assert all(not entry.source_file.startswith("/") for entry in index)


def test_reviewer_findings_are_concise_and_sorted(reviewer_state) -> None:
    findings = build_reviewer_findings(reviewer_state)

    assert [row["source_id"] for row in findings] == ["CR-0034", "RI-0001"]
    assert all(row["evidence_refs"] for row in findings)
    assert all("synthetic" not in row["summary"].lower() or row["entity_id"] for row in findings)


def test_reviewer_bundle_export_reload_and_validation(reviewer_state, tmp_path) -> None:
    out = tmp_path / "reviewer"
    metadata = export_reviewer_bundle(reviewer_state, out)
    briefing = load_reviewer_briefing(out)

    assert metadata["briefing_id"] == "RB-0001"
    assert metadata["kpi_count"] == 72
    assert metadata["finding_count"] == 2
    assert metadata["filtered_view_count"] == 8
    assert briefing.briefing_id == "RB-0001"
    assert validate_reviewer_bundle(out) == []
    assert (
        (out / "reviewer_briefing.md")
        .read_text(encoding="utf-8")
        .startswith("# Reviewer Briefing Bundle")
    )
    assert "model:MD-0003" in (out / "reviewer_evidence_index.csv").read_text(encoding="utf-8")


def test_reviewer_bundle_exports_are_byte_identical(reviewer_state, tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    export_reviewer_bundle(reviewer_state, first)
    export_reviewer_bundle(reviewer_state, second)

    first_files = sorted(path.name for path in first.iterdir())
    assert first_files == sorted(path.name for path in second.iterdir())
    for filename in first_files:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_missing_generated_outputs_fail_before_export(tmp_path) -> None:
    with pytest.raises(MissingGeneratedOutputError):
        load_reviewer_state(tmp_path)


def test_reviewer_demo_core_smoke_helpers(tmp_path) -> None:
    _write_outputs(tmp_path)
    result = run_core_smoke_checks(tmp_path)

    assert result["snapshot_id"] == "RS-0001"
    assert result["briefing_id"] == "RB-0001"
    assert result["evidence_ref_count"] >= 1
    assert result["filtered_view_count"] == 8
