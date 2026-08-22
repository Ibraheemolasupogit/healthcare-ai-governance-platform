#!/usr/bin/env python3
"""Run the complete deterministic portfolio assurance path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_ROOT = REPO_ROOT / "outputs"
FINAL_OUTPUT_DIR = OUTPUTS_ROOT / "final"

from governance_platform.reviewer import (  # noqa: E402
    build_portfolio_assurance_summary,
    export_portfolio_assurance_summary,
    load_portfolio_assurance_summary,
)

PIPELINE_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("inventory", (sys.executable, "scripts/generate_inventory.py")),
    ("access", (sys.executable, "scripts/generate_access.py")),
    ("evidence", (sys.executable, "scripts/generate_evidence.py")),
    ("compliance", (sys.executable, "scripts/generate_compliance.py")),
    ("reporting", (sys.executable, "scripts/generate_reporting.py")),
    ("reviewer_bundle", (sys.executable, "scripts/generate_reviewer_bundle.py")),
    ("policy_catalog", (sys.executable, "scripts/generate_policy_catalog.py")),
    ("assurance_history", (sys.executable, "scripts/generate_assurance_history.py")),
    ("assurance_pack", (sys.executable, "scripts/generate_assurance_pack.py")),
    ("review_readiness", (sys.executable, "scripts/generate_review_readiness.py")),
    ("offline_archive", (sys.executable, "scripts/generate_offline_archive.py")),
    ("archive_verification", (sys.executable, "scripts/verify_offline_archive.py")),
)

QUALITY_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lint", (sys.executable, "-m", "ruff", "check", ".")),
    ("format", (sys.executable, "-m", "ruff", "format", "--check", ".")),
    ("tests", (sys.executable, "-m", "pytest", "-q")),
    ("repository_validation", (sys.executable, "scripts/validate_repository.py")),
    ("reviewer_smoke", (sys.executable, "scripts/smoke_reviewer_demo.py")),
)


def _run_step(name: str, command: tuple[str, ...]) -> str:
    print(f"[portfolio-assurance] {name}: running")
    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError(f"step {name!r} failed with exit code {result.returncode}")
    print(f"[portfolio-assurance] {name}: passed")
    return "passed"


def main() -> int:
    try:
        for name, command in PIPELINE_STEPS:
            _run_step(name, command)
        quality = {name: _run_step(name, command) for name, command in QUALITY_STEPS}
        summary = build_portfolio_assurance_summary(
            OUTPUTS_ROOT,
            lint_status=quality["lint"],
            format_status=quality["format"],
            tests_status=quality["tests"],
            repository_validation_status=quality["repository_validation"],
            reviewer_smoke_status=quality["reviewer_smoke"],
        )
        export_portfolio_assurance_summary(summary, FINAL_OUTPUT_DIR)
        reloaded = load_portfolio_assurance_summary(FINAL_OUTPUT_DIR)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[portfolio-assurance] FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"[portfolio-assurance] final summary: {reloaded.summary_id}")
    print(f"[portfolio-assurance] readiness: {reloaded.review_readiness_status}")
    print(f"[portfolio-assurance] archive: {reloaded.archive_validation_status}")
    print(f"[portfolio-assurance] output: {FINAL_OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
