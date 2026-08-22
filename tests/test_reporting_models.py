from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.reporting import (
    GovernanceKPI,
    MetricUnit,
    ReportingMetricDomain,
    ReportingSnapshot,
)


def test_governance_kpi_is_frozen_and_forbids_extra_fields() -> None:
    metric = GovernanceKPI(
        metric_id="KPI-0001",
        metric_name="test_metric",
        metric_domain=ReportingMetricDomain.INVENTORY_POSTURE,
        value=1,
        unit=MetricUnit.COUNT,
        as_of=datetime(2025, 3, 15),
        source_refs=("inventory_portfolio",),
        description="Used only in tests.",
    )

    with pytest.raises(ValidationError):
        GovernanceKPI.model_validate({**metric.model_dump(mode="json"), "extra": "nope"})
    with pytest.raises(ValidationError):
        metric.metric_name = "changed"  # type: ignore[misc]


def test_governance_kpi_requires_source_references() -> None:
    with pytest.raises(ValidationError):
        GovernanceKPI(
            metric_id="KPI-0001",
            metric_name="test_metric",
            metric_domain=ReportingMetricDomain.INVENTORY_POSTURE,
            value=1,
            unit=MetricUnit.COUNT,
            as_of=datetime(2025, 3, 15),
            source_refs=(),
            description="Used only in tests.",
        )


def test_reporting_snapshot_forbids_extra_fields() -> None:
    raw = {
        "snapshot_id": "RS-0001",
        "generated_at": "2025-03-21T00:00:00",
        "inventory_metrics": [],
        "access_metrics": [],
        "audit_metrics": [],
        "compliance_metrics": [],
        "risk_metrics": [],
        "posture": "healthy",
        "limitations": [],
        "extra": "nope",
    }

    with pytest.raises(ValidationError):
        ReportingSnapshot.model_validate(raw)
