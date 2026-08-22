from datetime import datetime
from pathlib import Path

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
    build_assurance_history_bundle,
    build_policy_catalog_bundle,
    evaluate_compliance,
    export_assurance_history_bundle,
    export_compliance_assessment,
    export_policy_catalog_bundle,
    load_assurance_comparison,
    load_control_catalog,
    load_policy_assurance_summary,
    load_policy_catalog,
)
from governance_platform.inventory import export_portfolio, generate_portfolio
from governance_platform.reporting import build_reporting_snapshot, export_reporting_snapshot
from governance_platform.reviewer import (
    AcceptanceResult,
    AcceptanceStatus,
    ReviewerAcceptanceChecklist,
    ReviewReadinessStatus,
    build_acceptance_criteria,
    build_artifact_completeness,
    build_assurance_review_pack,
    build_review_readiness_bundle,
    build_reviewer_evidence_index,
    derive_readiness_status,
    export_assurance_review_pack_bundle,
    export_review_readiness_bundle,
    export_reviewer_bundle,
    load_acceptance_checklist,
    load_demo_readiness,
    load_reviewer_briefing,
    load_reviewer_readiness_state,
    load_reviewer_state,
    missing_readiness_source_paths,
    validate_review_readiness_outputs,
)
from governance_platform.reviewer.smoke import run_core_smoke_checks

EVIDENCE_GENERATED_AT = datetime(2025, 3, 20)
COMPLIANCE_EVALUATED_AT = datetime(2025, 3, 15)
REPORTING_GENERATED_AT = datetime(2025, 3, 21)


def _write_canonical_outputs(root):
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
def readiness_context(tmp_path):
    assessment = _write_canonical_outputs(tmp_path)
    state = load_reviewer_state(tmp_path)
    export_reviewer_bundle(state, tmp_path / "reviewer")
    known_refs = {entry.evidence_ref for entry in build_reviewer_evidence_index(state)}
    policy_bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    export_policy_catalog_bundle(policy_bundle, tmp_path / "policy")
    assurance_bundle = build_assurance_history_bundle(assessment, policy_bundle.controls)
    export_assurance_history_bundle(assurance_bundle, tmp_path / "assurance")
    briefing = load_reviewer_briefing(tmp_path / "reviewer")
    evidence_index = build_reviewer_evidence_index(state)
    assurance_pack = build_assurance_review_pack(
        state,
        briefing,
        load_policy_catalog(tmp_path / "policy"),
        load_control_catalog(tmp_path / "policy"),
        load_policy_assurance_summary(tmp_path / "policy"),
        load_assurance_comparison(tmp_path / "assurance"),
        evidence_index=evidence_index,
    )
    export_assurance_review_pack_bundle(assurance_pack, tmp_path / "assurance_pack")
    return tmp_path


def test_acceptance_models_are_frozen_and_claim_boundaries_are_required() -> None:
    criterion = build_acceptance_criteria()[0]
    result = AcceptanceResult(
        result_id="ARR-0099",
        criterion_id=criterion.criterion_id,
        evaluated_at=datetime(2025, 3, 24),
        status=AcceptanceStatus.DEMONSTRATED,
        evidence_refs=criterion.evidence_requirements,
        message="demonstrated for test",
        limitations=("local synthetic readiness evidence only",),
    )

    assert result.status == AcceptanceStatus.DEMONSTRATED
    with pytest.raises(ValidationError):
        result.result_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        AcceptanceResult(
            result_id="ARR-0100",
            criterion_id=criterion.criterion_id,
            evaluated_at=datetime(2025, 3, 24),
            status=AcceptanceStatus.DEMONSTRATED,
            evidence_refs=(),
            message="missing evidence",
            limitations=("local synthetic readiness evidence only",),
        )


def test_acceptance_criteria_are_ordered_and_include_not_applicable_signoff() -> None:
    criteria = build_acceptance_criteria()

    assert [criterion.criterion_id for criterion in criteria] == [
        f"ACR-{index:04d}" for index in range(1, len(criteria) + 1)
    ]
    assert criteria[-1].required is False
    assert criteria[-1].title == "Formal approval is not applicable"


def test_artifact_completeness_loads_semantic_outputs(readiness_context) -> None:
    root = readiness_context
    artifacts = build_artifact_completeness(root)

    assert all(artifact.status == AcceptanceStatus.DEMONSTRATED for artifact in artifacts)
    assert any(artifact.path == "outputs/policy/policy_catalog.json" for artifact in artifacts)
    assert any(
        artifact.path == "docs/demo/reviewer-walkthrough-template.md" for artifact in artifacts
    )


