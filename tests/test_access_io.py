import csv
from pathlib import Path

import pytest

from governance_platform.access import (
    REFERENCE_EVALUATION_TIME,
    export_access_state,
    generate_access_control_state,
    load_access_state,
)
from governance_platform.access.io import (
    ACCESS_GRANTS_CSV_FILENAME,
    ACCESS_REQUESTS_CSV_FILENAME,
    ACCESS_REVIEW_SUMMARY_FILENAME,
    ACCESS_STATE_FILENAME,
    APPROVAL_DECISIONS_CSV_FILENAME,
)
from governance_platform.inventory import generate_portfolio


def _export(tmp_path: Path) -> Path:
    inventory = generate_portfolio()
    state = generate_access_control_state()
    export_access_state(
        state, inventory, evaluated_at=REFERENCE_EVALUATION_TIME, output_dir=tmp_path
    )
    return tmp_path


def test_export_writes_expected_files(tmp_path: Path) -> None:
    _export(tmp_path)

    for filename in (
        ACCESS_STATE_FILENAME,
        ACCESS_REQUESTS_CSV_FILENAME,
        APPROVAL_DECISIONS_CSV_FILENAME,
        ACCESS_GRANTS_CSV_FILENAME,
        ACCESS_REVIEW_SUMMARY_FILENAME,
    ):
        assert (tmp_path / filename).is_file()


def test_export_creates_missing_output_directory(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "access"
    inventory = generate_portfolio()
    state = generate_access_control_state()
    export_access_state(state, inventory, evaluated_at=REFERENCE_EVALUATION_TIME, output_dir=nested)

    assert (nested / ACCESS_STATE_FILENAME).is_file()


def test_export_is_deterministic_across_runs(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _export(first_dir)
    _export(second_dir)

    for filename in (
        ACCESS_STATE_FILENAME,
        ACCESS_REQUESTS_CSV_FILENAME,
        APPROVAL_DECISIONS_CSV_FILENAME,
        ACCESS_GRANTS_CSV_FILENAME,
        ACCESS_REVIEW_SUMMARY_FILENAME,
    ):
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes()


def test_access_requests_csv_has_expected_row_count(tmp_path: Path) -> None:
    _export(tmp_path)
    state = generate_access_control_state()

    with (tmp_path / ACCESS_REQUESTS_CSV_FILENAME).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == len(state.requests)
    assert "request_id" in rows[0]


def test_load_access_state_round_trips(tmp_path: Path) -> None:
    original = generate_access_control_state()
    inventory = generate_portfolio()
    export_access_state(
        original, inventory, evaluated_at=REFERENCE_EVALUATION_TIME, output_dir=tmp_path
    )

    loaded = load_access_state(tmp_path)

    assert loaded.model_dump(mode="json") == original.model_dump(mode="json")


def test_load_access_state_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_access_state(tmp_path)
