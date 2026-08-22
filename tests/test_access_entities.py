from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.access import (
    AccessGrant,
    AccessRequest,
    ApprovalDecision,
    DecisionType,
    GrantStatus,
    RequesterRole,
    RequestStatus,
)


def _request(**overrides: object) -> AccessRequest:
    fields: dict[str, object] = dict(
        request_id="AR-0001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        requested_dataset_ids=("DS-0001",),
        requested_model_ids=(),
        purpose="Used only in tests.",
        requested_at=datetime(2025, 1, 1),
        requested_until=datetime(2025, 2, 1),
        status=RequestStatus.SUBMITTED,
    )
    fields.update(overrides)
    return AccessRequest(**fields)


def _decision(**overrides: object) -> ApprovalDecision:
    fields: dict[str, object] = dict(
        decision_id="AD-0001",
        request_id="AR-0001",
        approver_id="access-approver-test-01",
        decision=DecisionType.APPROVED,
        decision_reason="All governance eligibility checks passed.",
        decided_at=datetime(2025, 1, 2),
    )
    fields.update(overrides)
    return ApprovalDecision(**fields)


def _grant(**overrides: object) -> AccessGrant:
    fields: dict[str, object] = dict(
        grant_id="AG-0001",
        request_id="AR-0001",
        research_project_id="RP-0001",
        requester_id="researcher-test-01",
        dataset_ids=("DS-0001",),
        model_ids=(),
        granted_at=datetime(2025, 1, 3),
        expires_at=datetime(2025, 2, 1),
        status=GrantStatus.ISSUED,
    )
    fields.update(overrides)
    return AccessGrant(**fields)


class TestAccessRequestValidation:
    def test_valid_request_constructs(self) -> None:
        request = _request()
        assert request.request_id == "AR-0001"
        assert request.status is RequestStatus.SUBMITTED

    def test_rejects_malformed_request_id(self) -> None:
        with pytest.raises(ValidationError):
            _request(request_id="req-1")

    def test_rejects_malformed_research_project_id(self) -> None:
        with pytest.raises(ValidationError):
            _request(research_project_id="proj-1")

    def test_rejects_request_with_no_datasets_or_models(self) -> None:
        with pytest.raises(ValidationError, match="must request at least one"):
            _request(requested_dataset_ids=(), requested_model_ids=())

    def test_rejects_requested_until_before_requested_at(self) -> None:
        with pytest.raises(ValidationError, match="requested_until"):
            _request(requested_at=datetime(2025, 6, 1), requested_until=datetime(2025, 1, 1))

    def test_rejects_requested_until_equal_to_requested_at(self) -> None:
        with pytest.raises(ValidationError, match="requested_until"):
            _request(requested_at=datetime(2025, 6, 1), requested_until=datetime(2025, 6, 1))

    def test_rejects_unknown_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            _request(unexpected_field="nope")

    def test_frozen_request_cannot_be_mutated(self) -> None:
        request = _request()
        with pytest.raises(ValidationError):
            request.status = RequestStatus.APPROVED


class TestApprovalDecisionValidation:
    def test_valid_decision_constructs(self) -> None:
        decision = _decision()
        assert decision.decision is DecisionType.APPROVED

    def test_rejects_malformed_decision_id(self) -> None:
        with pytest.raises(ValidationError):
            _decision(decision_id="dec-1")

    def test_rejects_empty_decision_reason(self) -> None:
        with pytest.raises(ValidationError):
            _decision(decision_reason="")


class TestAccessGrantValidation:
    def test_valid_grant_constructs(self) -> None:
        grant = _grant()
        assert grant.status is GrantStatus.ISSUED
        assert grant.revoked_at is None

    def test_rejects_malformed_grant_id(self) -> None:
        with pytest.raises(ValidationError):
            _grant(grant_id="grant-1")

    def test_rejects_expires_at_not_after_granted_at(self) -> None:
        with pytest.raises(ValidationError, match="time-bounded"):
            _grant(granted_at=datetime(2025, 6, 1), expires_at=datetime(2025, 6, 1))

    def test_rejects_revoked_status_without_revocation_fields(self) -> None:
        with pytest.raises(ValidationError, match="status=revoked requires"):
            _grant(status=GrantStatus.REVOKED)

    def test_rejects_revocation_fields_without_revoked_status(self) -> None:
        with pytest.raises(ValidationError, match="only be set when status=revoked"):
            _grant(revoked_at=datetime(2025, 1, 10), revocation_reason="Not actually revoked.")

    def test_rejects_revoked_at_before_granted_at(self) -> None:
        with pytest.raises(ValidationError, match="revoked_at"):
            _grant(
                status=GrantStatus.REVOKED,
                revoked_at=datetime(2025, 1, 1),
                revocation_reason="Too early.",
                granted_at=datetime(2025, 1, 3),
            )

    def test_accepts_consistent_revoked_grant(self) -> None:
        grant = _grant(
            status=GrantStatus.REVOKED,
            revoked_at=datetime(2025, 1, 10),
            revocation_reason="Requester left the team.",
        )
        assert grant.status is GrantStatus.REVOKED
        assert grant.revoked_at == datetime(2025, 1, 10)
