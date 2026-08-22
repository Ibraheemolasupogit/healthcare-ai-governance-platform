from datetime import date, datetime

from governance_platform.access import (
    AccessControlPortfolio,
    AccessControlService,
    AccessGrant,
    AccessRequest,
    ApprovalDecision,
    DecisionType,
    RequesterRole,
)
from governance_platform.audit import (
    ActorType,
    AuditEntityType,
    AuditEvent,
    AuditLog,
    check_completeness,
)
from governance_platform.audit.adapters import (
    access_decision_event,
    access_evaluated_event,
    access_requested_event,
    grant_created_event,
    grant_revoked_event,
    request_correlation_id,
)
from governance_platform.audit.enums import AuditAction, AuditEventType, AuditOutcome
from governance_platform.inventory import (
    ApprovalStatus,
    DataCategory,
    Dataset,
    InventoryPortfolio,
    LifecycleStatus,
    ResearchProject,
    RetentionClass,
    RiskTier,
    SensitivityClassification,
    SourceType,
    WorkspaceStatus,
)

_DATASET = Dataset(
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
_PROJECT = ResearchProject(
    research_project_id="RP-0001",
    title="Test Project",
    principal_owner="Test Principal Investigator",
    purpose="Used only in tests.",
    linked_dataset_ids=("DS-0001",),
    approval_status=ApprovalStatus.APPROVED,
    risk_classification=RiskTier.LOW,
    start_date=date(2024, 1, 1),
    expiry_date=date(2025, 1, 1),
    workspace_status=WorkspaceStatus.ACTIVE,
)
_INVENTORY = InventoryPortfolio(datasets=(_DATASET,), research_projects=(_PROJECT,))


def _approved_request() -> AccessRequest:
    from governance_platform.access import RequestStatus

    return AccessRequest(
        request_id="AR-0001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        requested_dataset_ids=("DS-0001",),
        purpose="Used only in tests.",
        requested_at=datetime(2024, 6, 1),
        requested_until=datetime(2024, 9, 1),
        status=RequestStatus.APPROVED,
    )


def _decision(request_id: str = "AR-0001") -> ApprovalDecision:
    return ApprovalDecision(
        decision_id="AD-0001",
        request_id=request_id,
        approver_id="access-approver-test-01",
        decision=DecisionType.APPROVED,
        decision_reason="All governance eligibility checks passed.",
        decided_at=datetime(2024, 6, 2),
    )


def _grant() -> AccessGrant:
    return AccessGrant(
        grant_id="AG-0001",
        request_id="AR-0001",
        research_project_id="RP-0001",
        requester_id="researcher-test-01",
        dataset_ids=("DS-0001",),
        granted_at=datetime(2024, 6, 3),
        expires_at=datetime(2024, 9, 1),
    )


def test_complete_log_has_no_problems() -> None:
    request = _approved_request()
    decision = _decision()
    grant = _grant()
    access_state = AccessControlPortfolio(
        requests=(request,), decisions=(decision,), grants=(grant,)
    )
    log = AuditLog()
    log = log.append(access_requested_event("AE-0001", request))
    log = log.append(access_evaluated_event("AE-0002", request, decision))
    log = log.append(access_decision_event("AE-0003", request, decision))
    log = log.append(grant_created_event("AE-0004", grant, decision))

    assert check_completeness(log, _INVENTORY, access_state) == []


def test_reports_missing_evaluation_event() -> None:
    request = _approved_request()
    access_state = AccessControlPortfolio(requests=(request,))
    log = AuditLog().append(access_requested_event("AE-0001", request))

    problems = check_completeness(log, _INVENTORY, access_state)

    assert any("no access_evaluated event" in p for p in problems)


def test_reports_missing_rejection_event() -> None:
    from governance_platform.access import RequestStatus

    request = AccessRequest(
        request_id="AR-0001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        requested_dataset_ids=("DS-0001",),
        purpose="Used only in tests.",
        requested_at=datetime(2024, 6, 1),
        requested_until=datetime(2024, 9, 1),
        status=RequestStatus.REJECTED,
    )
    decision = ApprovalDecision(
        decision_id="AD-0001",
        request_id="AR-0001",
        approver_id="access-approver-test-01",
        decision=DecisionType.REJECTED,
        decision_reason="dataset DS-9999 does not exist in the inventory",
        decided_at=datetime(2024, 6, 2),
    )
    access_state = AccessControlPortfolio(requests=(request,), decisions=(decision,))
    log = AuditLog()
    log = log.append(access_requested_event("AE-0001", request))
    log = log.append(access_evaluated_event("AE-0002", request, decision))

    problems = check_completeness(log, _INVENTORY, access_state)

    assert any("no access_rejected event" in p for p in problems)


def test_reports_missing_grant_created_event() -> None:
    request = _approved_request()
    decision = _decision()
    grant = _grant()
    access_state = AccessControlPortfolio(
        requests=(request,), decisions=(decision,), grants=(grant,)
    )
    log = AuditLog()
    log = log.append(access_requested_event("AE-0001", request))
    log = log.append(access_evaluated_event("AE-0002", request, decision))
    log = log.append(access_decision_event("AE-0003", request, decision))

    problems = check_completeness(log, _INVENTORY, access_state)

    assert any("no grant_created event" in p for p in problems)


def test_reports_missing_grant_revoked_event() -> None:
    request = _approved_request()
    decision = _decision()
    revoked_grant = AccessControlService.revoke_grant(
        _grant(), revoked_at=datetime(2024, 7, 1), revocation_reason="No longer needed."
    )
    access_state = AccessControlPortfolio(
        requests=(request,), decisions=(decision,), grants=(revoked_grant,)
    )
    log = AuditLog()
    log = log.append(access_requested_event("AE-0001", request))
    log = log.append(access_evaluated_event("AE-0002", request, decision))
    log = log.append(access_decision_event("AE-0003", request, decision))
    log = log.append(grant_created_event("AE-0004", revoked_grant, decision))

    problems = check_completeness(log, _INVENTORY, access_state)
    assert any("no grant_revoked event" in p for p in problems)

    complete_log = log.append(grant_revoked_event("AE-0005", revoked_grant, decision))
    assert check_completeness(complete_log, _INVENTORY, access_state) == []


def test_reports_unknown_request_id_reference() -> None:
    request = _approved_request()
    access_state = AccessControlPortfolio(requests=(request,))
    stray_event = AuditEvent(
        event_id="AE-9999",
        event_type=AuditEventType.ACCESS_REQUESTED,
        occurred_at=datetime(2024, 6, 1),
        actor_id="researcher-test-01",
        actor_type=ActorType.RESEARCHER,
        entity_type=AuditEntityType.ACCESS_REQUEST,
        entity_id="AR-9999",
        action=AuditAction.REQUEST,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=request_correlation_id("AR-9999"),
        request_id="AR-9999",
    )
    log = AuditLog(events=(stray_event,))

    problems = check_completeness(log, _INVENTORY, access_state)

    assert any("unknown request_id" in p for p in problems)


def test_does_not_report_unknown_project_for_a_rejected_requests_own_events() -> None:
    # A request rejected specifically because it named an unknown project is
    # exactly the audit trail doing its job — this must not be flagged as a
    # completeness problem (see governance_platform.audit.completeness).
    request = AccessRequest(
        request_id="AR-0001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-9999",
        requested_dataset_ids=("DS-0001",),
        purpose="Used only in tests.",
        requested_at=datetime(2024, 6, 1),
        requested_until=datetime(2024, 9, 1),
    )
    decision = ApprovalDecision(
        decision_id="AD-0001",
        request_id="AR-0001",
        approver_id="access-approver-test-01",
        decision=DecisionType.REJECTED,
        decision_reason="research project RP-9999 does not exist in the inventory",
        decided_at=datetime(2024, 6, 2),
    )
    access_state = AccessControlPortfolio(requests=(request,), decisions=(decision,))
    log = AuditLog()
    log = log.append(access_requested_event("AE-0001", request))
    log = log.append(access_evaluated_event("AE-0002", request, decision))
    log = log.append(access_decision_event("AE-0003", request, decision))

    problems = check_completeness(log, _INVENTORY, access_state)

    assert problems == []


def test_reports_duplicate_event_ids_if_present() -> None:
    # AuditLog itself rejects duplicates at construction time; model_construct
    # bypasses validation to exercise check_completeness's own defensive check.
    request = _approved_request()
    access_state = AccessControlPortfolio(requests=(request,))
    event = access_requested_event("AE-0001", request)
    log = AuditLog.model_construct(events=(event, event))

    problems = check_completeness(log, _INVENTORY, access_state)

    assert any("duplicate event_id" in p for p in problems)
