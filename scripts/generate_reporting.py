#!/usr/bin/env python3
"""Generate, validate, and export the Milestone 6 governance reporting snapshot.

Run directly (``python scripts/generate_reporting.py``). This uses the same
deterministic Milestone 2-5 generators and evaluators as the existing scripts,
builds reporting-ready governance KPIs, writes outputs to ``outputs/reporting/``,
then reloads and validates the canonical JSON and KPI source references.

This is a local deterministic reporting layer. It does not deploy Microsoft
Fabric, create Power BI files, or perform live semantic-model refresh.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "outputs" / "reporting"

from governance_platform.access import (  # noqa: E402
    REFERENCE_EVALUATION_TIME,
    generate_access_control_state,
)
from governance_platform.audit import build_evidence_pack, generate_audit_log  # noqa: E402
from governance_platform.compliance import evaluate_compliance  # noqa: E402
from governance_platform.inventory import generate_portfolio  # noqa: E402
from governance_platform.reporting import (  # noqa: E402
    build_reporting_snapshot,
    export_reporting_snapshot,
    load_reporting_snapshot,
    unresolved_source_refs,
    validate_reporting_snapshot_file,
)

REPORTING_GENERATED_AT = datetime(2025, 3, 21)
EVIDENCE_GENERATED_AT = datetime(2025, 3, 20)
COMPLIANCE_EVALUATED_AT = datetime(2025, 3, 15)


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
    compliance_assessment = evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=COMPLIANCE_EVALUATED_AT,
    )
    snapshot = build_reporting_snapshot(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        compliance_assessment,
        snapshot_id="RS-0001",
        generated_at=REPORTING_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )

    unresolved = unresolved_source_refs(
        snapshot, inventory, access_state, audit_log, evidence_pack, compliance_assessment
    )
    if unresolved:
        print("Reporting source-reference validation FAILED:")
        for ref in unresolved:
            print(f"  - {ref}")
        return 1

    export_reporting_snapshot(snapshot, OUTPUT_DIR)
    problems = validate_reporting_snapshot_file(OUTPUT_DIR)
    if problems:
        print("Reporting output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    reloaded = load_reporting_snapshot(OUTPUT_DIR)
    print(f"Generated and validated reporting snapshot at {OUTPUT_DIR}")
    print(f"  KPIs:              {len(reloaded.all_metrics)}")
    print(f"  inventory metrics: {len(reloaded.inventory_metrics)}")
    print(f"  access metrics:    {len(reloaded.access_metrics)}")
    print(f"  audit metrics:     {len(reloaded.audit_metrics)}")
    print(f"  compliance metrics:{len(reloaded.compliance_metrics)}")
    print(f"  risk metrics:      {len(reloaded.risk_metrics)}")
    print(f"  posture:           {reloaded.posture.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
