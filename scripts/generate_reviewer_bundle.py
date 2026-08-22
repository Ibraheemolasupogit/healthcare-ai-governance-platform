#!/usr/bin/env python3
"""Generate and validate the Milestone 8 reviewer briefing bundle.

Run after the Milestone 2-6 generation scripts. This script loads the existing
canonical generated outputs, builds concise reviewer handoff artifacts under
``outputs/reviewer/``, reloads the canonical briefing, and validates expected
bundle files.

This is local deterministic packaging over synthetic governance outputs only.
It does not deploy infrastructure, start approval workflows, or create any
production reporting artifact.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
REVIEWER_OUTPUT_DIR = OUTPUTS_ROOT / "reviewer"

from governance_platform.reviewer import (  # noqa: E402
    MissingGeneratedOutputError,
    build_reviewer_evidence_index,
    export_reviewer_bundle,
    load_reviewer_briefing,
    load_reviewer_state,
    missing_output_paths,
    unresolved_evidence_refs,
    validate_reviewer_bundle,
)


def main() -> int:
    missing = missing_output_paths(OUTPUTS_ROOT)
    if missing:
        print("Reviewer bundle generation FAILED: required generated outputs are missing.")
        for path in missing:
            print(f"  - {path}")
        print("Run the inventory, access, evidence, compliance, and reporting generators first.")
        return 1

    try:
        state = load_reviewer_state(OUTPUTS_ROOT)
    except MissingGeneratedOutputError as exc:
        print(str(exc))
        return 1

    evidence_index = build_reviewer_evidence_index(state)
    unresolved = unresolved_evidence_refs(state, evidence_index)
    if unresolved:
        print("Reviewer evidence-reference validation FAILED:")
        for ref in unresolved:
            print(f"  - {ref}")
        return 1

    metadata = export_reviewer_bundle(state, REVIEWER_OUTPUT_DIR)
    problems = validate_reviewer_bundle(REVIEWER_OUTPUT_DIR)
    if problems:
        print("Reviewer bundle validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    briefing = load_reviewer_briefing(REVIEWER_OUTPUT_DIR)
    print(f"Generated and validated reviewer bundle at {REVIEWER_OUTPUT_DIR}")
    print(f"  briefing:           {briefing.briefing_id}")
    print(f"  KPIs:               {metadata['kpi_count']}")
    print(f"  findings:           {metadata['finding_count']}")
    print(f"  evidence refs:      {metadata['evidence_ref_count']}")
    print(f"  filtered views:     {metadata['filtered_view_count']}")
    print(f"  filtered view rows: {metadata['filtered_view_row_count']}")
    print(f"  posture:            {briefing.governance_posture}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
