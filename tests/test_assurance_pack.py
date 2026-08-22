from datetime import datetime

import pytest
from pydantic import ValidationError
from scripts.generate_assurance_pack import _missing_pack_sources

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
    AssuranceReviewPack,
    ReviewerActionPriority,
    build_assurance_review_pack,
    build_priority_findings,
    build_reviewer_evidence_index,
    export_assurance_review_pack_bundle,
    export_reviewer_bundle,
    load_assurance_review_pack,
    load_reviewer_assurance_pack_state,
    load_reviewer_briefing,
    load_reviewer_state,
    validate_assurance_review_pack,
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
def assurance_pack_context(tmp_path):
    assessment = _write_outputs(tmp_path)
    state = load_reviewer_state(tmp_path)
    export_reviewer_bundle(state, tmp_path / "reviewer")
    known_refs = {entry.evidence_ref for entry in build_reviewer_evidence_index(state)}
    policy_bundle = build_policy_catalog_bundle(assessment, known_evidence_refs=known_refs)
    export_policy_catalog_bundle(policy_bundle, tmp_path / "policy")
    assurance_bundle = build_assurance_history_bundle(assessment, policy_bundle.controls)
    export_assurance_history_bundle(assurance_bundle, tmp_path / "assurance")
    briefing = load_reviewer_briefing(tmp_path / "reviewer")
    policies = load_policy_catalog(tmp_path / "policy")
    controls = load_control_catalog(tmp_path / "policy")
    policy_summary = load_policy_assurance_summary(tmp_path / "policy")
    comparison = load_assurance_comparison(tmp_path / "assurance")
    evidence_index = build_reviewer_evidence_index(state)
    bundle = build_assurance_review_pack(
        state,
        briefing,
        policies,
        controls,
        policy_summary,
        comparison,
        evidence_index=evidence_index,
    )
    return tmp_path, bundle, evidence_index


def test_assurance_review_pack_model_and_claim_boundaries(assurance_pack_context) -> None:
    _, bundle, _ = assurance_pack_context
    pack = bundle.pack

    assert isinstance(pack, AssuranceReviewPack)
    assert pack.pack_id == "ARP-0001"
    assert pack.governance_posture == "attention_required"
    assert pack.bounded_risk_score == 3
    assert pack.synthetic_data_only is True
    assert pack.local_only is True
    assert pack.non_production is True
    with pytest.raises(ValidationError):
        pack.pack_id = "changed"  # type: ignore[misc]


def test_priority_findings_are_deterministic_and_ordered(assurance_pack_context) -> None:
    _, bundle, _ = assurance_pack_context
    findings = bundle.pack.priority_findings

    assert [finding.finding_id for finding in findings] == [
        f"PF-{index:04d}" for index in range(1, len(findings) + 1)
    ]
    assert [finding.control_id for finding in findings] == [
        "CTRL-0005",
        "CTRL-0014",
        "CTRL-0014",
    ]
    assert [finding.status for finding in findings] == [
        "warning",
        "warning",
        "risk_indicator",
    ]
    assert findings[0].entity_id == "synthetic_governance_state"
    assert findings[0].drift_id == "CD-0001"
    assert findings[1].entity_id == "MD-0003"


def test_finding_policy_control_evidence_and_drift_linkage(assurance_pack_context) -> None:
    _, bundle, evidence_index = assurance_pack_context
    index_refs = {entry.evidence_ref for entry in evidence_index}
    drift = bundle.pack.priority_findings[0]
    readiness = bundle.pack.priority_findings[1]

    assert readiness.control_id == "CTRL-0014"
    assert readiness.policy_ids == ("POL-0008",)
    assert "model:MD-0003" in readiness.evidence_refs
    assert set(readiness.evidence_refs) <= index_refs
    assert drift.control_id == "CTRL-0005"
    assert drift.policy_ids == ("POL-0009",)
    assert drift.drift_status == "new_finding"
    assert drift.drift_id == "CD-0001"
    assert all(row["evidence_ref"] in index_refs for row in bundle.evidence_map_rows)


