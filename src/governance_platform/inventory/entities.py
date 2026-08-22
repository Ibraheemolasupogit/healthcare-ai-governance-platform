"""Typed inventory entities: datasets, AI/ML models, and research projects.

These are the metadata/inventory plane's system-of-record shapes — what
later access review, audit, risk, compliance, model governance, and
evidence capabilities will join against. Entity-level validation enforces
invariants that hold regardless of what else is in the portfolio (e.g. a
dataset must assert it is synthetic-only); cross-entity referential
integrity (e.g. a model's linked datasets must exist) is enforced by
``governance_platform.inventory.portfolio.InventoryPortfolio``.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from governance_platform.inventory.enums import (
    ApprovalStatus,
    DataCategory,
    LifecycleStatus,
    ModelType,
    ResponsibleAIReviewStatus,
    RetentionClass,
    RiskTier,
    SensitivityClassification,
    SourceType,
    WorkspaceStatus,
)

_DATASET_ID_PATTERN = re.compile(r"^DS-\d{4}$")
_MODEL_ID_PATTERN = re.compile(r"^MD-\d{4}$")
_RESEARCH_PROJECT_ID_PATTERN = re.compile(r"^RP-\d{4}$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class Dataset(BaseModel):
    """A dataset registered in the inventory, per ``governance/dataset_governance.md``."""

    model_config = {"frozen": True, "extra": "forbid"}

    dataset_id: str = Field(pattern=_DATASET_ID_PATTERN.pattern)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    steward: str = Field(min_length=1)
    sensitivity_classification: SensitivityClassification
    data_category: DataCategory
    source_type: SourceType
    lifecycle_status: LifecycleStatus
    approval_status: ApprovalStatus
    research_use_allowed: bool
    retention_class: RetentionClass
    contains_synthetic_data_only: bool
    created_at: date
    reviewed_at: date | None = None

    @field_validator("contains_synthetic_data_only")
    @classmethod
    def _must_be_synthetic_only(cls, value: bool) -> bool:
        # ADR 0001: every dataset in this platform is synthetic, with no exceptions.
        if not value:
            raise ValueError(
                "contains_synthetic_data_only must be True — this platform holds no "
                "real patient, clinician, or institutional data (see ADR 0001)"
            )
        return value

    @model_validator(mode="after")
    def _reviewed_at_not_before_created_at(self) -> Dataset:
        if self.reviewed_at is not None and self.reviewed_at < self.created_at:
            raise ValueError(
                f"dataset {self.dataset_id}: reviewed_at ({self.reviewed_at}) "
                f"is before created_at ({self.created_at})"
            )
        return self


class AIModel(BaseModel):
    """An AI/ML model registered in the inventory, per ``governance/model_governance.md``.

    No training, deployment, inference, or monitoring is implemented here — this is
    metadata about a model, not the model itself.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    model_id: str = Field(pattern=_MODEL_ID_PATTERN.pattern)
    name: str = Field(min_length=1)
    version: str = Field(pattern=_VERSION_PATTERN.pattern)
    model_type: ModelType
    intended_use: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    linked_dataset_ids: tuple[str, ...] = Field(default_factory=tuple)
    lifecycle_status: LifecycleStatus
    approval_status: ApprovalStatus
    risk_tier: RiskTier
    responsible_ai_review_status: ResponsibleAIReviewStatus
    monitoring_required: bool
    created_at: date
    reviewed_at: date | None = None

    @model_validator(mode="after")
    def _reviewed_at_not_before_created_at(self) -> AIModel:
        if self.reviewed_at is not None and self.reviewed_at < self.created_at:
            raise ValueError(
                f"model {self.model_id}: reviewed_at ({self.reviewed_at}) "
                f"is before created_at ({self.created_at})"
            )
        return self

    @model_validator(mode="after")
    def _high_risk_requires_review_and_monitoring(self) -> AIModel:
        # governance/model_governance.md: higher risk-tier models require a recorded
        # responsible AI review before moving to "approved".
        if (
            self.risk_tier == RiskTier.HIGH
            and self.approval_status == ApprovalStatus.APPROVED
            and self.responsible_ai_review_status != ResponsibleAIReviewStatus.APPROVED
        ):
            raise ValueError(
                f"model {self.model_id}: high risk_tier models cannot be approved "
                f"without an approved responsible_ai_review_status "
                f"(got {self.responsible_ai_review_status.value})"
            )
        if self.risk_tier == RiskTier.HIGH and not self.monitoring_required:
            raise ValueError(
                f"model {self.model_id}: high risk_tier models must have "
                f"monitoring_required=True"
            )
        return self


class ResearchProject(BaseModel):
    """A research project registered in the inventory, per ``governance/research_approval.md``.

    No workspace provisioning or approval-workflow automation is implemented here —
    this is metadata about a project's declared state, not a live workflow.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    research_project_id: str = Field(pattern=_RESEARCH_PROJECT_ID_PATTERN.pattern)
    title: str = Field(min_length=1)
    principal_owner: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    linked_dataset_ids: tuple[str, ...] = Field(default_factory=tuple)
    linked_model_ids: tuple[str, ...] = Field(default_factory=tuple)
    approval_status: ApprovalStatus
    risk_classification: RiskTier
    start_date: date
    expiry_date: date
    workspace_status: WorkspaceStatus

    @model_validator(mode="after")
    def _expiry_after_start(self) -> ResearchProject:
        if self.expiry_date <= self.start_date:
            raise ValueError(
                f"research project {self.research_project_id}: expiry_date "
                f"({self.expiry_date}) must be after start_date ({self.start_date})"
            )
        return self
