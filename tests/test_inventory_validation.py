from pathlib import Path

from governance_platform.inventory import export_portfolio, generate_portfolio
from governance_platform.inventory.validation import (
    validate_portfolio_data,
    validate_portfolio_file,
)


def test_validate_portfolio_data_accepts_valid_data() -> None:
    data = generate_portfolio().model_dump(mode="json")
    assert validate_portfolio_data(data) == []


def test_validate_portfolio_data_reports_duplicate_ids() -> None:
    data = generate_portfolio().model_dump(mode="json")
    data["datasets"].append(dict(data["datasets"][0]))

    problems = validate_portfolio_data(data)

    assert problems
    assert any("duplicate dataset_id" in problem for problem in problems)


def test_validate_portfolio_data_reports_invalid_dataset_reference() -> None:
    data = generate_portfolio().model_dump(mode="json")
    data["models"][0]["linked_dataset_ids"] = ["DS-9999"]

    problems = validate_portfolio_data(data)

    assert problems
    assert any("unknown dataset_id" in problem for problem in problems)


def test_validate_portfolio_data_reports_invalid_model_reference() -> None:
    data = generate_portfolio().model_dump(mode="json")
    data["research_projects"][0]["linked_model_ids"] = ["MD-9999"]

    problems = validate_portfolio_data(data)

    assert problems
    assert any("unknown model_id" in problem for problem in problems)


def test_validate_portfolio_data_reports_malformed_metadata() -> None:
    data = generate_portfolio().model_dump(mode="json")
    data["datasets"][0]["sensitivity_classification"] = "not_a_real_classification"

    problems = validate_portfolio_data(data)

    assert problems


def test_validate_portfolio_data_reports_non_synthetic_dataset() -> None:
    data = generate_portfolio().model_dump(mode="json")
    data["datasets"][0]["contains_synthetic_data_only"] = False

    problems = validate_portfolio_data(data)

    assert any("synthetic" in problem for problem in problems)


def test_validate_portfolio_file_reports_missing_file(tmp_path: Path) -> None:
    problems = validate_portfolio_file(tmp_path)

    assert problems
    assert any("not found" in problem for problem in problems)


def test_validate_portfolio_file_accepts_generated_export(tmp_path: Path) -> None:
    export_portfolio(generate_portfolio(), tmp_path)
    assert validate_portfolio_file(tmp_path) == []
