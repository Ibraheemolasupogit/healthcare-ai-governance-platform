#!/usr/bin/env python3
"""Generate and validate Milestone 12 reviewer readiness outputs.

Run after all governance, reviewer, policy, assurance-history, and assurance
pack generators. This script evaluates deterministic review-readiness criteria,
exports checklist and demo-readiness artifacts under ``outputs/readiness/``,
then reloads and validates canonical outputs.

This is local review-readiness evidence only. It does not create human sign-off,
organisational approval, production acceptance, or regulatory certification.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
READINESS_OUTPUT_DIR = OUTPUTS_ROOT / "readiness"

from governance_platform.reviewer import (  # noqa: E402
    build_review_readiness_bundle,
    export_review_readiness_bundle,
    load_acceptance_checklist,
    load_demo_readiness,
    missing_readiness_source_paths,
    validate_review_readiness_outputs,
)

REQUIRED_REVIEW_READINESS_COMMANDS: tuple[str, ...] = (
    "python3 scripts/generate_inventory.py",
    "python3 scripts/generate_access.py",
    "python3 scripts/generate_evidence.py",
    "python3 scripts/generate_compliance.py",
    "python3 scripts/generate_reporting.py",
    "python3 scripts/generate_reviewer_bundle.py",
    "python3 scripts/generate_policy_catalog.py",
    "python3 scripts/generate_assurance_history.py",
    "python3 scripts/generate_assurance_pack.py",
)


def main() -> int:
    missing = missing_readiness_source_paths(OUTPUTS_ROOT)
    if missing:
        print("Review readiness generation FAILED: required generated outputs are missing.")
        for path in missing:
            print(f"  - {path}")
        print("Run the generation pipeline in this order:")
        for command in REQUIRED_REVIEW_READINESS_COMMANDS:
            print(f"  {command}")
        return 1

    try:
        bundle = build_review_readiness_bundle(OUTPUTS_ROOT)
    except (FileNotFoundError, ValueError) as exc:
        print("Review readiness generation FAILED: required generated outputs are missing.")
        print(f"  - {exc}")
        print("Run the generation pipeline in this order:")
        for command in REQUIRED_REVIEW_READINESS_COMMANDS:
            print(f"  {command}")
        return 1

    metadata = export_review_readiness_bundle(bundle, READINESS_OUTPUT_DIR)
    problems = validate_review_readiness_outputs(READINESS_OUTPUT_DIR)
    if problems:
        print("Review readiness output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    checklist = load_acceptance_checklist(READINESS_OUTPUT_DIR)
    demo = load_demo_readiness(READINESS_OUTPUT_DIR)
    print(f"Generated and validated review readiness at {READINESS_OUTPUT_DIR}")
    print(f"  checklist:          {checklist.checklist_id}")
    print(f"  readiness:          {checklist.readiness_status.value}")
    print(f"  demonstrated:       {metadata['demonstrated_count']}")
    print(f"  incomplete:         {metadata['incomplete_count']}")
    print(f"  not applicable:     {metadata['not_applicable_count']}")
    print(f"  artifacts:          {metadata['artifact_count']}")
    print(f"  demo readiness:     {demo.readiness_status.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
