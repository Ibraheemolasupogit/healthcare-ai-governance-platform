#!/usr/bin/env python3
"""Generate and validate Milestone 10 assurance-history drift outputs.

Run after policy catalog generation. This loads the canonical compliance
assessment and control catalog, builds an explicit baseline snapshot plus a
controlled deterministic comparison snapshot, exports drift artifacts under
``outputs/assurance/``, then reloads and validates canonical outputs.

This is local deterministic historical comparison over synthetic governance
outputs only. It does not provide live monitoring, scheduling, alerting,
remediation, production observability, or regulatory certification.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
ASSURANCE_OUTPUT_DIR = OUTPUTS_ROOT / "assurance"

from governance_platform.compliance import (  # noqa: E402
    build_assurance_history_bundle,
    export_assurance_history_bundle,
    load_assurance_comparison,
    load_assurance_history,
    load_compliance_assessment,
    load_control_catalog,
    validate_assurance_history_files,
)


def main() -> int:
    try:
        assessment = load_compliance_assessment(OUTPUTS_ROOT / "compliance")
        control_catalog = load_control_catalog(OUTPUTS_ROOT / "policy")
    except FileNotFoundError as exc:
        print("Assurance history generation FAILED: required generated outputs are missing.")
        print(f"  - {exc}")
        print("Run the compliance and policy catalog generators first.")
        return 1

    try:
        bundle = build_assurance_history_bundle(assessment, control_catalog)
    except ValueError as exc:
        print("Assurance history validation FAILED:")
        print(f"  - {exc}")
        return 1

    export_assurance_history_bundle(bundle, ASSURANCE_OUTPUT_DIR)
    problems = validate_assurance_history_files(ASSURANCE_OUTPUT_DIR)
    if problems:
        print("Assurance history output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    history = load_assurance_history(ASSURANCE_OUTPUT_DIR)
    comparison = load_assurance_comparison(ASSURANCE_OUTPUT_DIR)
    print(f"Generated and validated assurance history at {ASSURANCE_OUTPUT_DIR}")
    print(f"  snapshots:          {len(history.snapshots)}")
    print(f"  comparison:         {comparison.comparison_id}")
    print(f"  control drifts:     {len(comparison.control_drifts)}")
    print(f"  risk drifts:        {len(comparison.risk_drifts)}")
    print(f"  risk score delta:   {comparison.risk_score_delta}")
    print(f"  posture transition: {comparison.summary['posture_transition']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
