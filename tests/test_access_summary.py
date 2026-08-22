from datetime import datetime

from governance_platform.access import generate_access_control_state
from governance_platform.access.summary import build_access_summary
from governance_platform.inventory import generate_portfolio


def test_summary_total_requests_matches_state() -> None:
    inventory = generate_portfolio()
    state = generate_access_control_state()
    summary = build_access_summary(state, inventory, evaluated_at=datetime(2025, 3, 15))

    assert summary.total_requests == len(state.requests)


def test_summary_request_status_counts_are_correct() -> None:
    inventory = generate_portfolio()
    state = generate_access_control_state()
    summary = build_access_summary(state, inventory, evaluated_at=datetime(2025, 3, 15))

    expected_approved = sum(1 for r in state.requests if r.status.value == "approved")
    expected_rejected = sum(1 for r in state.requests if r.status.value == "rejected")

    assert summary.request_status["approved"] == expected_approved
    assert summary.request_status["rejected"] == expected_rejected
    assert set(summary.request_status) == {"submitted", "approved", "rejected"}


def test_summary_grant_status_reflects_evaluation_time() -> None:
    inventory = generate_portfolio()
    state = generate_access_control_state()

    # Well before any grant starts: nothing can be active or expired yet,
    # but a revocation is a fact independent of the evaluation time.
    early_summary = build_access_summary(state, inventory, evaluated_at=datetime(2020, 1, 1))
    assert early_summary.grant_status.active == 0
    assert early_summary.grant_status.revoked == 1

    later_summary = build_access_summary(state, inventory, evaluated_at=datetime(2025, 3, 15))
    assert later_summary.grant_status.active == 1
    assert later_summary.grant_status.expired == 1
    assert later_summary.grant_status.revoked == 1


def test_summary_rejection_reason_categories_have_stable_shape() -> None:
    inventory = generate_portfolio()
    state = generate_access_control_state()
    summary = build_access_summary(state, inventory, evaluated_at=datetime(2025, 3, 15))

    assert sum(summary.rejection_reason_categories.values()) > 0
    assert "unknown_research_project" in summary.rejection_reason_categories


def test_summary_on_empty_state_has_zeroed_counts() -> None:
    from governance_platform.access import AccessControlPortfolio

    inventory = generate_portfolio()
    summary = build_access_summary(
        AccessControlPortfolio(), inventory, evaluated_at=datetime(2025, 3, 15)
    )

    assert summary.total_requests == 0
    assert summary.grant_status.active == 0
    assert summary.grant_status.expired == 0
    assert summary.grant_status.revoked == 0
    assert all(count == 0 for count in summary.rejection_reason_categories.values())
