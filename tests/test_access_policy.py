from datetime import date, datetime

from governance_platform.access import RejectionReasonCode, RequesterRole
from governance_platform.access.entities import AccessRequest
from governance_platform.access.policy import evaluate_eligibility
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
    responsible_ai_review_status=ResponsibleAIReviewStatus.NOT_REQUIRED,
    monitoring_required=False,
    created_at=date(2024, 1, 1),
)

_PROJECT_KWARGS = dict(
    title="Test Project",
    principal_owner="Test Principal Investigator",
    purpose="Used only in tests.",
    risk_classification=RiskTier.LOW,
    start_date=date(2024, 1, 1),
    workspace_status=WorkspaceStatus.ACTIVE,
)


def _dataset(dataset_id: str, **overrides: object) -> Dataset:
    fields = dict(
        _DATASET_KWARGS,
        dataset_id=dataset_id,
        approval_status=ApprovalStatus.APPROVED,
        research_use_allowed=True,
    )
    fields.update(overrides)
    return Dataset(**fields)


def _model(model_id: str, linked_dataset_ids: tuple[str, ...] = (), **overrides: object) -> AIModel:
    fields = dict(
        _MODEL_KWARGS,
        model_id=model_id,
        linked_dataset_ids=linked_dataset_ids,
        approval_status=ApprovalStatus.APPROVED,
        risk_tier=RiskTier.LOW,
    )
    fields.update(overrides)
    return AIModel(**fields)


def _project(
    research_project_id: str,
    linked_dataset_ids: tuple[str, ...] = (),
    linked_model_ids: tuple[str, ...] = (),
    **overrides: object,
) -> ResearchProject:
    fields = dict(
        _PROJECT_KWARGS,
        research_project_id=research_project_id,
        linked_dataset_ids=linked_dataset_ids,
        linked_model_ids=linked_model_ids,
        approval_status=ApprovalStatus.APPROVED,
        expiry_date=date(2025, 1, 1),
    )
    fields.update(overrides)
    return ResearchProject(**fields)


def _request(**overrides: object) -> AccessRequest:
    fields: dict[str, object] = dict(
        request_id="AR-0001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        requested_dataset_ids=("DS-0001",),
        requested_model_ids=(),
        purpose="Used only in tests.",
        requested_at=datetime(2024, 6, 1),
        requested_until=datetime(2024, 9, 1),
    )
    fields.update(overrides)
    return AccessRequest(**fields)


def test_eligible_request_has_no_violations() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0001",)),),
    )
    result = evaluate_eligibility(_request(), inventory)

    assert result.eligible is True
    assert result.violations == ()


def test_unknown_research_project_is_reported() -> None:
    inventory = InventoryPortfolio(datasets=(_dataset("DS-0001"),))
    result = evaluate_eligibility(_request(research_project_id="RP-9999"), inventory)

    assert result.eligible is False
    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.UNKNOWN_RESEARCH_PROJECT in codes


def test_pending_project_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(
            _project(
                "RP-0001", linked_dataset_ids=("DS-0001",), approval_status=ApprovalStatus.PENDING
            ),
        ),
    )
    result = evaluate_eligibility(_request(), inventory)

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.RESEARCH_PROJECT_NOT_APPROVED in codes
    assert RejectionReasonCode.RESEARCH_PROJECT_EXPIRED not in codes


def test_expired_project_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(
            _project(
                "RP-0001", linked_dataset_ids=("DS-0001",), approval_status=ApprovalStatus.EXPIRED
            ),
        ),
    )
    result = evaluate_eligibility(_request(), inventory)

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.RESEARCH_PROJECT_EXPIRED in codes
    assert RejectionReasonCode.RESEARCH_PROJECT_NOT_APPROVED not in codes


def test_unknown_dataset_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0001",)),),
    )
    result = evaluate_eligibility(_request(requested_dataset_ids=("DS-9999",)), inventory)

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.UNKNOWN_DATASET in codes


def test_unknown_model_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0001",)),),
    )
    result = evaluate_eligibility(
        _request(requested_dataset_ids=(), requested_model_ids=("MD-9999",)), inventory
    )

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.UNKNOWN_MODEL in codes


def test_dataset_not_linked_to_project_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"), _dataset("DS-0002")),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0002",)),),
    )
    result = evaluate_eligibility(_request(requested_dataset_ids=("DS-0001",)), inventory)

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.DATASET_NOT_LINKED_TO_PROJECT in codes


def test_model_not_linked_to_project_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        models=(_model("MD-0001"),),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0001",)),),
    )
    result = evaluate_eligibility(
        _request(requested_dataset_ids=(), requested_model_ids=("MD-0001",)), inventory
    )

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.MODEL_NOT_LINKED_TO_PROJECT in codes


def test_research_use_not_allowed_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001", research_use_allowed=False),),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0001",)),),
    )
    result = evaluate_eligibility(_request(), inventory)

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.RESEARCH_USE_NOT_ALLOWED in codes


def test_dataset_not_approved_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001", approval_status=ApprovalStatus.PENDING),),
        research_projects=(_project("RP-0001", linked_dataset_ids=("DS-0001",)),),
    )
    result = evaluate_eligibility(_request(), inventory)

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.DATASET_NOT_APPROVED in codes


def test_model_not_approved_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        models=(
            _model(
                "MD-0001", linked_dataset_ids=("DS-0001",), approval_status=ApprovalStatus.PENDING
            ),
        ),
        research_projects=(
            _project("RP-0001", linked_dataset_ids=("DS-0001",), linked_model_ids=("MD-0001",)),
        ),
    )
    result = evaluate_eligibility(
        _request(requested_dataset_ids=(), requested_model_ids=("MD-0001",)), inventory
    )

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.MODEL_NOT_APPROVED in codes


def test_requested_duration_exceeding_project_expiry_is_reported() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(
            _project("RP-0001", linked_dataset_ids=("DS-0001",), expiry_date=date(2024, 7, 1)),
        ),
    )
    result = evaluate_eligibility(
        _request(requested_at=datetime(2024, 6, 1), requested_until=datetime(2024, 8, 1)),
        inventory,
    )

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.REQUESTED_DURATION_EXCEEDS_PROJECT_EXPIRY in codes


def test_requested_duration_within_project_expiry_passes() -> None:
    inventory = InventoryPortfolio(
        datasets=(_dataset("DS-0001"),),
        research_projects=(
            _project("RP-0001", linked_dataset_ids=("DS-0001",), expiry_date=date(2024, 12, 1)),
        ),
    )
    result = evaluate_eligibility(
        _request(requested_at=datetime(2024, 6, 1), requested_until=datetime(2024, 8, 1)),
        inventory,
    )

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.REQUESTED_DURATION_EXCEEDS_PROJECT_EXPIRY not in codes


def test_multiple_violations_are_all_reported() -> None:
    inventory = InventoryPortfolio()
    result = evaluate_eligibility(
        _request(requested_dataset_ids=("DS-9999",), requested_model_ids=("MD-9999",)), inventory
    )

    codes = {v.code for v in result.violations}
    assert RejectionReasonCode.UNKNOWN_RESEARCH_PROJECT in codes
    assert RejectionReasonCode.UNKNOWN_DATASET in codes
    assert RejectionReasonCode.UNKNOWN_MODEL in codes
    assert result.eligible is False
