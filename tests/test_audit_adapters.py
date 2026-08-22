from datetime import date, datetime

import pytest

from governance_platform.access import (
    AccessControlService,
    AccessGrant,
    AccessRequest,
    ApprovalDecision,
    DecisionType,
    RequesterRole,
)
from governance_platform.audit import (
    ActorType,
    AuditEventType,
    AuditOutcome,
    request_correlation_id,
)
from governance_platform.audit.adapters import (
    access_decision_event,
    access_evaluated_event,
    access_requested_event,
    grant_created_event,
    grant_expired_event,
    grant_revoked_event,
    inventory_created_event,
    inventory_validated_event,
)
from governance_platform.inventory import (
    ApprovalStatus,
    DataCategory,
    Dataset,
    InventoryPortfolio,
    LifecycleStatus,
    RetentionClass,
    SensitivityClassification,
    SourceType,
)

_REQUEST = AccessRequest(
    request_id="AR-0001",
    requester_id="researcher-test-01",
    requester_role=RequesterRole.RESEARCHER,
    research_project_id="RP-0001",
    requested_dataset_ids=("DS-0001",),
    purpose="Used only in tests.",
    requested_at=datetime(2024, 6, 1),
    requested_until=datetime(2024, 9, 1),
)

_APPROVED_DECISION = ApprovalDecision(
    decision_id="AD-0001",
    request_id="AR-0001",
    approver_id="access-approver-test-01",
    decision=DecisionType.APPROVED,
    decision_reason="All governance eligibility checks passed.",
    decided_at=datetime(2024, 6, 2),
)

_REJECTED_DECISION = ApprovalDecision(
    decision_id="AD-0002",
    request_id="AR-0001",
    approver_id="access-approver-test-01",
    decision=DecisionType.REJECTED,
    decision_reason="dataset DS-9999 does not exist in the inventory",
    decided_at=datetime(2024, 6, 2),
)

_GRANT = AccessGrant(
    grant_id="AG-0001",
    request_id="AR-0001",
    research_project_id="RP-0001",
    requester_id="researcher-test-01",
    dataset_ids=("DS-0001",),
    granted_at=datetime(2024, 6, 3),
    expires_at=datetime(2024, 9, 1),
)


def _inventory() -> InventoryPortfolio:
    dataset = Dataset(
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
    )
    return InventoryPortfolio(datasets=(dataset,))


def test_inventory_created_event_carries_counts() -> None:
    event = inventory_created_event("AE-0001", _inventory(), occurred_at=datetime(2024, 1, 1))
    assert event.event_type is AuditEventType.INVENTORY_CREATED
    assert event.metadata["dataset_count"] == "1"
    assert event.request_id is None


def test_inventory_validated_event() -> None:
    event = inventory_validated_event("AE-0002", occurred_at=datetime(2024, 1, 1))
    assert event.event_type is AuditEventType.INVENTORY_VALIDATED
    assert event.actor_type is ActorType.SYSTEM


def test_access_requested_event_reflects_request() -> None:
    event = access_requested_event("AE-0003", _REQUEST)
    assert event.actor_id == "researcher-test-01"
    assert event.request_id == "AR-0001"
    assert event.correlation_id == request_correlation_id("AR-0001")
    assert event.occurred_at == _REQUEST.requested_at


def test_access_evaluated_event_outcome_matches_decision() -> None:
    approved = access_evaluated_event("AE-0004", _REQUEST, _APPROVED_DECISION)
    rejected = access_evaluated_event("AE-0004", _REQUEST, _REJECTED_DECISION)

    assert approved.outcome is AuditOutcome.SUCCESS
    assert approved.reason is None
    assert rejected.outcome is AuditOutcome.DENIED
    assert rejected.reason == _REJECTED_DECISION.decision_reason


def test_access_decision_event_approved_vs_rejected() -> None:
    approved = access_decision_event("AE-0005", _REQUEST, _APPROVED_DECISION)
    rejected = access_decision_event("AE-0005", _REQUEST, _REJECTED_DECISION)

    assert approved.event_type is AuditEventType.ACCESS_APPROVED
    assert approved.decision_id == "AD-0001"
    assert rejected.event_type is AuditEventType.ACCESS_REJECTED
    assert rejected.reason == _REJECTED_DECISION.decision_reason


def test_grant_created_event() -> None:
    event = grant_created_event("AE-0006", _GRANT, _APPROVED_DECISION)
    assert event.event_type is AuditEventType.GRANT_CREATED
    assert event.grant_id == "AG-0001"
    assert event.correlation_id == request_correlation_id("AR-0001")
    assert event.metadata["dataset_count"] == "1"


def test_grant_revoked_event_requires_revoked_grant() -> None:
    with pytest.raises(ValueError, match="not revoked"):
        grant_revoked_event("AE-0007", _GRANT, _APPROVED_DECISION)


def test_grant_revoked_event_on_revoked_grant() -> None:
    revoked = AccessControlService.revoke_grant(
        _GRANT, revoked_at=datetime(2024, 7, 1), revocation_reason="No longer needed."
    )
    event = grant_revoked_event("AE-0007", revoked, _APPROVED_DECISION)

    assert event.event_type is AuditEventType.GRANT_REVOKED
    assert event.outcome is AuditOutcome.REVOKED
    assert event.reason == "No longer needed."


def test_grant_expired_event_requires_inactive_grant() -> None:
    with pytest.raises(ValueError, match="still active"):
        grant_expired_event("AE-0008", _GRANT, evaluated_at=datetime(2024, 7, 1))


def test_grant_expired_event_on_lapsed_grant() -> None:
    event = grant_expired_event("AE-0008", _GRANT, evaluated_at=datetime(2025, 1, 1))
    assert event.event_type is AuditEventType.GRANT_EXPIRED
    assert event.outcome is AuditOutcome.EXPIRED
    assert event.occurred_at == datetime(2025, 1, 1)


def test_grant_expired_event_rejects_revoked_grant() -> None:
    revoked = AccessControlService.revoke_grant(
        _GRANT, revoked_at=datetime(2024, 7, 1), revocation_reason="No longer needed."
    )
    with pytest.raises(ValueError, match="was revoked, not expired"):
        grant_expired_event("AE-0008", revoked, evaluated_at=datetime(2025, 1, 1))


def test_request_correlation_id_is_deterministic() -> None:
    assert request_correlation_id("AR-0001") == request_correlation_id("AR-0001")
    assert request_correlation_id("AR-0001") != request_correlation_id("AR-0002")
