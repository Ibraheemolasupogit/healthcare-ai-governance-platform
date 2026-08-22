"""Validate raw audit log / evidence pack data without raising, for CLI-style reporting.

Mirrors ``governance_platform.inventory.validation`` and
``governance_platform.access.validation``:
:class:`~governance_platform.audit.log.AuditLog` and
:class:`~governance_platform.audit.evidence.EvidencePack` already enforce
their own structural invariants at construction time by raising
``pydantic.ValidationError``. This module exists for callers that want a list
of human-readable problems instead.

This only validates structure (well-formed events, internal uniqueness and
ordering) — cross-plane evidence completeness against the inventory and
access-control state is a separate concern, handled by
:mod:`governance_platform.audit.completeness`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from governance_platform.audit.evidence import EvidencePack
from governance_platform.audit.io import AUDIT_EVENTS_JSON_FILENAME, EVIDENCE_PACK_JSON_FILENAME
from governance_platform.audit.log import AuditLog


def _format_error(error: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in error["loc"]) or "<audit log>"
    return f"{location}: {error['msg']}"


def validate_audit_log_data(data: dict[str, Any]) -> list[str]:
    """Validate raw ``data`` (as produced by ``AuditLog.model_dump(mode='json')``).

    Returns a list of human-readable problems; an empty list means ``data``
    describes a fully valid, internally-consistent audit log.
    """
    try:
        AuditLog.model_validate(data)
    except ValidationError as exc:
        return [_format_error(error) for error in exc.errors()]
    return []


def validate_audit_log_file(input_dir: str | Path) -> list[str]:
    """Validate the canonical audit events JSON in ``input_dir``.

    Returns a list of human-readable problems (including a missing-file
    problem rather than raising ``FileNotFoundError``).
    """
    path = Path(input_dir) / AUDIT_EVENTS_JSON_FILENAME
    if not path.is_file():
        return [f"audit events file not found: {path}"]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]

    return validate_audit_log_data(raw)


def validate_evidence_pack_file(input_dir: str | Path) -> list[str]:
    """Validate the canonical evidence pack JSON in ``input_dir``.

    Returns a list of human-readable problems (including a missing-file
    problem rather than raising ``FileNotFoundError``).
    """
    path = Path(input_dir) / EVIDENCE_PACK_JSON_FILENAME
    if not path.is_file():
        return [f"evidence pack file not found: {path}"]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]

    try:
        EvidencePack.model_validate(raw)
    except ValidationError as exc:
        return [_format_error(error) for error in exc.errors()]
    return []
