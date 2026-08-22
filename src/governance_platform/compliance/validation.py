"""Validate compliance output data without raising, for CLI-style reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from governance_platform.compliance.entities import ComplianceAssessment
from governance_platform.compliance.io import COMPLIANCE_SUMMARY_FILENAME


def _format_error(error: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in error["loc"]) or "<compliance assessment>"
    return f"{location}: {error['msg']}"


def validate_compliance_assessment_data(data: dict[str, Any]) -> list[str]:
    """Validate raw compliance assessment data and return human-readable problems."""
    try:
        ComplianceAssessment.model_validate(data)
    except ValidationError as exc:
        return [_format_error(error) for error in exc.errors()]
    return []


def validate_compliance_assessment_file(input_dir: str | Path) -> list[str]:
    """Validate the canonical compliance summary JSON in ``input_dir``."""
    path = Path(input_dir) / COMPLIANCE_SUMMARY_FILENAME
    if not path.is_file():
        return [f"compliance summary file not found: {path}"]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]

    return validate_compliance_assessment_data(raw)
