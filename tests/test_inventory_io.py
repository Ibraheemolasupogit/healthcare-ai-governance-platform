import csv
from pathlib import Path

import pytest

from governance_platform.inventory import export_portfolio, generate_portfolio, load_portfolio
from governance_platform.inventory.io import (
    DATASETS_CSV_FILENAME,
    MODELS_CSV_FILENAME,
    PORTFOLIO_FILENAME,
    RESEARCH_PROJECTS_CSV_FILENAME,
    SUMMARY_FILENAME,
)


def test_export_writes_expected_files(tmp_path: Path) -> None:
    export_portfolio(generate_portfolio(), tmp_path)

    for filename in (
        PORTFOLIO_FILENAME,
        DATASETS_CSV_FILENAME,
        MODELS_CSV_FILENAME,
        RESEARCH_PROJECTS_CSV_FILENAME,
        SUMMARY_FILENAME,
    ):
        assert (tmp_path / filename).is_file()


def test_export_creates_missing_output_directory(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "inventory"
    export_portfolio(generate_portfolio(), nested)

    assert (nested / PORTFOLIO_FILENAME).is_file()


def test_export_is_deterministic_across_runs(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    export_portfolio(generate_portfolio(), first_dir)
    export_portfolio(generate_portfolio(), second_dir)

    for filename in (
        PORTFOLIO_FILENAME,
        DATASETS_CSV_FILENAME,
        MODELS_CSV_FILENAME,
        RESEARCH_PROJECTS_CSV_FILENAME,
        SUMMARY_FILENAME,
    ):
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes()


def test_datasets_csv_has_expected_columns_and_row_count(tmp_path: Path) -> None:
    portfolio = generate_portfolio()
    export_portfolio(portfolio, tmp_path)

    with (tmp_path / DATASETS_CSV_FILENAME).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == len(portfolio.datasets)
    assert "dataset_id" in rows[0]
    assert "contains_synthetic_data_only" in rows[0]
    assert all(row["contains_synthetic_data_only"] == "true" for row in rows)


def test_load_portfolio_round_trips(tmp_path: Path) -> None:
    original = generate_portfolio()
    export_portfolio(original, tmp_path)

    loaded = load_portfolio(tmp_path)

    assert loaded.model_dump(mode="json") == original.model_dump(mode="json")


def test_load_portfolio_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_portfolio(tmp_path)
