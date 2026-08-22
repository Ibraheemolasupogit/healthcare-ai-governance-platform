#!/usr/bin/env python3
"""Smoke-check the local reviewer demo handoff.

The smoke check validates generated outputs, reviewer data loading, briefing
construction, common drill-through/filter helpers, Streamlit availability, and
a brief headless Streamlit startup. It stops the server before exiting.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"

from governance_platform.reviewer.smoke import run_smoke_checks  # noqa: E402


def main() -> int:
    try:
        result = run_smoke_checks(OUTPUTS_ROOT, start_streamlit=True)
    except Exception as exc:  # noqa: BLE001 - CLI smoke script reports any failed check.
        print("Reviewer demo smoke check FAILED:")
        print(f"  - {exc}")
        return 1

    print("Reviewer demo smoke check passed.")
    print(f"  snapshot:          {result['snapshot_id']}")
    print(f"  briefing:          {result['briefing_id']}")
    print(f"  evidence refs:     {result['evidence_ref_count']}")
    print(f"  filtered views:    {result['filtered_view_count']}")
    print(f"  streamlit startup: {result['streamlit_headless_start']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
