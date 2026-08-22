from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import AuditEventType, check_completeness, generate_audit_log
from governance_platform.audit.adapters import request_correlation_id
from governance_platform.inventory import generate_portfolio


def test_generation_is_deterministic() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()

    first = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    second = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_event_ids_are_sequential_and_gapless() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    ids = [e.event_id for e in log.events]
    expected = [f"AE-{i:04d}" for i in range(1, len(ids) + 1)]
    assert ids == expected


def test_generated_log_is_complete() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    assert check_completeness(log, inventory, access_state) == []


def test_every_request_lifecycle_is_correlated_together() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    # AR-0001 is the valid approved request that becomes the active grant
    # (see governance_platform.access.generation) — its whole lifecycle
    # (request -> evaluation -> approval -> grant) must share one
    # correlation id.
    correlation_id = request_correlation_id("AR-0001")
    group = log.filter_by_correlation_id(correlation_id)
    event_types = {e.event_type for e in group}

    assert event_types == {
        AuditEventType.ACCESS_REQUESTED,
        AuditEventType.ACCESS_EVALUATED,
        AuditEventType.ACCESS_APPROVED,
        AuditEventType.GRANT_CREATED,
    }


def test_revoked_request_lifecycle_includes_revocation_event() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    group = log.filter_by_correlation_id(request_correlation_id("AR-0010"))
    event_types = {e.event_type for e in group}

    assert AuditEventType.GRANT_REVOKED in event_types
    assert AuditEventType.GRANT_EXPIRED not in event_types


def test_expired_grant_lifecycle_includes_expiry_event() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    group = log.filter_by_correlation_id(request_correlation_id("AR-0009"))
    event_types = {e.event_type for e in group}

    assert AuditEventType.GRANT_EXPIRED in event_types
    assert AuditEventType.GRANT_REVOKED not in event_types


def test_rejected_request_lifecycle_has_no_grant_events() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    group = log.filter_by_correlation_id(request_correlation_id("AR-0002"))
    event_types = {e.event_type for e in group}

    assert event_types == {
        AuditEventType.ACCESS_REQUESTED,
        AuditEventType.ACCESS_EVALUATED,
        AuditEventType.ACCESS_REJECTED,
    }


def test_reuses_milestone_3_scenarios_not_a_separate_universe() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)

    request_ids_in_log = {e.request_id for e in log.events if e.request_id is not None}
    assert request_ids_in_log == {r.request_id for r in access_state.requests}
