from datetime import datetime

from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import build_evidence_pack, generate_audit_log
from governance_platform.compliance import evaluate_compliance
from governance_platform.inventory import generate_portfolio
from governance_platform.reporting import (
    build_reporting_snapshot,
    export_reporting_snapshot,
    load_reporting_snapshot,
    render_executive_summary_markdown,
    validate_reporting_snapshot_file,
)


def _build_snapshot():
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    evidence_pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=datetime(2025, 3, 20),
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    compliance = evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=datetime(2025, 3, 15),
    )
    return build_reporting_snapshot(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        compliance,
        snapshot_id="RS-0001",
        generated_at=datetime(2025, 3, 21),
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )


def test_reporting_export_reload_and_deterministic_output(tmp_path) -> None:
    snapshot = _build_snapshot()

    export_reporting_snapshot(snapshot, tmp_path)
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    export_reporting_snapshot(snapshot, tmp_path)
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}

    assert first == second
    assert validate_reporting_snapshot_file(tmp_path) == []
    assert load_reporting_snapshot(tmp_path) == snapshot
    assert "Executive Governance Summary" in first["executive_summary.md"].decode()


def test_executive_summary_is_evidence_backed_and_claim_disciplined() -> None:
    markdown = render_executive_summary_markdown(_build_snapshot())

    assert "Snapshot ID" in markdown
    assert "Governance posture" in markdown
    assert "No Fabric or Power BI deployment exists" in markdown
    assert "regulatory certification" in markdown
    assert ".pbix" not in markdown
