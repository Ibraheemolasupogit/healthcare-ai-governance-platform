from datetime import datetime
from pathlib import Path

from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import (
    build_evidence_pack,
    export_audit_log,
    export_evidence_pack,
    generate_audit_log,
    validate_audit_log_data,
    validate_audit_log_file,
    validate_evidence_pack_file,
)
from governance_platform.inventory import generate_portfolio


def _log():
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    return generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)


def test_validate_audit_log_data_accepts_valid_data() -> None:
    data = _log().model_dump(mode="json")
    assert validate_audit_log_data(data) == []


def test_validate_audit_log_data_reports_duplicate_event_ids() -> None:
    data = _log().model_dump(mode="json")
    data["events"].append(dict(data["events"][0]))

    problems = validate_audit_log_data(data)

    assert problems
    assert any("duplicate event_id" in problem for problem in problems)


def test_validate_audit_log_data_reports_malformed_event_type() -> None:
    data = _log().model_dump(mode="json")
    data["events"][0]["event_type"] = "not_a_real_event_type"

    assert validate_audit_log_data(data) != []


def test_validate_audit_log_file_reports_missing_file(tmp_path: Path) -> None:
    problems = validate_audit_log_file(tmp_path)

    assert problems
    assert any("not found" in problem for problem in problems)


def test_validate_audit_log_file_accepts_generated_export(tmp_path: Path) -> None:
    export_audit_log(_log(), tmp_path)
    assert validate_audit_log_file(tmp_path) == []


def test_validate_evidence_pack_file_reports_missing_file(tmp_path: Path) -> None:
    problems = validate_evidence_pack_file(tmp_path)

    assert problems
    assert any("not found" in problem for problem in problems)


def test_validate_evidence_pack_file_accepts_generated_export(tmp_path: Path) -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = _log()
    pack = build_evidence_pack(
        inventory,
        access_state,
        log,
        evidence_pack_id="EVP-0001",
        generated_at=datetime(2025, 3, 20),
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    export_evidence_pack(pack, tmp_path)

    assert validate_evidence_pack_file(tmp_path) == []
