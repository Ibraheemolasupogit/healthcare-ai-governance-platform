import csv
from datetime import datetime
from pathlib import Path

import pytest

from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import (
    build_audit_summary,
    build_evidence_pack,
    export_audit_log,
    export_audit_summary,
    export_evidence_pack,
    generate_audit_log,
    load_audit_log,
    load_evidence_pack,
)
from governance_platform.audit.io import (
    AUDIT_EVENTS_CSV_FILENAME,
    AUDIT_EVENTS_JSON_FILENAME,
    AUDIT_SUMMARY_FILENAME,
    EVIDENCE_PACK_JSON_FILENAME,
    EVIDENCE_PACK_MARKDOWN_FILENAME,
)
from governance_platform.inventory import generate_portfolio

_GENERATED_AT = datetime(2025, 3, 20)


def _build_all():
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    pack = build_evidence_pack(
        inventory,
        access_state,
        log,
        evidence_pack_id="EVP-0001",
        generated_at=_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )
    return inventory, access_state, log, pack


def test_export_audit_log_writes_json_and_csv(tmp_path: Path) -> None:
    _, _, log, _ = _build_all()
    export_audit_log(log, tmp_path)

    assert (tmp_path / AUDIT_EVENTS_JSON_FILENAME).is_file()
    assert (tmp_path / AUDIT_EVENTS_CSV_FILENAME).is_file()


def test_export_evidence_pack_writes_json_and_markdown(tmp_path: Path) -> None:
    _, _, _, pack = _build_all()
    export_evidence_pack(pack, tmp_path)

    assert (tmp_path / EVIDENCE_PACK_JSON_FILENAME).is_file()
    assert (tmp_path / EVIDENCE_PACK_MARKDOWN_FILENAME).is_file()


def test_export_audit_summary_writes_json(tmp_path: Path) -> None:
    _, access_state, log, _ = _build_all()
    export_audit_summary(build_audit_summary(log, access_state), tmp_path)

    assert (tmp_path / AUDIT_SUMMARY_FILENAME).is_file()


def test_load_audit_log_round_trips(tmp_path: Path) -> None:
    _, _, log, _ = _build_all()
    export_audit_log(log, tmp_path)

    loaded = load_audit_log(tmp_path)

    assert loaded.model_dump(mode="json") == log.model_dump(mode="json")


def test_load_evidence_pack_round_trips(tmp_path: Path) -> None:
    _, _, _, pack = _build_all()
    export_evidence_pack(pack, tmp_path)

    loaded = load_evidence_pack(tmp_path)

    assert loaded.model_dump(mode="json") == pack.model_dump(mode="json")


def test_load_audit_log_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_audit_log(tmp_path)


def test_load_evidence_pack_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_evidence_pack(tmp_path)


def test_audit_events_csv_row_count_matches_log(tmp_path: Path) -> None:
    _, _, log, _ = _build_all()
    export_audit_log(log, tmp_path)

    with (tmp_path / AUDIT_EVENTS_CSV_FILENAME).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == len(log.events)
    assert "event_id" in rows[0]


def test_evidence_pack_markdown_contains_required_sections(tmp_path: Path) -> None:
    _, _, _, pack = _build_all()
    export_evidence_pack(pack, tmp_path)

    markdown = (tmp_path / EVIDENCE_PACK_MARKDOWN_FILENAME).read_text(encoding="utf-8")

    for heading in (
        "# Governance Evidence Pack",
        "## Source systems represented",
        "## Inventory summary",
        "## Access-control summary",
        "## Key audit events",
        "## Rejected-access evidence",
        "## Grant evidence: active / expired / revoked",
        "## Control-assurance summary",
        "## Limitations",
    ):
        assert heading in markdown
    assert "EVP-0001" in markdown


def test_export_is_deterministic_across_runs(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    _, access_state1, log1, pack1 = _build_all()
    export_audit_log(log1, first_dir)
    export_audit_summary(build_audit_summary(log1, access_state1), first_dir)
    export_evidence_pack(pack1, first_dir)

    _, access_state2, log2, pack2 = _build_all()
    export_audit_log(log2, second_dir)
    export_audit_summary(build_audit_summary(log2, access_state2), second_dir)
    export_evidence_pack(pack2, second_dir)

    for filename in (
        AUDIT_EVENTS_JSON_FILENAME,
        AUDIT_EVENTS_CSV_FILENAME,
        AUDIT_SUMMARY_FILENAME,
        EVIDENCE_PACK_JSON_FILENAME,
        EVIDENCE_PACK_MARKDOWN_FILENAME,
    ):
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes()
