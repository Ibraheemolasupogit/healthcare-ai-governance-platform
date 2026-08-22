"""Validate raw access-control state data without raising, for CLI-style reporting.

Mirrors ``governance_platform.inventory.validation``:
:class:`~governance_platform.access.portfolio.AccessControlPortfolio` already
enforces every structural invariant at construction time by raising
``pydantic.ValidationError``. This module exists for callers that want a list
of human-readable problems instead.

This only validates the access plane's own internal referential integrity
(duplicate IDs, decisions/grants referencing unknown requests, grants without
an approved decision) — it does not re-run inventory eligibility policy,
which is a property of a request/inventory pair, not of the state file alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from governance_platform.access.io import ACCESS_STATE_FILENAME
from governance_platform.access.portfolio import AccessControlPortfolio


def _format_error(error: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in error["loc"]) or "<access control state>"
    return f"{location}: {error['msg']}"


def validate_access_state_data(data: dict[str, Any]) -> list[str]:
    """Validate raw ``data`` (as produced by ``AccessControlPortfolio.model_dump(mode='json')``).

    Returns a list of human-readable problems; an empty list means ``data``
    describes a fully valid, internally-consistent access-control state.
    """
    try:
        AccessControlPortfolio.model_validate(data)
    except ValidationError as exc:
        return [_format_error(error) for error in exc.errors()]
    return []


def validate_access_state_file(input_dir: str | Path) -> list[str]:
    """Validate the canonical access-control state JSON in ``input_dir``.

    Returns a list of human-readable problems (including a missing-file
    problem rather than raising ``FileNotFoundError``), so this is safe to
    call from a CLI without a surrounding try/except.
    """
    state_path = Path(input_dir) / ACCESS_STATE_FILENAME
    if not state_path.is_file():
        return [f"access control state file not found: {state_path}"]

    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{state_path}: invalid JSON ({exc})"]

    return validate_access_state_data(raw)
