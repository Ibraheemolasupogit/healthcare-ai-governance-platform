"""Final deterministic portfolio assurance summary.

Milestone 14 aggregates already-generated validation state. It does not add
governance evaluation, external attestation, deployment, or approval records.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.compliance import load_compliance_assessment
from governance_platform.reviewer.archive import load_archive_validation
from governance_platform.reviewer.readiness import load_acceptance_checklist

FINAL_ASSURANCE_JSON_FILENAME = "portfolio_assurance_summary.json"
FINAL_ASSURANCE_MARKDOWN_FILENAME = "portfolio_assurance_summary.md"
FINAL_ASSURANCE_OUTPUT_FILENAMES: tuple[str, ...] = (
    FINAL_ASSURANCE_JSON_FILENAME,
    FINAL_ASSURANCE_MARKDOWN_FILENAME,
)
_GENERATED_AT = datetime(2025, 3, 24, 0, 0, 0)
_LIMITATIONS: tuple[str, ...] = (
    "This summary covers a local repository with deterministic synthetic governance outputs.",
    "Passing checks do not establish production readiness, authenticity, certification, "
    "or human approval.",
    "The Streamlit smoke result may report an explicit environment fallback when local "
    "port binding is restricted.",
)


class PortfolioAssuranceSummary(BaseModel):
    """Canonical final release-assurance summary for the portfolio repository."""

    model_config = {"frozen": True, "extra": "forbid"}

    summary_id: str = Field(pattern=r"^PAS-\d{4}$")
    generated_at: datetime
    repository_name: str = Field(min_length=1)
    pipeline_steps: tuple[str, ...]
    pipeline_status: str = Field(min_length=1)
    lint_status: str = Field(min_length=1)
    format_status: str = Field(min_length=1)
    tests_status: str = Field(min_length=1)
    repository_validation_status: str = Field(min_length=1)
    reviewer_smoke_status: str = Field(min_length=1)
    review_readiness_status: str = Field(min_length=1)
    governance_posture: str = Field(min_length=1)
    bounded_risk_score: int = Field(ge=0, le=100)
    archive_validation_status: str = Field(min_length=1)
    key_artifact_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    synthetic_data_only: bool
    local_only: bool
    non_production: bool

    @field_validator("pipeline_steps", "key_artifact_refs", "limitations")
    @classmethod
    def _non_empty_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("summary tuple fields must not be empty")
        return value

    @model_validator(mode="after")
    def _claim_boundaries_are_explicit(self) -> PortfolioAssuranceSummary:
        if not self.synthetic_data_only or not self.local_only or not self.non_production:
            raise ValueError("final assurance summary must preserve local synthetic boundaries")
        return self


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_portfolio_assurance_summary(
    outputs_root: str | Path,
    *,
    pipeline_status: str = "passed",
    lint_status: str = "passed",
    format_status: str = "passed",
    tests_status: str = "passed",
    repository_validation_status: str = "passed",
    reviewer_smoke_status: str = "passed",
) -> PortfolioAssuranceSummary:
    """Aggregate canonical readiness, compliance, and archive validation outputs."""
    root = Path(outputs_root)
    readiness = load_acceptance_checklist(root / "readiness")
    compliance = load_compliance_assessment(root / "compliance")
    archive = load_archive_validation(root / "archive")
    return PortfolioAssuranceSummary(
        summary_id="PAS-0001",
        generated_at=_GENERATED_AT,
        repository_name="healthcare-ai-governance-platform",
        pipeline_steps=(
            "inventory",
            "access",
            "evidence",
            "compliance",
            "reporting",
            "reviewer_bundle",
            "policy_catalog",
            "assurance_history",
            "assurance_pack",
            "review_readiness",
            "offline_archive",
            "archive_verification",
        ),
        pipeline_status=pipeline_status,
        lint_status=lint_status,
        format_status=format_status,
        tests_status=tests_status,
        repository_validation_status=repository_validation_status,
        reviewer_smoke_status=reviewer_smoke_status,
        review_readiness_status=readiness.readiness_status.value,
        governance_posture=compliance.posture.value,
        bounded_risk_score=compliance.summary.total_bounded_risk_score,
        archive_validation_status=archive.status.value,
        key_artifact_refs=(
            "outputs/reviewer/reviewer_briefing.md",
            "outputs/assurance_pack/assurance_review_pack.md",
            "outputs/readiness/review_readiness_report.md",
            "outputs/archive/archive_manifest.json",
            "outputs/archive/offline_handoff_guide.md",
        ),
        limitations=_LIMITATIONS,
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def render_portfolio_assurance_summary(summary: PortfolioAssuranceSummary) -> str:
    """Render a concise reviewer-readable final assurance summary."""
    return (
        f"""# Portfolio Assurance Summary

## Scope

Summary `{summary.summary_id}` covers the local
`healthcare-ai-governance-platform` repository and its deterministic synthetic
governance outputs.

## Assurance Status

- Pipeline: `{summary.pipeline_status}`
- Review readiness: `{summary.review_readiness_status}`
- Governance posture: `{summary.governance_posture}`
- Bounded risk score: `{summary.bounded_risk_score}`
- Archive verification: `{summary.archive_validation_status}`
- Reviewer smoke: `{summary.reviewer_smoke_status}`

## Quality Gates

- Ruff lint: `{summary.lint_status}`
- Ruff format: `{summary.format_status}`
- Tests: `{summary.tests_status}`
- Repository validation: `{summary.repository_validation_status}`

## Key Artifacts

"""
        + "\n".join(f"- `{ref}`" for ref in summary.key_artifact_refs)
        + f"""

## Pipeline

`{" -> ".join(summary.pipeline_steps)}`

## Boundaries

This repository is local, read-only, synthetic-data-only, and non-production. Passing checks do not
establish authenticity, production readiness, regulatory certification, external attestation,
human governance approval, or deployment. Future Snowflake, Fabric, Power BI, identity, monitoring,
and hosting integrations remain planned.

## Limitations

"""
        + "\n".join(f"- {limitation}" for limitation in summary.limitations)
        + "\n"
    )


def export_portfolio_assurance_summary(
    summary: PortfolioAssuranceSummary, output_dir: str | Path
) -> None:
    """Export canonical JSON and reviewer-readable Markdown."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / FINAL_ASSURANCE_JSON_FILENAME).write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    (destination / FINAL_ASSURANCE_MARKDOWN_FILENAME).write_text(
        render_portfolio_assurance_summary(summary), encoding="utf-8"
    )


def load_portfolio_assurance_summary(path_or_dir: str | Path) -> PortfolioAssuranceSummary:
    """Load the canonical final assurance summary."""
    path = Path(path_or_dir)
    path = path / FINAL_ASSURANCE_JSON_FILENAME if path.is_dir() else path
    return PortfolioAssuranceSummary.model_validate_json(path.read_text(encoding="utf-8"))


__all__ = [
    "FINAL_ASSURANCE_OUTPUT_FILENAMES",
    "PortfolioAssuranceSummary",
    "build_portfolio_assurance_summary",
    "export_portfolio_assurance_summary",
    "load_portfolio_assurance_summary",
    "render_portfolio_assurance_summary",
]
