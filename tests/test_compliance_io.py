import json

from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import build_evidence_pack, generate_audit_log
from governance_platform.compliance import (
    evaluate_compliance,
    export_compliance_assessment,
    load_compliance_assessment,
    validate_compliance_assessment_file,
)
from governance_platform.inventory import generate_portfolio


def test_compliance_json_round_trip_and_exports_are_deterministic(tmp_path) -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    evidence_pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=REFERENCE_EVALUATION_TIME,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    assessment = evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )

    export_compliance_assessment(assessment, tmp_path)
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir()) if path.is_file()}
    export_compliance_assessment(assessment, tmp_path)
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir()) if path.is_file()}

    assert first == second
    assert validate_compliance_assessment_file(tmp_path) == []
    assert load_compliance_assessment(tmp_path) == assessment
    summary = json.loads((tmp_path / "compliance_summary.json").read_text(encoding="utf-8"))
    assert summary["assessment_id"] == "CA-0001"
