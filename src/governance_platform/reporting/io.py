"""Loading and export for deterministic governance reporting outputs."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

from governance_platform.reporting.entities import GovernanceKPI, ReportingSnapshot
from governance_platform.reporting.markdown import render_executive_summary_markdown

GOVERNANCE_KPIS_JSON_FILENAME = "governance_kpis.json"
GOVERNANCE_KPIS_CSV_FILENAME = "governance_kpis.csv"
REPORTING_SNAPSHOT_FILENAME = "reporting_snapshot.json"
EXECUTIVE_SUMMARY_MARKDOWN_FILENAME = "executive_summary.md"

_LIST_FIELD_SEPARATOR = ";"
_KPI_COLUMNS = list(GovernanceKPI.model_fields.keys())


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple | list):
        return _LIST_FIELD_SEPARATOR.join(str(item) for item in value)
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row[column]) for column in columns])


def export_reporting_snapshot(snapshot: ReportingSnapshot, output_dir: str | Path) -> None:
    """Write reporting snapshot outputs to ``output_dir`` in deterministic order."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_json(
        out / GOVERNANCE_KPIS_JSON_FILENAME,
        [metric.model_dump(mode="json") for metric in snapshot.all_metrics],
    )
    _write_csv(
        out / GOVERNANCE_KPIS_CSV_FILENAME,
        _KPI_COLUMNS,
        [metric.model_dump(mode="json") for metric in snapshot.all_metrics],
    )
    _write_json(out / REPORTING_SNAPSHOT_FILENAME, snapshot.model_dump(mode="json"))
    (out / EXECUTIVE_SUMMARY_MARKDOWN_FILENAME).write_text(
        render_executive_summary_markdown(snapshot), encoding="utf-8"
    )


def load_reporting_snapshot(input_dir: str | Path) -> ReportingSnapshot:
    """Load the canonical reporting snapshot JSON from ``input_dir``."""
    path = Path(input_dir) / REPORTING_SNAPSHOT_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Reporting snapshot file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return ReportingSnapshot.model_validate(raw)