def test_reviewer_actions_are_review_only_and_linked(assurance_pack_context) -> None:
    _, bundle, _ = assurance_pack_context
    actions = bundle.pack.reviewer_actions

    assert [action.action_id for action in actions] == [
        f"RA-{index:04d}" for index in range(1, len(actions) + 1)
    ]
    assert actions[0].priority == ReviewerActionPriority.MEDIUM
    assert actions[0].related_control_ids == ("CTRL-0005",)
    assert "remediate" not in " ".join(action.description.lower() for action in actions)
    assert all(action.evidence_refs for action in actions)


def test_evidence_map_is_stably_ordered(assurance_pack_context) -> None:
    _, bundle, _ = assurance_pack_context
    rows = bundle.evidence_map_rows

    assert rows == tuple(
        sorted(
            rows,
            key=lambda row: (
                row["finding_id"],
                row["control_id"],
                row["policy_id"],
                row["evidence_ref"],
            ),
        )
    )
    assert any(
        row["finding_id"] == "PF-0002"
        and row["control_id"] == "CTRL-0014"
        and row["policy_id"] == "POL-0008"
        and row["evidence_ref"] == "model:MD-0003"
        for row in rows
    )


def test_assurance_pack_export_reload_and_validation(assurance_pack_context, tmp_path) -> None:
    _, bundle, _ = assurance_pack_context
    out = tmp_path / "assurance_pack"

    metadata = export_assurance_review_pack_bundle(bundle, out)

    assert metadata["pack_id"] == "ARP-0001"
    assert validate_assurance_review_pack(out) == []
    assert load_assurance_review_pack(out) == bundle.pack
    assert (
        (out / "assurance_review_pack.md")
        .read_text(encoding="utf-8")
        .startswith("# Assurance Review Pack")
    )


def test_assurance_pack_exports_are_byte_identical(assurance_pack_context, tmp_path) -> None:
    _, bundle, _ = assurance_pack_context
    first = tmp_path / "first"
    second = tmp_path / "second"

    export_assurance_review_pack_bundle(bundle, first)
    export_assurance_review_pack_bundle(bundle, second)

    first_files = sorted(path.name for path in first.iterdir())
    assert first_files == sorted(path.name for path in second.iterdir())
    for filename in first_files:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_missing_source_handling_lists_required_outputs(tmp_path) -> None:
    missing = _missing_pack_sources(tmp_path)

    assert tmp_path / "inventory" / "inventory_portfolio.json" in missing
    assert tmp_path / "reviewer" / "reviewer_briefing.json" in missing
    assert tmp_path / "policy" / "control_catalog.json" in missing
    assert tmp_path / "assurance" / "assurance_comparison.json" in missing


def test_pack_reviewer_data_loading(assurance_pack_context) -> None:
    root, bundle, _ = assurance_pack_context
    export_assurance_review_pack_bundle(bundle, root / "assurance_pack")

    state = load_reviewer_assurance_pack_state(root)

    assert state.pack.pack_id == "ARP-0001"
    assert len(state.priority_finding_rows) == len(bundle.pack.priority_findings)
    assert len(state.reviewer_action_rows) == len(bundle.pack.reviewer_actions)
    assert len(state.evidence_map_rows) == len(bundle.evidence_map_rows)


def test_priority_helper_rejects_missing_evidence_refs(assurance_pack_context) -> None:
    _, bundle, evidence_index = assurance_pack_context
    broken_pack = bundle.pack.model_copy(
        update={
            "priority_findings": (
                bundle.pack.priority_findings[0].model_copy(
                    update={"evidence_refs": ("missing:ref",)}
                ),
            )
        }
    )

    with pytest.raises(ValueError, match="does not resolve"):
        __import__(
            "governance_platform.reviewer",
            fromlist=["build_assurance_evidence_map"],
        ).build_assurance_evidence_map(broken_pack, evidence_index)


def test_priority_finding_helper_stable_with_same_inputs(assurance_pack_context) -> None:
    root, bundle, _ = assurance_pack_context
    state = load_reviewer_state(root)
    controls = load_control_catalog(root / "policy")
    comparison = load_assurance_comparison(root / "assurance")

    assert build_priority_findings(state, controls, comparison) == bundle.pack.priority_findings
