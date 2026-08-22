"""Loading and export for the audit log and evidence pack.

Mirrors the inventory/access planes' convention: ``audit_events.json`` is the
canonical, lossless serialization of an :class:`~governance_platform.audit.log.AuditLog`
that :func:`load_audit_log` reads back, and ``evidence_pack.json`` is the
canonical serialization of an :class:`~governance_platform.audit.evidence.EvidencePack`
read back by :func:`load_evidence_pack`. ``audit_events.csv`` and
``evidence_pack.md`` are export-only, reviewer/tool-facing views.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

from governance_platform.audit.entities import AuditEvent
from governance_platform.audit.evidence import EvidencePack
from governance_platform.audit.log import AuditLog
from governance_platform.audit.markdown import render_evidence_pack_markdown
from governance_platform.audit.summary import AuditSummary

AUDIT_EVENTS_JSON_FILENAME = "audit_events.json"
AUDIT_EVENTS_CSV_FILENAME = "audit_events.csv"
AUDIT_SUMMARY_FILENAME = "audit_summary.json"
EVIDENCE_PACK_JSON_FILENAME = "evidence_pack.json"
EVIDENCE_PACK_MARKDOWN_FILENAME = "evidence_pack.md"

_LIST_FIELD_SEPARATOR = ";"
_DICT_ENTRY_SEPARATOR = ";"
_DICT_KV_SEPARATOR = "="

_EVENT_COLUMNS = list(AuditEvent.model_fields.keys())


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return _DICT_ENTRY_SEPARATOR.join(f"{k}{_DICT_KV_SEPARATOR}{v}" for k, v in value.items())
    if isinstance(value, tuple | list):
        return _LIST_FIELD_SEPARATOR.join(str(item) for item in value)
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "value"):  # Enum
        return str(value.value)
    return str(value)


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row[column]) for column in columns])


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def export_audit_log(audit_log: AuditLog, output_dir: str | Path) -> None:
    """Write ``audit_log`` to ``output_dir`` as canonical JSON plus a flattened CSV."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_json(out / AUDIT_EVENTS_JSON_FILENAME, audit_log.model_dump(mode="json"))
    _write_csv(
        out / AUDIT_EVENTS_CSV_FILENAME,
        _EVENT_COLUMNS,
        [e.model_dump(mode="json") for e in audit_log.events_in_order()],
    )


def load_audit_log(input_dir: str | Path) -> AuditLog:
    """Load and validate the canonical audit log JSON from ``input_dir``.

    Raises ``FileNotFoundError`` if ``audit_events.json`` is missing and
    ``pydantic.ValidationError`` if its contents don't form a valid,
    internally-consistent :class:`~governance_platform.audit.log.AuditLog`.
    """
    path = Path(input_dir) / AUDIT_EVENTS_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Audit events file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return AuditLog.model_validate(raw)


def export_audit_summary(summary: AuditSummary, output_dir: str | Path) -> None:
    """Write ``summary`` to ``output_dir`` as ``audit_summary.json``."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / AUDIT_SUMMARY_FILENAME, summary.model_dump(mode="json"))


def export_evidence_pack(pack: EvidencePack, output_dir: str | Path) -> None:
    """Write ``pack`` to ``output_dir`` as canonical JSON and reviewer-readable Markdown."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_json(out / EVIDENCE_PACK_JSON_FILENAME, pack.model_dump(mode="json"))
    (out / EVIDENCE_PACK_MARKDOWN_FILENAME).write_text(
        render_evidence_pack_markdown(pack), encoding="utf-8"
    )


def load_evidence_pack(input_dir: str | Path) -> EvidencePack:
    """Load and validate the canonical evidence pack JSON from ``input_dir``.

    Raises ``FileNotFoundError`` if ``evidence_pack.json`` is missing and
    ``pydantic.ValidationError`` if its contents don't form a valid
    :class:`~governance_platform.audit.evidence.EvidencePack`.
    """
    path = Path(input_dir) / EVIDENCE_PACK_JSON_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Evidence pack file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return EvidencePack.model_validate(raw)