def test_missing_artifact_is_reported_without_regeneration(tmp_path) -> None:
    artifacts = build_artifact_completeness(tmp_path)
    missing = missing_readiness_source_paths(tmp_path)

    assert any(artifact.status == AcceptanceStatus.INCOMPLETE for artifact in artifacts)
    assert tmp_path / "inventory" / "inventory_portfolio.json" in missing


def test_readiness_bundle_statuses_and_evidence_refs(readiness_context) -> None:
    bundle = build_review_readiness_bundle(readiness_context)

    assert bundle.checklist.readiness_status in {
        ReviewReadinessStatus.READY_FOR_REVIEW,
        ReviewReadinessStatus.READY_WITH_LIMITATIONS,
    }
    assert bundle.checklist.not_applicable_count == 1
    assert all(result.evidence_refs for result in bundle.checklist.results)
    assert bundle.demo_readiness.required_outputs_present is True
    assert bundle.demo_readiness.evidence_traceability_available is True


def test_readiness_status_derivation_handles_incomplete_and_environment_blocked() -> None:
    criterion = build_acceptance_criteria()[0]
    demonstrated = AcceptanceResult(
        result_id="ARR-0001",
        criterion_id=criterion.criterion_id,
        evaluated_at=datetime(2025, 3, 24),
        status=AcceptanceStatus.DEMONSTRATED,
        evidence_refs=criterion.evidence_requirements,
        message="ok",
        limitations=("local synthetic readiness evidence only",),
    )
    blocked = demonstrated.model_copy(update={"status": AcceptanceStatus.BLOCKED_BY_ENVIRONMENT})
    incomplete = demonstrated.model_copy(update={"status": AcceptanceStatus.INCOMPLETE})

    assert derive_readiness_status((demonstrated,)) == ReviewReadinessStatus.READY_FOR_REVIEW
    assert derive_readiness_status((demonstrated, blocked)) == (
        ReviewReadinessStatus.READY_WITH_LIMITATIONS
    )
    assert derive_readiness_status((demonstrated, incomplete)) == ReviewReadinessStatus.NOT_READY


def test_readiness_export_reload_validation_and_portal_loading(readiness_context) -> None:
    bundle = build_review_readiness_bundle(readiness_context)
    out = readiness_context / "readiness"

    metadata = export_review_readiness_bundle(bundle, out)

    assert metadata["checklist_id"] == "RAC-0001"
    assert validate_review_readiness_outputs(out) == []
    assert load_acceptance_checklist(out) == bundle.checklist
    assert load_demo_readiness(out) == bundle.demo_readiness
    state = load_reviewer_readiness_state(readiness_context)
    assert state.checklist.checklist_id == "RAC-0001"
    assert len(state.acceptance_result_rows) == len(bundle.checklist.results)
    assert len(state.artifact_rows) == len(bundle.artifact_completeness)


def test_readiness_exports_are_byte_identical(readiness_context, tmp_path) -> None:
    bundle = build_review_readiness_bundle(readiness_context)
    first = tmp_path / "first"
    second = tmp_path / "second"

    export_review_readiness_bundle(bundle, first)
    export_review_readiness_bundle(bundle, second)

    first_files = sorted(path.name for path in first.iterdir())
    assert first_files == sorted(path.name for path in second.iterdir())
    for filename in first_files:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_non_server_smoke_helper_loads_readiness_outputs(readiness_context) -> None:
    bundle = build_review_readiness_bundle(readiness_context)
    export_review_readiness_bundle(bundle, readiness_context / "readiness")

    result = run_core_smoke_checks(readiness_context, include_extended=True)

    assert result["readiness_status"] in {"ready_for_review", "ready_with_limitations"}
    assert result["policy_traceability_rows"] > 0
    assert result["assurance_evidence_map_rows"] > 0


def test_walkthrough_template_and_claim_discipline_safeguards(readiness_context) -> None:
    template = (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("docs/demo/reviewer-walkthrough-template.md")
        .read_text(encoding="utf-8")
        .lower()
    )
    bundle = build_review_readiness_bundle(readiness_context)

    assert "blank template" in template
    assert "do not use this template to imply approval" in template
    assert "production acceptance" in template
    assert bundle.checklist.synthetic_data_only is True
    assert bundle.checklist.local_only is True
    assert bundle.checklist.non_production is True
    with pytest.raises(ValidationError):
        ReviewerAcceptanceChecklist.model_validate(
            {
                **bundle.checklist.model_dump(mode="json"),
                "synthetic_data_only": False,
            }
        )
