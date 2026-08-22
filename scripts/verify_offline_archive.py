#!/usr/bin/env python3
"""Verify offline archive files and checksums without regenerating state."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = REPO_ROOT / "outputs" / "archive"

from governance_platform.reviewer import verify_archive  # noqa: E402


def main() -> int:
    try:
        result = verify_archive(ARCHIVE_DIR, REPO_ROOT)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Offline archive verification FAILED: {exc}")
        return 1
    if result.status.value != "passed":
        print("Offline archive verification FAILED:")
        for issue in result.issues:
            print(f"  - {issue}")
        return 1
    print("Offline archive verification passed.")
    print("  checksum validation: passed")
    print("  required artifacts:  present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
