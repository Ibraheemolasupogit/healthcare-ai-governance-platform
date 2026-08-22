"""Loading and export for the inventory portfolio.

``inventory_portfolio.json`` is the canonical, lossless serialization of an
:class:`InventoryPortfolio` and is what :func:`load_portfolio` reads back. The
per-entity CSV files and ``inventory_summary.json`` are export-only, stable
machine-readable views for downstream tools (e.g. a future reporting plane) —
list-valued fields (``linked_dataset_ids``, ``linked_model_ids``) are
flattened to a semicolon-joined string for CSV, so they are not read back by
``load_portfolio``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from governance_platform.inventory.entities import AIModel, Dataset, ResearchProject
from governance_platform.inventory.portfolio import InventoryPortfolio
from governance_platform.inventory.summary import build_summary

PORTFOLIO_FILENAME = "inventory_portfolio.json"
DATASETS_CSV_FILENAME = "datasets.csv"
MODELS_CSV_FILENAME = "models.csv"
RESEARCH_PROJECTS_CSV_FILENAME = "research_projects.csv"
SUMMARY_FILENAME = "inventory_summary.json"

_LIST_FIELD_SEPARATOR = ";"

_DATASET_COLUMNS = list(Dataset.model_fields.keys())
_MODEL_COLUMNS = list(AIModel.model_fields.keys())
_RESEARCH_PROJECT_COLUMNS = list(ResearchProject.model_fields.keys())


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple | list):
        return _LIST_FIELD_SEPARATOR.join(str(item) for item in value)
    if value is None:
        return ""
    if hasattr(value, "value"):  # Enum
        return str(value.value)
    return str(value)


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row[column]) for column in columns])


def export_portfolio(portfolio: InventoryPortfolio, output_dir: str | Path) -> None:
    """Write ``portfolio`` to ``output_dir`` as JSON + CSV, creating it if needed.

    Writes the canonical ``inventory_portfolio.json``, one CSV per entity type,
    and ``inventory_summary.json``. All output is deterministic: identical
    ``portfolio`` input always produces byte-identical files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / PORTFOLIO_FILENAME).write_text(
        json.dumps(portfolio.model_dump(mode="json"), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    _write_csv(
        out / DATASETS_CSV_FILENAME,
        _DATASET_COLUMNS,
        [d.model_dump(mode="json") for d in portfolio.datasets],
    )
    _write_csv(
        out / MODELS_CSV_FILENAME,
        _MODEL_COLUMNS,
        [m.model_dump(mode="json") for m in portfolio.models],
    )
    _write_csv(
        out / RESEARCH_PROJECTS_CSV_FILENAME,
        _RESEARCH_PROJECT_COLUMNS,
        [p.model_dump(mode="json") for p in portfolio.research_projects],
    )

    summary = build_summary(portfolio)
    (out / SUMMARY_FILENAME).write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def load_portfolio(input_dir: str | Path) -> InventoryPortfolio:
    """Load and validate the canonical portfolio JSON from ``input_dir``.

    Raises ``FileNotFoundError`` if ``inventory_portfolio.json`` is missing and
    ``pydantic.ValidationError`` if its contents don't form a valid,
    internally-consistent :class:`InventoryPortfolio`.
    """
    portfolio_path = Path(input_dir) / PORTFOLIO_FILENAME
    if not portfolio_path.is_file():
        raise FileNotFoundError(f"Inventory portfolio file not found: {portfolio_path}")

    raw = json.loads(portfolio_path.read_text(encoding="utf-8"))
    return InventoryPortfolio.model_validate(raw)
