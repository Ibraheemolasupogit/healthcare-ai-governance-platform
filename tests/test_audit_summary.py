from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import build_audit_summary, generate_audit_log
from governance_platform.inventory import generate_portfolio


def test_summary_total_events_matches_log() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    summary = build_audit_summary(log, access_state)

    assert summary.total_events == len(log.events)


def test_summary_events_by_type_counts_are_correct() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    summary = build_audit_summary(log, access_state)

    assert summary.events_by_type["access_requested"] == 10
    assert summary.events_by_type["access_approved"] == 3
    assert summary.events_by_type["access_rejected"] == 7
    assert summary.events_by_type["grant_created"] == 3
    assert summary.events_by_type["grant_revoked"] == 1
    assert summary.events_by_type["grant_expired"] == 1
    # every AuditEventType member is present, even at zero, for a stable shape
    assert set(summary.events_by_type) == {
        "inventory_created",
        "inventory_validated",
        "access_requested",
        "access_evaluated",
        "access_approved",
        "access_rejected",
        "grant_created",
        "grant_revoked",
        "grant_expired",
    }


def test_summary_events_by_research_project() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    summary = build_audit_summary(log, access_state)

    # RP-9999 (the unknown-project scenario) is still recorded against the
    # project id the request named, even though it doesn't resolve.
    assert "RP-9999" in summary.events_by_research_project
    assert sum(summary.events_by_research_project.values()) > 0


def test_summary_coverage_is_fully_covered_for_generated_state() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    coverage = build_audit_summary(log, access_state).coverage

    assert coverage.requests_with_evaluation_event == coverage.requests_total == 10
    assert coverage.rejected_requests_with_rejection_event == coverage.rejected_requests_total == 7
    assert coverage.grants_with_creation_event == coverage.grants_total == 3
    assert coverage.revoked_grants_with_revocation_event == coverage.revoked_grants_total == 1


def test_summary_on_empty_log_has_zeroed_counts() -> None:
    from governance_platform.access import AccessControlPortfolio
    from governance_platform.audit import AuditLog

    summary = build_audit_summary(AuditLog(), AccessControlPortfolio())

    assert summary.total_events == 0
    assert all(count == 0 for count in summary.events_by_type.values())
    assert summary.coverage.requests_total == 0
