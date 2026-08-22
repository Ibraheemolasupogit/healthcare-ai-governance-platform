"""Loading and export for compliance control results and posture outputs."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

from governance_platform.compliance.entities import ComplianceAssessment, ControlResult
from governance_platform.compliance.markdown import render_governance_posture_markdown

CONTROL_RESULTS_JSON_FILENAME = "control_results.json"
CONTROL_RESULTS_CSV_FILENAME = "control_results.csv"
RISK_INDICATORS_JSON_FILENAME = "risk_indicators.json"
COMPLIANCE_SUMMARY_FILENAME = "compliance_summary.json"
GOVERNANCE_POSTURE_MARKDOWN_FILENAME = "governance_posture.md"

_LIST_FIELD_SEPARATOR = ";"
_CONTROL_RESULT_COLUMNS = list(ControlResult.model_fields.keys())


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


def export_compliance_assessment(assessment: ComplianceAssessment, output_dir: str | Path) -> None:
    """Write compliance outputs to ``output_dir`` in deterministic order."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_json(
        out / CONTROL_RESULTS_JSON_FILENAME,
        [result.model_dump(mode="json") for result in assessment.control_results],
    )
    _write_csv(
        out / CONTROL_RESULTS_CSV_FILENAME,
        _CONTROL_RESULT_COLUMNS,
        [result.model_dump(mode="json") for result in assessment.control_results],
    )
    _write_json(
        out / RISK_INDICATORS_JSON_FILENAME,
        [indicator.model_dump(mode="json") for indicator in assessment.risk_indicators],
    )
    _write_json(out / COMPLIANCE_SUMMARY_FILENAME, assessment.model_dump(mode="json"))
    (out / GOVERNANCE_POSTURE_MARKDOWN_FILENAME).write_text(
        render_governance_posture_markdown(assessment), encoding="utf-8"
    )


def load_compliance_assessment(input_dir: str | Path) -> ComplianceAssessment:
    """Load the canonical compliance assessment from ``compliance_summary.json``."""
    path = Path(input_dir) / COMPLIANCE_SUMMARY_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Compliance summary file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return ComplianceAssessment.model_validate(raw)
