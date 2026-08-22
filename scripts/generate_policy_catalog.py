#!/usr/bin/env python3
"""Generate and validate the Milestone 9 policy/control catalog.

Run after the inventory, access, evidence, compliance, reporting, and reviewer
bundle generators. This loads existing implemented control definitions and the
current compliance assessment, builds local policy/control catalog metadata,
exports traceability artifacts under ``outputs/policy/``, then reloads and
validates canonical outputs.

This is a local deterministic catalog over implemented controls. It is not a
generic policy engine, live enforcement system, or regulatory certification.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
POLICY_OUTPUT_DIR = OUTPUTS_ROOT / "policy"

from governance_platform.compliance import (  # noqa: E402
    build_policy_catalog_bundle,
    export_policy_catalog_bundle,
    load_compliance_assessment,
    load_control_catalog,
    load_policy_assurance_summary,
    load_policy_catalog,
    validate_policy_catalog_files,
)
from governance_platform.reviewer import (  # noqa: E402
    build_reviewer_evidence_index,
    load_reviewer_state,
)


def main() -> int:
    try:
        assessment = load_compliance_assessment(OUTPUTS_ROOT / "compliance")
        reviewer_state = load_reviewer_state(OUTPUTS_ROOT)
    except FileNotFoundError as exc:
        print("Policy catalog generation FAILED: required generated outputs are missing.")
        print(f"  - {exc}")
        print(
            "Run the inventory, access, evidence, compliance, reporting, and reviewer "
            "generators first."
        )
        return 1

    known_evidence_refs = {
        entry.evidence_ref for entry in build_reviewer_evidence_index(reviewer_state)
    }
    try:
        bundle = build_policy_catalog_bundle(
            assessment,
            known_evidence_refs=known_evidence_refs,
        )
    except ValueError as exc:
        print("Policy catalog validation FAILED:")
        print(f"  - {exc}")
        return 1

    export_policy_catalog_bundle(bundle, POLICY_OUTPUT_DIR)
    problems = validate_policy_catalog_files(POLICY_OUTPUT_DIR)
    if problems:
        print("Policy catalog output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    policies = load_policy_catalog(POLICY_OUTPUT_DIR)
    controls = load_control_catalog(POLICY_OUTPUT_DIR)
    summary = load_policy_assurance_summary(POLICY_OUTPUT_DIR)
    print(f"Generated and validated policy catalog at {POLICY_OUTPUT_DIR}")
    print(f"  policies:              {len(policies)}")
    print(f"  controls:              {len(controls)}")
    print(f"  evidence requirements: {summary.evidence_requirement_count}")
    print(f"  traceability rows:     {summary.traceability_row_count}")
    print(f"  warnings:              {summary.evaluation_status_counts.get('warning', 0)}")
    print(f"  failures:              {summary.evaluation_status_counts.get('fail', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
