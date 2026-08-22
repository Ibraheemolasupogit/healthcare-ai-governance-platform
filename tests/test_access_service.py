from datetime import date, datetime

import pytest

from governance_platform.access import (
    AccessControlService,
    DecisionType,
    GrantStatus,
    RequesterRole,
    RequestStatus,
)
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


@pytest.fixture
def inventory() -> InventoryPortfolio:
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
    project = ResearchProject(
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
    return InventoryPortfolio(datasets=(dataset,), research_projects=(project,))


def _submit(service: AccessControlService, **overrides: object):
    fields: dict[str, object] = dict(
        request_id="AR-0001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        purpose="Used only in tests.",
        requested_at=datetime(2024, 6, 1),
        requested_until=datetime(2024, 9, 1),
        requested_dataset_ids=("DS-0001",),
    )
    fields.update(overrides)
    return service.submit_request(**fields)


class TestSubmitAndDecide:
    def test_submit_creates_a_submitted_request(self, inventory: InventoryPortfolio) -> None:
        service = AccessControlService(inventory)
        request = _submit(service)

        assert request.status is RequestStatus.SUBMITTED

    def test_decide_approves_an_eligible_request(self, inventory: InventoryPortfolio) -> None:
        service = AccessControlService(inventory)
        request = _submit(service)

        finalized, decision = service.decide(
            request,
            decision_id="AD-0001",
            approver_id="access-approver-test-01",
            decided_at=datetime(2024, 6, 2),
        )

        assert decision.decision is DecisionType.APPROVED
        assert finalized.status is RequestStatus.APPROVED
        assert "passed" in decision.decision_reason.lower()

    def test_decide_rejects_an_ineligible_request(self, inventory: InventoryPortfolio) -> None:
        service = AccessControlService(inventory)
        request = _submit(
            service, research_project_id="RP-0001", requested_dataset_ids=("DS-9999",)
        )

        finalized, decision = service.decide(
            request,
            decision_id="AD-0001",
            approver_id="access-approver-test-01",
            decided_at=datetime(2024, 6, 2),
        )

        assert decision.decision is DecisionType.REJECTED
        assert finalized.status is RequestStatus.REJECTED
        assert "DS-9999" in decision.decision_reason

    def test_original_request_object_is_not_mutated(self, inventory: InventoryPortfolio) -> None:
        service = AccessControlService(inventory)
        request = _submit(service)

        service.decide(
            request,
            decision_id="AD-0001",
            approver_id="access-approver-test-01",
            decided_at=datetime(2024, 6, 2),
        )

        assert request.status is RequestStatus.SUBMITTED


class TestCreateGrant:
    def test_creates_grant_from_approved_decision(self, inventory: InventoryPortfolio) -> None:
        service = AccessControlService(inventory)
        request = _submit(service)
        finalized, decision = service.decide(
            request,
            decision_id="AD-0001",
            approver_id="access-approver-test-01",
            decided_at=datetime(2024, 6, 2),
        )

        grant = service.create_grant(
            finalized,
            decision,
            grant_id="AG-0001",
            granted_at=datetime(2024, 6, 3),
            expires_at=datetime(2024, 9, 1),
        )

        assert grant.status is GrantStatus.ISSUED
        assert grant.dataset_ids == ("DS-0001",)

    def test_raises_for_rejected_decision(self, inventory: InventoryPortfolio) -> None:
        service = AccessControlService(inventory)
        request = _submit(service, requested_dataset_ids=("DS-9999",))
        finalized, decision = service.decide(
            request,
            decision_id="AD-0001",
            approver_id="access-approver-test-01",
            decided_at=datetime(2024, 6, 2),
        )

        with pytest.raises(ValueError, match="cannot create a grant"):
            service.create_grant(
                finalized,
                decision,
                grant_id="AG-0001",
                granted_at=datetime(2024, 6, 3),
                expires_at=datetime(2024, 9, 1),
            )

    def test_raises_for_mismatched_request_and_decision(
        self, inventory: InventoryPortfolio
    ) -> None:
        service = AccessControlService(inventory)
        request_a = _submit(service, request_id="AR-0001")
        request_b = _submit(service, request_id="AR-0002")
        _, decision_a = service.decide(
            request_a,
            decision_id="AD-0001",
            approver_id="access-approver-test-01",
            decided_at=datetime(2024, 6, 2),
        )

        with pytest.raises(ValueError, match="does not correspond to"):
            service.create_grant(
                request_b,
                decision_a,
                grant_id="AG-0001",
                granted_at=datetime(2024, 6, 3),
                expires_at=datetime(2024, 9, 1),
            )


class TestGrantActivityAndRevocation:
    def test_grant_is_active_within_its_window(self) -> None:
        from governance_platform.access import AccessGrant

        grant = AccessGrant(
            grant_id="AG-0001",
            request_id="AR-0001",
            research_project_id="RP-0001",
            requester_id="researcher-test-01",
            dataset_ids=("DS-0001",),
            granted_at=datetime(2024, 1, 1),
            expires_at=datetime(2024, 12, 31),
        )

        assert AccessControlService.is_grant_active(grant, datetime(2024, 6, 1)) is True
        assert AccessControlService.is_grant_active(grant, datetime(2023, 12, 31)) is False
        assert AccessControlService.is_grant_active(grant, datetime(2025, 1, 1)) is False

    def test_revoked_grant_is_never_active_even_within_window(self) -> None:
        from governance_platform.access import AccessGrant

        grant = AccessGrant(
            grant_id="AG-0001",
            request_id="AR-0001",
            research_project_id="RP-0001",
            requester_id="researcher-test-01",
            dataset_ids=("DS-0001",),
            granted_at=datetime(2024, 1, 1),
            expires_at=datetime(2024, 12, 31),
        )
        revoked = AccessControlService.revoke_grant(
            grant, revoked_at=datetime(2024, 6, 1), revocation_reason="No longer needed."
        )

        assert AccessControlService.is_grant_active(revoked, datetime(2024, 7, 1)) is False
        assert grant.status is GrantStatus.ISSUED  # original untouched

    def test_revoking_an_already_revoked_grant_raises(self) -> None:
        from governance_platform.access import AccessGrant

        grant = AccessGrant(
            grant_id="AG-0001",
            request_id="AR-0001",
            research_project_id="RP-0001",
            requester_id="researcher-test-01",
            dataset_ids=("DS-0001",),
            granted_at=datetime(2024, 1, 1),
            expires_at=datetime(2024, 12, 31),
            status=GrantStatus.REVOKED,
            revoked_at=datetime(2024, 6, 1),
            revocation_reason="Already revoked.",
        )

        with pytest.raises(ValueError, match="already revoked"):
            AccessControlService.revoke_grant(
                grant, revoked_at=datetime(2024, 7, 1), revocation_reason="Again."
            )

    def test_expired_grants_excludes_active_and_revoked(self) -> None:
        from governance_platform.access import AccessGrant

        active = AccessGrant(
            grant_id="AG-0001",
            request_id="AR-0001",
            research_project_id="RP-0001",
            requester_id="researcher-test-01",
            dataset_ids=("DS-0001",),
            granted_at=datetime(2024, 1, 1),
            expires_at=datetime(2024, 12, 31),
        )
        expired = AccessGrant(
            grant_id="AG-0002",
            request_id="AR-0002",
            research_project_id="RP-0001",
            requester_id="researcher-test-01",
            dataset_ids=("DS-0001",),
            granted_at=datetime(2023, 1, 1),
            expires_at=datetime(2023, 6, 1),
        )
        revoked = AccessGrant(
            grant_id="AG-0003",
            request_id="AR-0003",
            research_project_id="RP-0001",
            requester_id="researcher-test-01",
            dataset_ids=("DS-0001",),
            granted_at=datetime(2023, 1, 1),
            expires_at=datetime(2023, 6, 1),
            status=GrantStatus.REVOKED,
            revoked_at=datetime(2023, 3, 1),
            revocation_reason="Revoked before expiry.",
        )

        result = AccessControlService.expired_grants(
            (active, expired, revoked), datetime(2024, 6, 1)
        )

        assert result == [expired]
