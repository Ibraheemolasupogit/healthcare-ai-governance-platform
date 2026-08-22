#!/usr/bin/env python3
"""Generate and validate the Milestone 11 integrated assurance review pack.

Run after reviewer bundle, policy catalog, and assurance-history generation.
This script loads canonical generated outputs, builds a concise reviewer-ready
assurance pack, exports it under ``outputs/assurance_pack/``, then reloads and
validates the canonical representation.

This is local deterministic handoff packaging over synthetic governance outputs
only. It does not evaluate new controls, score new risks, run workflows, send
notifications, remediate issues, or create production assurance storage.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
ASSURANCE_PACK_OUTPUT_DIR = OUTPUTS_ROOT / "assurance_pack"

from governance_platform.compliance import (  # noqa: E402
    load_assurance_comparison,
    load_control_catalog,
    load_policy_assurance_summary,
    load_policy_catalog,
)
from governance_platform.reviewer import (  # noqa: E402
    build_assurance_review_pack,
    build_reviewer_evidence_index,
    export_assurance_review_pack_bundle,
    load_assurance_review_pack,
    load_reviewer_briefing,
    load_reviewer_state,
    missing_assurance_output_paths,
    missing_output_paths,
    missing_policy_output_paths,
    validate_assurance_review_pack,
)

REQUIRED_ASSURANCE_PACK_COMMANDS: tuple[str, ...] = (
    "python3 scripts/generate_inventory.py",
    "python3 scripts/generate_access.py",
    "python3 scripts/generate_evidence.py",
    "python3 scripts/generate_compliance.py",
    "python3 scripts/generate_reporting.py",
    "python3 scripts/generate_reviewer_bundle.py",
    "python3 scripts/generate_policy_catalog.py",
    "python3 scripts/generate_assurance_history.py",
)


def _required_reviewer_paths(outputs_root: Path) -> tuple[Path, ...]:
    return (
        outputs_root / "reviewer" / "reviewer_briefing.json",
        outputs_root / "reviewer" / "reviewer_evidence_index.csv",
    )


def _missing_reviewer_paths(outputs_root: Path) -> tuple[Path, ...]:
    return tuple(path for path in _required_reviewer_paths(outputs_root) if not path.is_file())


def _missing_pack_sources(outputs_root: Path) -> tuple[Path, ...]:
    return (
        *missing_output_paths(outputs_root),
        *_missing_reviewer_paths(outputs_root),
        *missing_policy_output_paths(outputs_root),
        *missing_assurance_output_paths(outputs_root),
    )


def main() -> int:
    missing = _missing_pack_sources(OUTPUTS_ROOT)
    if missing:
        print("Assurance review pack generation FAILED: required generated outputs are missing.")
        for path in missing:
            print(f"  - {path}")
        print("Run the generation pipeline in this order:")
        for command in REQUIRED_ASSURANCE_PACK_COMMANDS:
            print(f"  {command}")
        return 1

    try:
        state = load_reviewer_state(OUTPUTS_ROOT)
        briefing = load_reviewer_briefing(OUTPUTS_ROOT / "reviewer")
        policies = load_policy_catalog(OUTPUTS_ROOT / "policy")
        controls = load_control_catalog(OUTPUTS_ROOT / "policy")
        policy_summary = load_policy_assurance_summary(OUTPUTS_ROOT / "policy")
        comparison = load_assurance_comparison(OUTPUTS_ROOT / "assurance")
        evidence_index = build_reviewer_evidence_index(state)
        bundle = build_assurance_review_pack(
            state,
            briefing,
            policies,
            controls,
            policy_summary,
            comparison,
            evidence_index=evidence_index,
        )
    except (FileNotFoundError, ValueError) as exc:
        print("Assurance review pack validation FAILED:")
        print(f"  - {exc}")
        return 1

    metadata = export_assurance_review_pack_bundle(bundle, ASSURANCE_PACK_OUTPUT_DIR)
    problems = validate_assurance_review_pack(ASSURANCE_PACK_OUTPUT_DIR)
    if problems:
        print("Assurance review pack output validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    pack = load_assurance_review_pack(ASSURANCE_PACK_OUTPUT_DIR)
    print(f"Generated and validated assurance review pack at {ASSURANCE_PACK_OUTPUT_DIR}")
    print(f"  pack:                  {pack.pack_id}")
    print(f"  posture:               {pack.governance_posture}")
    print(f"  bounded risk score:    {pack.bounded_risk_score}")
    print(f"  priority findings:     {metadata['priority_finding_count']}")
    print(f"  reviewer actions:      {metadata['reviewer_action_count']}")
    print(f"  evidence map rows:     {metadata['evidence_map_row_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
