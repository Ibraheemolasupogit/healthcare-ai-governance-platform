"""Typed immutable models for deterministic compliance monitoring.

These are assessment artifacts over the existing synthetic governance state,
not regulatory certifications and not live monitoring records.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.compliance.enums import (
    ComplianceEntityType,
    ControlDomain,
    ControlSeverity,
    ControlStatus,
    FindingCode,
    GovernancePosture,
    RiskCategory,
)


class ControlDefinition(BaseModel):
    """A fixed control that the local evaluator knows how to run."""

    model_config = {"frozen": True, "extra": "forbid"}

    control_id: str = Field(pattern=r"^CTRL-\d{4}$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    control_domain: ControlDomain
    severity: ControlSeverity
    applies_to: tuple[ComplianceEntityType, ...]
    evidence_requirements: tuple[str, ...]
    enabled: bool = True


class ControlResult(BaseModel):
    """The deterministic outcome of evaluating one control for one entity or scope."""

    model_config = {"frozen": True, "extra": "forbid"}

    result_id: str = Field(pattern=r"^CR-\d{4}$")
    control_id: str = Field(pattern=r"^CTRL-\d{4}$")
    evaluated_at: datetime
    entity_type: ComplianceEntityType
    entity_id: str = Field(min_length=1)
    status: ControlStatus
    severity: ControlSeverity
    finding_code: FindingCode
    message: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _passing_results_use_pass_code(self) -> ControlResult:
        if self.status == ControlStatus.PASS and self.finding_code != FindingCode.CONTROL_PASSED:
            raise ValueError("passing control results must use finding_code=control_passed")
        if self.status != ControlStatus.PASS and self.finding_code == FindingCode.CONTROL_PASSED:
            raise ValueError("non-passing control results need a specific finding_code")
        return self


class RiskIndicator(BaseModel):
    """An explainable bounded risk indicator derived from non-passing control results."""

    model_config = {"frozen": True, "extra": "forbid"}

    indicator_id: str = Field(pattern=r"^RI-\d{4}$")
    entity_type: ComplianceEntityType
    entity_id: str = Field(min_length=1)
    category: RiskCategory
    severity: ControlSeverity
    score: int = Field(ge=1, le=8)
    rationale: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    evaluated_at: datetime


class ComplianceSummary(BaseModel):
    """Reviewer-facing aggregate metrics for a compliance assessment."""

    model_config = {"frozen": True, "extra": "forbid"}

    total_controls_evaluated: int
    passed_controls: int
    warning_controls: int
    failed_controls: int
    pass_rate: float
    findings_by_severity: dict[str, int]
    findings_by_domain: dict[str, int]
    number_of_risk_indicators: int
    total_bounded_risk_score: int
    overall_posture: GovernancePosture

    @field_validator("pass_rate")
    @classmethod
    def _pass_rate_is_bounded(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("pass_rate must be between 0 and 1")
        return value


class ComplianceAssessment(BaseModel):
    """A reproducible risk/compliance assessment over Milestones 2-4 state."""

    model_config = {"frozen": True, "extra": "forbid"}

    assessment_id: str = Field(pattern=r"^CA-\d{4}$")
    evaluated_at: datetime
    scope: str = Field(min_length=1)
    control_results: tuple[ControlResult, ...]
    risk_indicators: tuple[RiskIndicator, ...]
    posture: GovernancePosture
    summary: ComplianceSummary
    limitations: tuple[str, ...]
