from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.access import (
    AccessControlPortfolio,
    AccessGrant,
    AccessRequest,
    ApprovalDecision,
    DecisionType,
    RequesterRole,
)

_REQUEST_KWARGS = dict(
    requester_id="researcher-test-01",
    requester_role=RequesterRole.RESEARCHER,
    research_project_id="RP-0001",
    requested_dataset_ids=("DS-0001",),
    purpose="Used only in tests.",
    requested_at=datetime(2024, 6, 1),
    requested_until=datetime(2024, 9, 1),
)

_GRANT_KWARGS = dict(
    research_project_id="RP-0001",
    requester_id="researcher-test-01",
    dataset_ids=("DS-0001",),
    granted_at=datetime(2024, 6, 3),
    expires_at=datetime(2024, 9, 1),
)


def _request(request_id: str, **overrides: object) -> AccessRequest:
    fields = dict(_REQUEST_KWARGS, request_id=request_id)
    fields.update(overrides)
    return AccessRequest(**fields)


def _decision(decision_id: str, request_id: str, **overrides: object) -> ApprovalDecision:
    fields: dict[str, object] = dict(
        decision_id=decision_id,
        request_id=request_id,
        approver_id="access-approver-test-01",
        decision=DecisionType.APPROVED,
        decision_reason="All governance eligibility checks passed.",
        decided_at=datetime(2024, 6, 2),
    )
    fields.update(overrides)
    return ApprovalDecision(**fields)


def _grant(grant_id: str, request_id: str, **overrides: object) -> AccessGrant:
    fields = dict(_GRANT_KWARGS, grant_id=grant_id, request_id=request_id)
    fields.update(overrides)
    return AccessGrant(**fields)


def test_valid_portfolio_constructs() -> None:
    request = _request("AR-0001")
    decision = _decision("AD-0001", "AR-0001")
    grant = _grant("AG-0001", "AR-0001")

    portfolio = AccessControlPortfolio(requests=(request,), decisions=(decision,), grants=(grant,))

    assert portfolio.request_by_id("AR-0001").request_id == "AR-0001"
    assert portfolio.decision_for_request("AR-0001") is decision
    assert portfolio.grants_for_request("AR-0001") == (grant,)


def test_rejects_duplicate_request_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate request_id"):
        AccessControlPortfolio(requests=(_request("AR-0001"), _request("AR-0001")))


def test_rejects_duplicate_grant_ids() -> None:
    request = _request("AR-0001")
    decision = _decision("AD-0001", "AR-0001")
    with pytest.raises(ValidationError, match="duplicate grant_id"):
        AccessControlPortfolio(
            requests=(request,),
            decisions=(decision,),
            grants=(_grant("AG-0001", "AR-0001"), _grant("AG-0001", "AR-0001")),
        )


def test_rejects_decision_referencing_unknown_request() -> None:
    with pytest.raises(ValidationError, match="unknown request_id"):
        AccessControlPortfolio(decisions=(_decision("AD-0001", "AR-9999"),))


def test_rejects_second_decision_for_same_request() -> None:
    request = _request("AR-0001")
    with pytest.raises(ValidationError, match="more than one decision"):
        AccessControlPortfolio(
            requests=(request,),
            decisions=(_decision("AD-0001", "AR-0001"), _decision("AD-0002", "AR-0001")),
        )


def test_rejects_grant_for_unknown_request() -> None:
    with pytest.raises(ValidationError, match="unknown request_id"):
        AccessControlPortfolio(grants=(_grant("AG-0001", "AR-9999"),))


def test_rejects_grant_for_rejected_decision() -> None:
    request = _request("AR-0001")
    decision = _decision("AD-0001", "AR-0001", decision=DecisionType.REJECTED)
    with pytest.raises(ValidationError, match="no approved decision"):
        AccessControlPortfolio(
            requests=(request,), decisions=(decision,), grants=(_grant("AG-0001", "AR-0001"),)
        )


def test_rejects_grant_for_undecided_request() -> None:
    request = _request("AR-0001")
    with pytest.raises(ValidationError, match="no approved decision"):
        AccessControlPortfolio(requests=(request,), grants=(_grant("AG-0001", "AR-0001"),))


def test_rejects_grant_dataset_not_requested() -> None:
    request = _request("AR-0001", requested_dataset_ids=("DS-0001",))
    decision = _decision("AD-0001", "AR-0001")
    grant = _grant("AG-0001", "AR-0001", dataset_ids=("DS-0002",))
    with pytest.raises(ValidationError, match="not requested"):
        AccessControlPortfolio(requests=(request,), decisions=(decision,), grants=(grant,))


def test_rejects_grant_research_project_mismatch() -> None:
    request = _request("AR-0001", research_project_id="RP-0001")
    decision = _decision("AD-0001", "AR-0001")
    grant = _grant("AG-0001", "AR-0001", research_project_id="RP-0002")
    with pytest.raises(ValidationError, match="does not match"):
        AccessControlPortfolio(requests=(request,), decisions=(decision,), grants=(grant,))


def test_request_by_id_raises_for_unknown_id() -> None:
    portfolio = AccessControlPortfolio(requests=(_request("AR-0001"),))
    with pytest.raises(KeyError):
        portfolio.request_by_id("AR-9999")
