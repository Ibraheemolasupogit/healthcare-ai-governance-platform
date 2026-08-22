"""Aggregate governance summary computed from an inventory portfolio.

Deliberately limited to counts and breakdowns — no calculated enterprise risk
score is produced here; that is explicitly out of scope until the risk/
compliance plane is implemented (see ``governance/compliance_monitoring.md``).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel

from governance_platform.inventory.enums import (
    ApprovalStatus,
    LifecycleStatus,
    RiskTier,
    SensitivityClassification,
    WorkspaceStatus,
)
from governance_platform.inventory.portfolio import InventoryPortfolio

_E = TypeVar("_E", bound=Enum)


def _counts_by_enum(enum_cls: type[_E], values: Iterable[_E]) -> dict[str, int]:
    """Count occurrences of each ``enum_cls`` member, in enum definition order.

    Every member appears in the result (with a count of 0 if unused) so the
    summary is a complete, stable-shaped breakdown rather than only listing
    whichever statuses happen to occur in the current portfolio.
    """
    tally = Counter(values)
    return {member.value: tally.get(member, 0) for member in enum_cls}


class EntityCounts(BaseModel):
    """Number of registered entities of each kind."""

    datasets: int
    models: int
    research_projects: int


class InventorySummary(BaseModel):
    """Aggregate governance information derived from an :class:`InventoryPortfolio`."""

    model_config = {"frozen": True}

    entity_counts: EntityCounts
    dataset_approval_status: dict[str, int]
    dataset_sensitivity_classification: dict[str, int]
    dataset_lifecycle_status: dict[str, int]
    model_approval_status: dict[str, int]
    model_risk_tier: dict[str, int]
    model_lifecycle_status: dict[str, int]
    research_project_approval_status: dict[str, int]
    research_project_risk_classification: dict[str, int]
    research_project_workspace_status: dict[str, int]
    all_datasets_synthetic_only: bool


def build_summary(portfolio: InventoryPortfolio) -> InventorySummary:
    """Compute the aggregate governance summary for ``portfolio``."""
    return InventorySummary(
        entity_counts=EntityCounts(
            datasets=len(portfolio.datasets),
            models=len(portfolio.models),
            research_projects=len(portfolio.research_projects),
        ),
        dataset_approval_status=_counts_by_enum(
            ApprovalStatus, (d.approval_status for d in portfolio.datasets)
        ),
        dataset_sensitivity_classification=_counts_by_enum(
            SensitivityClassification,
            (d.sensitivity_classification for d in portfolio.datasets),
        ),
        dataset_lifecycle_status=_counts_by_enum(
            LifecycleStatus, (d.lifecycle_status for d in portfolio.datasets)
        ),
        model_approval_status=_counts_by_enum(
            ApprovalStatus, (m.approval_status for m in portfolio.models)
        ),
        model_risk_tier=_counts_by_enum(RiskTier, (m.risk_tier for m in portfolio.models)),
        model_lifecycle_status=_counts_by_enum(
            LifecycleStatus, (m.lifecycle_status for m in portfolio.models)
        ),
        research_project_approval_status=_counts_by_enum(
            ApprovalStatus, (p.approval_status for p in portfolio.research_projects)
        ),
        research_project_risk_classification=_counts_by_enum(
            RiskTier, (p.risk_classification for p in portfolio.research_projects)
        ),
        research_project_workspace_status=_counts_by_enum(
            WorkspaceStatus, (p.workspace_status for p in portfolio.research_projects)
        ),
        all_datasets_synthetic_only=all(d.contains_synthetic_data_only for d in portfolio.datasets),
    )
