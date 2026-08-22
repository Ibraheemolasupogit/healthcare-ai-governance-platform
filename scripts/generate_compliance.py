#!/usr/bin/env python3
"""Generate, validate, and export the Milestone 5 compliance assessment.

Run directly (``python scripts/generate_compliance.py``). This uses the same
deterministic Milestone 2-4 generators as the existing scripts, evaluates the
fixed compliance controls, derives bounded risk indicators and posture, writes
outputs to ``outputs/compliance/``, then reloads and validates the canonical
JSON.

This is a local deterministic governance simulation. It is not formal
regulatory compliance, live monitoring, alerting, or production policy
enforcement.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs" / "compliance"

from governance_platform.access import (  # noqa: E402
    REFERENCE_EVALUATION_TIME,
    generate_access_control_state,
)
from governance_platform.audit import build_evidence_pack, generate_audit_log  # noqa: E402
from governance_platform.compliance import (  # noqa: E402
    evaluate_compliance,
    export_compliance_assessment,
    load_compliance_assessment,
    validate_compliance_assessment_file,
)
from governance_platform.inventory import generate_portfolio  # noqa: E402

COMPLIANCE_EVALUATED_AT = datetime(2025, 3, 15)
EVIDENCE_GENERATED_AT = datetime(2025, 3, 20)


def main() -> int:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    evidence_pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=EVIDENCE_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )

    assessment = evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=COMPLIANCE_EVALUATED_AT,
    )
    export_compliance_assessment(assessment, OUTPUT_DIR)

    problems = validate_compliance_assessment_file(OUTPUT_DIR)
    if problems:
        print("Compliance output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    reloaded = load_compliance_assessment(OUTPUT_DIR)
    print(f"Generated and validated compliance assessment at {OUTPUT_DIR}")
    print(f"  control results:  {len(reloaded.control_results)}")
    print(f"  passed:           {reloaded.summary.passed_controls}")
    print(f"  warnings:         {reloaded.summary.warning_controls}")
    print(f"  failures:         {reloaded.summary.failed_controls}")
    print(f"  risk indicators:  {len(reloaded.risk_indicators)}")
    print(f"  bounded score:    {reloaded.summary.total_bounded_risk_score}")
    print(f"  posture:          {reloaded.posture.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
