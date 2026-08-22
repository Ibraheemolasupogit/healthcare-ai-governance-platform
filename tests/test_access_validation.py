from datetime import datetime
from pathlib import Path

from governance_platform.access import (
    REFERENCE_EVALUATION_TIME,
    export_access_state,
    generate_access_control_state,
)
from governance_platform.access.validation import (
    validate_access_state_data,
    validate_access_state_file,
)
from governance_platform.inventory import generate_portfolio


def test_validate_access_state_data_accepts_valid_data() -> None:
    data = generate_access_control_state().model_dump(mode="json")
    assert validate_access_state_data(data) == []


def test_validate_access_state_data_reports_duplicate_request_ids() -> None:
    data = generate_access_control_state().model_dump(mode="json")
    data["requests"].append(dict(data["requests"][0]))

    problems = validate_access_state_data(data)

    assert problems
    assert any("duplicate request_id" in problem for problem in problems)


def test_validate_access_state_data_reports_grant_without_approved_decision() -> None:
    data = generate_access_control_state().model_dump(mode="json")
    rejected_request_id = next(
        r["request_id"] for r in data["requests"] if r["status"] == "rejected"
    )
    approved_grant = dict(data["grants"][0])
    approved_grant.update(
        grant_id="AG-9999",
        request_id=rejected_request_id,
        granted_at=datetime(2025, 1, 1).isoformat(),
        expires_at=datetime(2025, 2, 1).isoformat(),
    )
    data["grants"].append(approved_grant)

    problems = validate_access_state_data(data)

    assert problems
    assert any("no approved decision" in problem for problem in problems)


def test_validate_access_state_data_reports_malformed_metadata() -> None:
    data = generate_access_control_state().model_dump(mode="json")
    data["requests"][0]["status"] = "not_a_real_status"

    assert validate_access_state_data(data) != []


def test_validate_access_state_file_reports_missing_file(tmp_path: Path) -> None:
    problems = validate_access_state_file(tmp_path)

    assert problems
    assert any("not found" in problem for problem in problems)


def test_validate_access_state_file_accepts_generated_export(tmp_path: Path) -> None:
    inventory = generate_portfolio()
    state = generate_access_control_state()
    export_access_state(
        state, inventory, evaluated_at=REFERENCE_EVALUATION_TIME, output_dir=tmp_path
    )

    assert validate_access_state_file(tmp_path) == []
