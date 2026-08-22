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
    ControlCatalogEntry,
    EvidenceRequirement,
    PolicyAssuranceSummary,
    PolicyDefinition,
    SourcePlane,
    build_control_catalog,
    build_policy_catalog_bundle,
    build_policy_definitions,
    build_traceability_matrix,
    default_control_definitions,
    evaluate_compliance,
    export_compliance_assessment,
    export_policy_catalog_bundle,
    load_compliance_assessment,
    load_control_catalog,
    load_policy_assurance_summary,
    load_policy_catalog,
    validate_policy_catalog,
    validate_policy_catalog_files,
)
from governance_platform.inventory import export_portfolio, generate_portfolio
from governance_platform.reporting import build_reporting_snapshot, export_reporting_snapshot
from governance_platform.reviewer import (
    build_reviewer_evidence_index,
    load_reviewer_policy_state,
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


@pytest.fixture()
def catalog_context(tmp_path):
    _write_outputs(tmp_path)
    assessment = load_compliance_assessment(tmp_path / "compliance")
    reviewer_state = load_reviewer_state(tmp_path)
    known_refs = {entry.evidence_ref for entry in build_reviewer_evidence_index(reviewer_state)}
    return tmp_path, assessment, known_refs


def test_policy_and_control_catalog_models_are_frozen(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    policy = bundle.policies[0]
    control = bundle.controls[0]
    requirement = control.evidence_requirements[0]

    assert isinstance(policy, PolicyDefinition)
    assert isinstance(control, ControlCatalogEntry)
    assert isinstance(requirement, EvidenceRequirement)
    assert policy.policy_id == "POL-0001"
    assert control.control_id == "CTRL-0001"
    assert requirement.requirement_id == "ER-CTRL-0001-01"
    with pytest.raises(ValidationError):
        control.name = "Changed"  # type: ignore[misc]


def test_catalog_is_synchronized_with_implemented_controls(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    controls = build_control_catalog()
    policies = build_policy_definitions()

    assert [control.control_id for control in controls] == [
        control.control_id for control in default_control_definitions()
    ]
    assert (
        validate_policy_catalog(policies, controls, assessment, known_evidence_refs=known_refs)
        == []
    )
    assert all(control.policy_ids for control in controls)
    assert all(control.evidence_requirements for control in controls if control.enabled)


def test_traceability_matrix_uses_real_evidence_refs(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    rows = bundle.traceability_rows

    assert rows == tuple(
        sorted(
            rows,
            key=lambda row: (
                row["policy_id"],
                row["control_id"],
                row["evidence_requirement"],
                row["reviewer_location"],
                row["evidence_ref"],
            ),
        )
    )
    assert any(
        row["control_id"] == "CTRL-0014"
        and row["evidence_ref"] == "model:MD-0003"
        and row["evaluation_status"] == "warning"
        for row in rows
    )
    assert any(
        row["control_id"] == "CTRL-0003"
        and row["evidence_ref"] == "adr:0001"
        and row["source_plane"] == SourcePlane.GOVERNANCE.value
        for row in rows
    )
    assert {row["evidence_ref"] for row in rows if row["evidence_ref"]} <= known_refs


def test_policy_assurance_summary_preserves_claim_boundaries(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    summary = build_policy_catalog_bundle(
        assessment, known_evidence_refs=known_refs
    ).assurance_summary

    assert isinstance(summary, PolicyAssuranceSummary)
    assert summary.policy_count == 9
    assert summary.control_count == 26
    assert summary.evidence_requirement_count == 41
    assert summary.missing_evidence_refs == ()
    assert summary.synthetic_data_only is True
    assert summary.local_only is True
    assert summary.non_production is True


def test_catalog_export_reload_and_validation(catalog_context, tmp_path) -> None:
    _, assessment, known_refs = catalog_context
    bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    out = tmp_path / "policy"

    export_policy_catalog_bundle(bundle, out)

    assert validate_policy_catalog_files(out) == []
    assert load_policy_catalog(out) == bundle.policies
    assert load_control_catalog(out) == bundle.controls
    assert load_policy_assurance_summary(out) == bundle.assurance_summary
    assert (
        (out / "policy_assurance_summary.md")
        .read_text(encoding="utf-8")
        .startswith("# Policy Assurance Summary")
    )


def test_reviewer_policy_data_loading(catalog_context) -> None:
    root, assessment, known_refs = catalog_context
    bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    export_policy_catalog_bundle(bundle, root / "policy")

    policy_state = load_reviewer_policy_state(root)

    assert len(policy_state.policy_rows) == 9
    assert len(policy_state.control_rows) == 26
    assert len(policy_state.traceability_rows) == bundle.assurance_summary.traceability_row_count
    assert policy_state.assurance_summary.policy_count == 9


def test_catalog_exports_are_byte_identical(catalog_context, tmp_path) -> None:
    _, assessment, known_refs = catalog_context
    bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    first = tmp_path / "first"
    second = tmp_path / "second"

    export_policy_catalog_bundle(bundle, first)
    export_policy_catalog_bundle(bundle, second)

    first_files = sorted(path.name for path in first.iterdir())
    assert first_files == sorted(path.name for path in second.iterdir())
    for filename in first_files:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_missing_control_detection(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    controls = tuple(
        control for control in build_control_catalog() if control.control_id != "CTRL-0001"
    )
    problems = validate_policy_catalog(
        build_policy_definitions(), controls, assessment, known_evidence_refs=known_refs
    )

    assert "implemented control missing from catalog: CTRL-0001" in problems


def test_orphan_control_detection(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    orphan = build_control_catalog()[0].model_copy(update={"control_id": "CTRL-9999"})
    problems = validate_policy_catalog(
        build_policy_definitions(),
        (*build_control_catalog(), orphan),
        assessment,
        known_evidence_refs=known_refs,
    )

    assert "catalog control does not resolve to implemented control: CTRL-9999" in problems


def test_orphan_evidence_requirement_detection(catalog_context) -> None:
    _, assessment, known_refs = catalog_context
    control = build_control_catalog()[0]
    bad_requirement = control.evidence_requirements[0].model_copy(
        update={"control_id": "CTRL-9999"}
    )
    bad_control = control.model_copy(update={"evidence_requirements": (bad_requirement,)})
    controls = (bad_control, *build_control_catalog()[1:])
    problems = validate_policy_catalog(
        build_policy_definitions(), controls, assessment, known_evidence_refs=known_refs
    )

    assert any("orphan evidence requirement" in problem for problem in problems)


def test_evidence_reference_resolution_failure_is_reported(catalog_context) -> None:
    _, assessment, _known_refs = catalog_context
    known_refs = {"portfolio:synthetic_governance_state"}
    problems = validate_policy_catalog(
        build_policy_definitions(),
        build_control_catalog(),
        assessment,
        known_evidence_refs=known_refs,
    )

    assert any("expected evidence reference does not resolve" in problem for problem in problems)


def test_empty_policy_control_references_are_rejected() -> None:
    policy = build_policy_definitions()[0]
    with pytest.raises(ValueError):
        PolicyDefinition.model_validate(
            {**policy.model_dump(mode="json"), "related_control_ids": ()}
        )


def test_traceability_can_be_built_from_reloaded_catalog(catalog_context, tmp_path) -> None:
    _, assessment, known_refs = catalog_context
    bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    export_policy_catalog_bundle(bundle, tmp_path)
    policies = load_policy_catalog(tmp_path)
    controls = load_control_catalog(tmp_path)

    rows = build_traceability_matrix(policies, controls, assessment)

    assert rows == bundle.traceability_rows
    assert len(rows) == bundle.assurance_summary.traceability_row_count
