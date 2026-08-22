"""Loading and export for the access-control state.

Mirrors ``governance_platform.inventory.io``'s convention:
``access_control_state.json`` is the canonical, lossless serialization that
:func:`load_access_state` reads back; the per-entity CSVs and
``access_review_summary.json`` are export-only, stable machine-readable
views. List-valued fields (``requested_dataset_ids``, ``dataset_ids``, etc.)
are flattened to a semicolon-joined string for CSV, so they are not read back
by :func:`load_access_state`.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

from governance_platform.access.entities import AccessGrant, AccessRequest, ApprovalDecision
from governance_platform.access.portfolio import AccessControlPortfolio
from governance_platform.access.summary import build_access_summary
from governance_platform.inventory import InventoryPortfolio

ACCESS_STATE_FILENAME = "access_control_state.json"
ACCESS_REQUESTS_CSV_FILENAME = "access_requests.csv"
APPROVAL_DECISIONS_CSV_FILENAME = "approval_decisions.csv"
ACCESS_GRANTS_CSV_FILENAME = "access_grants.csv"
ACCESS_REVIEW_SUMMARY_FILENAME = "access_review_summary.json"

_LIST_FIELD_SEPARATOR = ";"

_REQUEST_COLUMNS = list(AccessRequest.model_fields.keys())
_DECISION_COLUMNS = list(ApprovalDecision.model_fields.keys())
_GRANT_COLUMNS = list(AccessGrant.model_fields.keys())


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
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


def export_access_state(
    state: AccessControlPortfolio,
    inventory: InventoryPortfolio,
    *,
    evaluated_at: datetime,
    output_dir: str | Path,
) -> None:
    """Write ``state`` to ``output_dir`` as JSON + CSV, creating it if needed.

    Writes the canonical ``access_control_state.json``, one CSV per entity
    type, and ``access_review_summary.json`` (built against ``inventory`` and
    ``evaluated_at`` — see :func:`~governance_platform.access.summary.build_access_summary`).
    All output is deterministic: identical inputs always produce
    byte-identical files.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / ACCESS_STATE_FILENAME).write_text(
        json.dumps(state.model_dump(mode="json"), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    _write_csv(
        out / ACCESS_REQUESTS_CSV_FILENAME,
        _REQUEST_COLUMNS,
        [r.model_dump(mode="json") for r in state.requests],
    )
    _write_csv(
        out / APPROVAL_DECISIONS_CSV_FILENAME,
        _DECISION_COLUMNS,
        [d.model_dump(mode="json") for d in state.decisions],
    )
    _write_csv(
        out / ACCESS_GRANTS_CSV_FILENAME,
        _GRANT_COLUMNS,
        [g.model_dump(mode="json") for g in state.grants],
    )

    summary = build_access_summary(state, inventory, evaluated_at=evaluated_at)
    (out / ACCESS_REVIEW_SUMMARY_FILENAME).write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def load_access_state(input_dir: str | Path) -> AccessControlPortfolio:
    """Load and validate the canonical access-control state JSON from ``input_dir``.

    Raises ``FileNotFoundError`` if ``access_control_state.json`` is missing
    and ``pydantic.ValidationError`` if its contents don't form a valid,
    internally-consistent :class:`AccessControlPortfolio`.
    """
    state_path = Path(input_dir) / ACCESS_STATE_FILENAME
    if not state_path.is_file():
        raise FileNotFoundError(f"Access control state file not found: {state_path}")

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    return AccessControlPortfolio.model_validate(raw)
