from datetime import date

import pytest
from pydantic import ValidationError

from governance_platform.inventory import (
    AIModel,
    ApprovalStatus,
    DataCategory,
    Dataset,
    InventoryPortfolio,
    LifecycleStatus,
    ModelType,
    ResearchProject,
    ResponsibleAIReviewStatus,
    RetentionClass,
    RiskTier,
    SensitivityClassification,
    SourceType,
    WorkspaceStatus,
)

_DATASET_KWARGS = dict(
    name="Test Dataset",
    description="A dataset used only in tests.",
    domain="Testing",
    owner="Test Data Owner",
    steward="Test Governance Steward",
    sensitivity_classification=SensitivityClassification.INTERNAL,
    data_category=DataCategory.OPERATIONAL,
    source_type=SourceType.SYNTHETIC_GENERATED,
    lifecycle_status=LifecycleStatus.ACTIVE,
    approval_status=ApprovalStatus.APPROVED,
    research_use_allowed=True,
    retention_class=RetentionClass.STANDARD,
    contains_synthetic_data_only=True,
    created_at=date(2024, 1, 1),
)

_MODEL_KWARGS = dict(
    name="Test Model",
    version="1.0.0",
    model_type=ModelType.MACHINE_LEARNING,
    intended_use="Used only in tests.",
    owner="Test Model Owner",
    lifecycle_status=LifecycleStatus.ACTIVE,
    approval_status=ApprovalStatus.APPROVED,
    risk_tier=RiskTier.LOW,
    responsible_ai_review_status=ResponsibleAIReviewStatus.NOT_REQUIRED,
    monitoring_required=False,
    created_at=date(2024, 1, 1),
)

_PROJECT_KWARGS = dict(
    title="Test Project",
    principal_owner="Test Principal Investigator",
    purpose="Used only in tests.",
    approval_status=ApprovalStatus.APPROVED,
    risk_classification=RiskTier.LOW,
    start_date=date(2024, 1, 1),
    expiry_date=date(2025, 1, 1),
    workspace_status=WorkspaceStatus.ACTIVE,
)


def _dataset(dataset_id: str) -> Dataset:
    return Dataset(dataset_id=dataset_id, **_DATASET_KWARGS)


def _model(model_id: str, linked_dataset_ids: tuple[str, ...]) -> AIModel:
    return AIModel(model_id=model_id, linked_dataset_ids=linked_dataset_ids, **_MODEL_KWARGS)


def _project(
    research_project_id: str,
    linked_dataset_ids: tuple[str, ...],
    linked_model_ids: tuple[str, ...],
) -> ResearchProject:
    return ResearchProject(
        research_project_id=research_project_id,
        linked_dataset_ids=linked_dataset_ids,
        linked_model_ids=linked_model_ids,
        **_PROJECT_KWARGS,
    )


def test_valid_portfolio_constructs() -> None:
    portfolio = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        models=(_model("MD-0001", ("DS-0001",)),),
        research_projects=(_project("RP-0001", ("DS-0001",), ("MD-0001",)),),
    )
    assert portfolio.dataset_by_id("DS-0001").dataset_id == "DS-0001"
    assert portfolio.model_by_id("MD-0001").model_id == "MD-0001"
    assert portfolio.research_project_by_id("RP-0001").research_project_id == "RP-0001"


def test_rejects_duplicate_dataset_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate dataset_id"):
        InventoryPortfolio(datasets=(_dataset("DS-0001"), _dataset("DS-0001")))


def test_rejects_duplicate_model_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate model_id"):
        InventoryPortfolio(
            datasets=(_dataset("DS-0001"),),
            models=(
                _model("MD-0001", ("DS-0001",)),
                _model("MD-0001", ("DS-0001",)),
            ),
        )


def test_rejects_duplicate_research_project_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate research_project_id"):
        InventoryPortfolio(
            datasets=(_dataset("DS-0001"),),
            research_projects=(
                _project("RP-0001", ("DS-0001",), ()),
                _project("RP-0001", ("DS-0001",), ()),
            ),
        )


def test_rejects_model_referencing_unknown_dataset() -> None:
    with pytest.raises(ValidationError, match="unknown dataset_id"):
        InventoryPortfolio(
            datasets=(_dataset("DS-0001"),),
            models=(_model("MD-0001", ("DS-9999",)),),
        )


def test_rejects_research_project_referencing_unknown_dataset() -> None:
    with pytest.raises(ValidationError, match="unknown dataset_id"):
        InventoryPortfolio(
            datasets=(_dataset("DS-0001"),),
            research_projects=(_project("RP-0001", ("DS-9999",), ()),),
        )


def test_rejects_research_project_referencing_unknown_model() -> None:
    with pytest.raises(ValidationError, match="unknown model_id"):
        InventoryPortfolio(
            datasets=(_dataset("DS-0001"),),
            models=(_model("MD-0001", ("DS-0001",)),),
            research_projects=(_project("RP-0001", ("DS-0001",), ("MD-9999",)),),
        )


def test_dataset_by_id_raises_for_unknown_id() -> None:
    portfolio = InventoryPortfolio(datasets=(_dataset("DS-0001"),))
    with pytest.raises(KeyError):
        portfolio.dataset_by_id("DS-9999")
