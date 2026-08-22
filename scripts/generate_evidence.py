#!/usr/bin/env python3
"""Generate, validate, and export the Milestone 4 synthetic audit log and evidence pack.

Run directly (``python scripts/generate_evidence.py``). Loads the
deterministic Milestone 2 inventory and runs the deterministic Milestone 3
access scenarios (the same generators ``scripts/generate_inventory.py`` and
``scripts/generate_access.py`` use — no separate synthetic universe), builds
the audit log from that existing state via
``governance_platform.audit.generate_audit_log``, checks evidence
completeness, derives the evidence pack, writes everything to
``outputs/evidence/``, then reloads and re-validates the canonical JSON
representations.

This is a local, deterministic governance simulation. It does not implement
a real SIEM, cloud audit service, or any live Snowflake/Entra ID/Microsoft
Purview integration — see the root README's Explicit non-goals section.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs" / "evidence"

from governance_platform.access import (  # noqa: E402
    REFERENCE_EVALUATION_TIME,
    generate_access_control_state,
)
from governance_platform.audit import (  # noqa: E402
    build_audit_summary,
    build_evidence_pack,
    check_completeness,
    export_audit_log,
    export_audit_summary,
    export_evidence_pack,
    generate_audit_log,
    load_audit_log,
    load_evidence_pack,
    validate_audit_log_file,
    validate_evidence_pack_file,
)
from governance_platform.inventory import generate_portfolio  # noqa: E402

#: The instant this evidence pack claims to represent — a fixed, explicitly
#: supplied placeholder, not the system clock. Chosen after every synthetic
#: scenario's activity so the pack reads as "as of" a coherent point in time.
EVIDENCE_GENERATED_AT = datetime(2025, 3, 20)


def main() -> int:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    completeness_problems = check_completeness(audit_log, inventory, access_state)
    if completeness_problems:
        print("Audit evidence completeness check FAILED:")
        for problem in completeness_problems:
            print(f"  - {problem}")
        return 1

    pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=EVIDENCE_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )

    export_audit_log(audit_log, OUTPUT_DIR)
    export_audit_summary(build_audit_summary(audit_log, access_state), OUTPUT_DIR)
    export_evidence_pack(pack, OUTPUT_DIR)

    problems = validate_audit_log_file(OUTPUT_DIR) + validate_evidence_pack_file(OUTPUT_DIR)
    if problems:
        print("Evidence output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    reloaded_log = load_audit_log(OUTPUT_DIR)
    reloaded_pack = load_evidence_pack(OUTPUT_DIR)

    print(f"Generated and validated evidence pack at {OUTPUT_DIR}")
    print(f"  audit events:      {len(reloaded_log.events)}")
    print(f"  correlation groups: {len(reloaded_pack.correlation_groups)}")
    print(f"  rejected access:   {len(reloaded_pack.rejected_access)}")
    print(f"  grants:            {len(reloaded_pack.grants)}")
    status = "COMPLETE" if reloaded_pack.completeness.complete else "INCOMPLETE"
    print(f"  completeness:      {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
