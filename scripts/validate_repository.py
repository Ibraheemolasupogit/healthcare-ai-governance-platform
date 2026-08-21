#!/usr/bin/env python3
"""Validate that the repository's Milestone 1 foundation structure is intact.

Run directly (``python scripts/validate_repository.py``) or imported from
tests via ``validate()``. Checks presence of required directories/files and a
few structural invariants (e.g. the architecture report contains a Mermaid
diagram, ADRs exist). This does not validate governance logic — there is
none yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DIRS = [
    "data",
    "src/governance_platform",
    "governance",
    "infrastructure/docker",
    "infrastructure/terraform",
    "infrastructure/snowflake",
    "fabric/semantic_model",
    "fabric/dashboards",
    "config",
    "outputs",
    "reports",
    "docs/architecture/decisions",
    "tests",
    ".github/workflows",
]

REQUIRED_FILES = [
    "README.md",
    "pyproject.toml",
    ".gitignore",
    "reports/architecture.md",
    "src/governance_platform/__init__.py",
    "infrastructure/docker/Dockerfile",
    "infrastructure/docker/docker-compose.yml",
    "infrastructure/terraform/main.tf",
    "infrastructure/terraform/variables.tf",
    "infrastructure/snowflake/README.md",
    "fabric/semantic_model/README.md",
    "fabric/dashboards/README.md",
    ".github/workflows/ci.yml",
]

REQUIRED_GOVERNANCE_DOCS = [
    "dataset_governance.md",
    "model_governance.md",
    "research_approval.md",
    "access_review.md",
    "audit_evidence.md",
    "responsible_ai.md",
    "compliance_monitoring.md",
]

MIN_ADR_COUNT = 5


def validate() -> list[str]:
    """Return a list of problems found; an empty list means the check passed."""
    problems: list[str] = []

    for rel_dir in REQUIRED_DIRS:
        if not (REPO_ROOT / rel_dir).is_dir():
            problems.append(f"missing required directory: {rel_dir}")

    for rel_file in REQUIRED_FILES:
        if not (REPO_ROOT / rel_file).is_file():
            problems.append(f"missing required file: {rel_file}")

    governance_dir = REPO_ROOT / "governance"
    for doc in REQUIRED_GOVERNANCE_DOCS:
        if not (governance_dir / doc).is_file():
            problems.append(f"missing governance operating-model doc: governance/{doc}")

    adr_dir = REPO_ROOT / "docs/architecture/decisions"
    adr_files = sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")) if adr_dir.is_dir() else []
    if len(adr_files) < MIN_ADR_COUNT:
        problems.append(
            f"expected at least {MIN_ADR_COUNT} ADR files in docs/architecture/decisions/, "
            f"found {len(adr_files)}"
        )

    architecture_report = REPO_ROOT / "reports/architecture.md"
    if architecture_report.is_file():
        content = architecture_report.read_text()
        if "```mermaid" not in content:
            problems.append("reports/architecture.md does not contain a ```mermaid diagram")

    readme = REPO_ROOT / "README.md"
    if readme.is_file():
        content = readme.read_text()
        if "Implemented" not in content or "Planned" not in content:
            problems.append("README.md must clearly separate Implemented and Planned capabilities")

    return problems


def main() -> int:
    problems = validate()
    if problems:
        print("Repository validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
