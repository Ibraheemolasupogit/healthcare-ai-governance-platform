"""Validate raw inventory data without raising, for CLI-style reporting.

:class:`~governance_platform.inventory.portfolio.InventoryPortfolio` already
enforces every invariant at construction time by raising
``pydantic.ValidationError``. This module exists for callers that want a list
of human-readable problems instead (mirroring ``scripts/validate_repository.py``'s
``validate() -> list[str]`` shape) — e.g. a CLI that wants to report every
problem found in a hand-edited inventory file rather than stopping at the
first exception.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from governance_platform.inventory.io import PORTFOLIO_FILENAME
from governance_platform.inventory.portfolio import InventoryPortfolio


def _format_error(error: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in error["loc"]) or "<portfolio>"
    return f"{location}: {error['msg']}"


def validate_portfolio_data(data: dict[str, Any]) -> list[str]:
    """Validate raw ``data`` (as produced by ``InventoryPortfolio.model_dump(mode='json')``).

    Returns a list of human-readable problems; an empty list means ``data``
    describes a fully valid, internally-consistent portfolio.
    """
    try:
        InventoryPortfolio.model_validate(data)
    except ValidationError as exc:
        return [_format_error(error) for error in exc.errors()]
    return []


def validate_portfolio_file(input_dir: str | Path) -> list[str]:
    """Validate the canonical portfolio JSON in ``input_dir``.

    Returns a list of human-readable problems (including a missing-file
    problem rather than raising ``FileNotFoundError``), so this is safe to
    call from a CLI without a surrounding try/except.
    """
    portfolio_path = Path(input_dir) / PORTFOLIO_FILENAME
    if not portfolio_path.is_file():
        return [f"inventory portfolio file not found: {portfolio_path}"]

    try:
        raw = json.loads(portfolio_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{portfolio_path}: invalid JSON ({exc})"]

    return validate_portfolio_data(raw)
