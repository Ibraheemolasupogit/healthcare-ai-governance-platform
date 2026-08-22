"""Typed immutable reporting models for governance KPI snapshots."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from governance_platform.compliance import GovernancePosture
from governance_platform.reporting.enums import MetricUnit, ReportingMetricDomain

MetricValue = int | float | str | bool


class GovernanceKPI(BaseModel):
    """One reporting-ready metric with traceable source references."""

    model_config = {"frozen": True, "extra": "forbid"}

    metric_id: str = Field(pattern=r"^KPI-\d{4}$")
    metric_name: str = Field(min_length=1)
    metric_domain: ReportingMetricDomain
    value: MetricValue
    unit: MetricUnit
    as_of: datetime
    source_refs: tuple[str, ...]
    description: str = Field(min_length=1)

    @field_validator("source_refs")
    @classmethod
    def _source_refs_are_present(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("source_refs must contain at least one reference")
        return value


class ReportingSnapshot(BaseModel):
    """A deterministic reporting semantic snapshot over existing governance outputs."""

    model_config = {"frozen": True, "extra": "forbid"}

    snapshot_id: str = Field(pattern=r"^RS-\d{4}$")
    generated_at: datetime
    inventory_metrics: tuple[GovernanceKPI, ...]
    access_metrics: tuple[GovernanceKPI, ...]
    audit_metrics: tuple[GovernanceKPI, ...]
    compliance_metrics: tuple[GovernanceKPI, ...]
    risk_metrics: tuple[GovernanceKPI, ...]
    posture: GovernancePosture
    limitations: tuple[str, ...]

    @property
    def all_metrics(self) -> tuple[GovernanceKPI, ...]:
        """All KPI rows in deterministic semantic-layer order."""
        return (
            *self.inventory_metrics,
            *self.access_metrics,
            *self.audit_metrics,
            *self.compliance_metrics,
            *self.risk_metrics,
        )
