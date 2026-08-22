#!/usr/bin/env python3
"""Generate, evaluate, validate, and export the Milestone 3 synthetic access-control state.

Run directly (``python scripts/generate_access.py``). Loads the deterministic
Milestone 2 synthetic inventory, runs the fixed set of Milestone 3 access
scenarios through ``governance_platform.access.AccessControlService``, writes
the resulting requests/decisions/grants to ``outputs/access/``, then reloads
and re-validates the written files, and confirms every active/expired/revoked
grant is classified the way the summary says it is.

This is a local governance simulation — it does not authenticate anyone,
does not call Snowflake, Entra ID, or any other identity system, and does not
enforce access to anything. See the root README's Explicit non-goals section.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs" / "access"

from governance_platform.access import (  # noqa: E402
    REFERENCE_EVALUATION_TIME,
    AccessControlService,
    export_access_state,
    generate_access_control_state,
    load_access_state,
    validate_access_state_file,
)
from governance_platform.inventory import generate_portfolio  # noqa: E402


def main() -> int:
    inventory = generate_portfolio()
    state = generate_access_control_state()

    export_access_state(
        state, inventory, evaluated_at=REFERENCE_EVALUATION_TIME, output_dir=OUTPUT_DIR
    )

    problems = validate_access_state_file(OUTPUT_DIR)
    if problems:
        print("Access control state validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    reloaded = load_access_state(OUTPUT_DIR)
    active_grants = [
        g
        for g in reloaded.grants
        if AccessControlService.is_grant_active(g, REFERENCE_EVALUATION_TIME)
    ]
    expired_grants = AccessControlService.expired_grants(reloaded.grants, REFERENCE_EVALUATION_TIME)
    revoked_grants = [g for g in reloaded.grants if g.status.value == "revoked"]

    print(f"Generated and validated access control state at {OUTPUT_DIR}")
    print(f"  requests:  {len(reloaded.requests)}")
    print(f"  decisions: {len(reloaded.decisions)}")
    print(f"  grants:    {len(reloaded.grants)}")
    print(f"    active:  {len(active_grants)}")
    print(f"    expired: {len(expired_grants)}")
    print(f"    revoked: {len(revoked_grants)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
