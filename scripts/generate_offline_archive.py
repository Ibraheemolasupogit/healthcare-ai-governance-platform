#!/usr/bin/env python3
"""Generate and validate the deterministic offline assurance manifest."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
ARCHIVE_OUTPUT_DIR = OUTPUTS_ROOT / "archive"

from governance_platform.reviewer import (  # noqa: E402
    build_archive_manifest,
    export_archive_bundle,
    load_archive_manifest,
    load_archive_validation,
    validate_archive_manifest,
)


def main() -> int:
    try:
        manifest = build_archive_manifest(REPO_ROOT)
        export_archive_bundle(manifest, ARCHIVE_OUTPUT_DIR, REPO_ROOT)
        reloaded = load_archive_manifest(ARCHIVE_OUTPUT_DIR)
        validation = validate_archive_manifest(reloaded, REPO_ROOT)
        stored_validation = load_archive_validation(ARCHIVE_OUTPUT_DIR)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Offline archive generation FAILED: {exc}")
        print("Run the Milestone 1-12 generation pipeline before this command.")
        return 1
    if validation != stored_validation or validation.status.value != "passed":
        print("Offline archive validation FAILED:")
        for issue in validation.issues:
            print(f"  - {issue}")
        return 1
    print(f"Generated and validated offline archive manifest at {ARCHIVE_OUTPUT_DIR}")
    print(f"  manifest:              {reloaded.manifest_id}")
    print(f"  artifacts:             {reloaded.artifact_count}")
    print(f"  required artifacts:    {reloaded.required_artifact_count}")
    print(f"  total bytes:           {reloaded.total_size_bytes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
