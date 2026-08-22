#!/usr/bin/env python3
"""Generate, validate, and export the Milestone 2 synthetic governance inventory.

Run directly (``python scripts/generate_inventory.py``). Generates the fixed,
deterministic synthetic dataset/model/research-project portfolio from
``governance_platform.inventory``, writes it to ``outputs/inventory/``, then
reloads and re-validates the written files as an end-to-end check that the
generate -> export -> load -> validate path is consistent.

This does not implement access review, audit, risk scoring, or any other
governance logic — see the root README's Implemented vs. Planned section.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs" / "inventory"

from governance_platform.inventory import (  # noqa: E402
    build_summary,
    export_portfolio,
    generate_portfolio,
    load_portfolio,
    validate_portfolio_file,
)


def main() -> int:
    portfolio = generate_portfolio()
    export_portfolio(portfolio, OUTPUT_DIR)

    problems = validate_portfolio_file(OUTPUT_DIR)
    if problems:
        print("Inventory validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    reloaded = load_portfolio(OUTPUT_DIR)
    summary = build_summary(reloaded)

    print(f"Generated and validated inventory at {OUTPUT_DIR}")
    print(f"  datasets:          {summary.entity_counts.datasets}")
    print(f"  models:            {summary.entity_counts.models}")
    print(f"  research_projects: {summary.entity_counts.research_projects}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
