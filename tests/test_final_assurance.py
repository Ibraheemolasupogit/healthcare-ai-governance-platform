from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.reviewer.final_assurance import (
    PortfolioAssuranceSummary,
    export_portfolio_assurance_summary,
    load_portfolio_assurance_summary,
    render_portfolio_assurance_summary,
)


def _summary() -> PortfolioAssuranceSummary:
    return PortfolioAssuranceSummary(
        summary_id="PAS-0001",
        generated_at=datetime(2025, 3, 24),
        repository_name="fixture",
        pipeline_steps=("inventory", "archive_verification"),
        pipeline_status="passed",
        lint_status="passed",
        format_status="passed",
        tests_status="passed",
        repository_validation_status="passed",
        reviewer_smoke_status="passed",
        review_readiness_status="ready_for_review",
        governance_posture="attention_required",
        bounded_risk_score=3,
        archive_validation_status="passed",
        key_artifact_refs=("outputs/archive/archive_manifest.json",),
        limitations=("local synthetic fixture",),
        synthetic_data_only=True,
        local_only=True,
        non_production=True,
    )


def test_final_summary_requires_claim_boundaries_and_is_immutable() -> None:
    summary = _summary()
    assert summary.archive_validation_status == "passed"
    with pytest.raises(ValidationError):
        summary.pipeline_status = "failed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        PortfolioAssuranceSummary(**{**summary.model_dump(), "synthetic_data_only": False})


def test_final_summary_export_round_trips_deterministically(tmp_path) -> None:
    summary = _summary()
    export_portfolio_assurance_summary(summary, tmp_path)
    first = (tmp_path / "portfolio_assurance_summary.json").read_bytes()
    export_portfolio_assurance_summary(summary, tmp_path)

    assert (tmp_path / "portfolio_assurance_summary.json").read_bytes() == first
    assert load_portfolio_assurance_summary(tmp_path) == summary
    assert "ready_for_review" in render_portfolio_assurance_summary(summary)


def test_final_summary_requires_canonical_outputs(tmp_path) -> None:
    from governance_platform.reviewer.final_assurance import build_portfolio_assurance_summary

    with pytest.raises(FileNotFoundError):
        build_portfolio_assurance_summary(tmp_path)
