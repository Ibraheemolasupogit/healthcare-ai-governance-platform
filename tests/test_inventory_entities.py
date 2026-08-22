from datetime import date

import pytest
from pydantic import ValidationError

from governance_platform.inventory import (
    AIModel,
    ApprovalStatus,
    DataCategory,
    Dataset,
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


def _dataset(**overrides: object) -> Dataset:
    fields: dict[str, object] = dict(
        dataset_id="DS-0001",
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
        reviewed_at=date(2024, 2, 1),
    )
    fields.update(overrides)
    return Dataset(**fields)


def _model(**overrides: object) -> AIModel:
    fields: dict[str, object] = dict(
        model_id="MD-0001",
        name="Test Model",
        version="1.0.0",
        model_type=ModelType.MACHINE_LEARNING,
        intended_use="Used only in tests.",
        owner="Test Model Owner",
        linked_dataset_ids=("DS-0001",),
        lifecycle_status=LifecycleStatus.ACTIVE,
        approval_status=ApprovalStatus.APPROVED,
        risk_tier=RiskTier.LOW,
        responsible_ai_review_status=ResponsibleAIReviewStatus.NOT_REQUIRED,
        monitoring_required=False,
        created_at=date(2024, 1, 1),
        reviewed_at=date(2024, 2, 1),
    )
    fields.update(overrides)
    return AIModel(**fields)


def _research_project(**overrides: object) -> ResearchProject:
    fields: dict[str, object] = dict(
        research_project_id="RP-0001",
        title="Test Project",
        principal_owner="Test Principal Investigator",
        purpose="Used only in tests.",
        linked_dataset_ids=("DS-0001",),
        linked_model_ids=("MD-0001",),
        approval_status=ApprovalStatus.APPROVED,
        risk_classification=RiskTier.LOW,
        start_date=date(2024, 1, 1),
        expiry_date=date(2025, 1, 1),
        workspace_status=WorkspaceStatus.ACTIVE,
    )
    fields.update(overrides)
    return ResearchProject(**fields)


class TestDatasetValidation:
    def test_valid_dataset_constructs(self) -> None:
        dataset = _dataset()
        assert dataset.dataset_id == "DS-0001"
        assert dataset.sensitivity_classification is SensitivityClassification.INTERNAL

    def test_rejects_malformed_dataset_id(self) -> None:
        with pytest.raises(ValidationError):
            _dataset(dataset_id="dataset-1")

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            _dataset(name="")

    def test_rejects_unknown_enum_value(self) -> None:
        with pytest.raises(ValidationError):
            _dataset(sensitivity_classification="top_secret")

    def test_rejects_reviewed_at_before_created_at(self) -> None:
        with pytest.raises(ValidationError, match="reviewed_at"):
            _dataset(created_at=date(2024, 6, 1), reviewed_at=date(2024, 1, 1))

    def test_rejects_non_synthetic_dataset(self) -> None:
        with pytest.raises(ValidationError, match="synthetic"):
            _dataset(contains_synthetic_data_only=False)

    def test_rejects_unknown_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            _dataset(unexpected_field="nope")


class TestAIModelValidation:
    def test_valid_model_constructs(self) -> None:
        model = _model()
        assert model.model_id == "MD-0001"
        assert model.linked_dataset_ids == ("DS-0001",)

    def test_rejects_malformed_model_id(self) -> None:
        with pytest.raises(ValidationError):
            _model(model_id="model-1")

    def test_rejects_non_semver_version(self) -> None:
        with pytest.raises(ValidationError):
            _model(version="v1")

    def test_high_risk_approved_requires_approved_rai_review(self) -> None:
        with pytest.raises(ValidationError, match="responsible_ai_review_status"):
            _model(
                risk_tier=RiskTier.HIGH,
                approval_status=ApprovalStatus.APPROVED,
                responsible_ai_review_status=ResponsibleAIReviewStatus.IN_PROGRESS,
                monitoring_required=True,
            )

    def test_high_risk_pending_does_not_require_approved_rai_review(self) -> None:
        model = _model(
            risk_tier=RiskTier.HIGH,
            approval_status=ApprovalStatus.PENDING,
            responsible_ai_review_status=ResponsibleAIReviewStatus.IN_PROGRESS,
            monitoring_required=True,
        )
        assert model.responsible_ai_review_status is ResponsibleAIReviewStatus.IN_PROGRESS

    def test_high_risk_requires_monitoring(self) -> None:
        with pytest.raises(ValidationError, match="monitoring_required"):
            _model(
                risk_tier=RiskTier.HIGH,
                approval_status=ApprovalStatus.PENDING,
                responsible_ai_review_status=ResponsibleAIReviewStatus.IN_PROGRESS,
                monitoring_required=False,
            )


class TestResearchProjectValidation:
    def test_valid_research_project_constructs(self) -> None:
        project = _research_project()
        assert project.research_project_id == "RP-0001"

    def test_rejects_malformed_research_project_id(self) -> None:
        with pytest.raises(ValidationError):
            _research_project(research_project_id="proj-1")

    def test_rejects_expiry_not_after_start(self) -> None:
        with pytest.raises(ValidationError, match="expiry_date"):
            _research_project(start_date=date(2024, 6, 1), expiry_date=date(2024, 6, 1))

    def test_allows_empty_linked_models(self) -> None:
        project = _research_project(linked_model_ids=())
        assert project.linked_model_ids == ()
