from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.audit import (
    ActorType,
    AuditAction,
    AuditEntityType,
    AuditEvent,
    AuditEventType,
    AuditLog,
    AuditOutcome,
)


def _event(
    event_id: str, occurred_at: datetime, correlation_id: str = "CORR-AR-0001"
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.ACCESS_REQUESTED,
        occurred_at=occurred_at,
        actor_id="researcher-test-01",
        actor_type=ActorType.RESEARCHER,
        entity_type=AuditEntityType.ACCESS_REQUEST,
        entity_id="AR-0001",
        action=AuditAction.REQUEST,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=correlation_id,
        research_project_id="RP-0001",
        request_id="AR-0001",
    )


def test_append_returns_new_log_and_does_not_mutate_original() -> None:
    log = AuditLog()
    event = _event("AE-0001", datetime(2025, 1, 1))

    appended = log.append(event)

    assert log.events == ()
    assert appended.events == (event,)
    assert appended is not log


def test_rejects_duplicate_event_ids() -> None:
    event = _event("AE-0001", datetime(2025, 1, 1))
    with pytest.raises(ValidationError, match="duplicate event_id"):
        AuditLog(events=(event, event))


def test_append_of_duplicate_id_raises() -> None:
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 1)),))
    with pytest.raises(ValidationError, match="duplicate event_id"):
        log.append(_event("AE-0001", datetime(2025, 1, 2)))


def test_rejects_backwards_timestamp_within_correlation_group() -> None:
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 5)),))
    with pytest.raises(ValidationError, match="timestamps within one governance activity"):
        log.append(_event("AE-0002", datetime(2025, 1, 1)))


def test_allows_backwards_timestamp_across_different_correlation_groups() -> None:
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 5), correlation_id="CORR-AR-0001"),))
    appended = log.append(_event("AE-0002", datetime(2020, 1, 1), correlation_id="CORR-AR-0002"))
    assert len(appended.events) == 2


def test_events_in_order_is_sorted_by_occurred_at_then_event_id() -> None:
    log = AuditLog(
        events=(
            _event("AE-0002", datetime(2025, 1, 2), correlation_id="CORR-AR-0002"),
            _event("AE-0001", datetime(2025, 1, 1), correlation_id="CORR-AR-0001"),
        )
    )
    ordered = log.events_in_order()
    assert [e.event_id for e in ordered] == ["AE-0001", "AE-0002"]


def test_filter_by_entity_id() -> None:
    other = _event("AE-0002", datetime(2025, 1, 2), correlation_id="CORR-AR-0002").model_copy(
        update={"entity_id": "AR-0002", "request_id": "AR-0002"}
    )
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 1)), other))

    result = log.filter_by_entity_id("AR-0001")

    assert [e.event_id for e in result] == ["AE-0001"]


def test_filter_by_research_project() -> None:
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 1)),))
    assert len(log.filter_by_research_project("RP-0001")) == 1
    assert len(log.filter_by_research_project("RP-9999")) == 0


def test_filter_by_request() -> None:
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 1)),))
    assert len(log.filter_by_request("AR-0001")) == 1
    assert len(log.filter_by_request("AR-9999")) == 0


def test_filter_by_event_type() -> None:
    log = AuditLog(events=(_event("AE-0001", datetime(2025, 1, 1)),))
    assert len(log.filter_by_event_type(AuditEventType.ACCESS_REQUESTED)) == 1
    assert len(log.filter_by_event_type(AuditEventType.GRANT_CREATED)) == 0


def test_correlation_groups_group_and_order_events() -> None:
    # Stored out of chronological order (allowed since the two events belong
    # to different correlation groups — the ordering invariant only applies
    # within one group); events_in_order()/correlation_groups() must still
    # return them sorted by occurred_at rather than storage order.
    log = AuditLog(
        events=(
            _event("AE-0002", datetime(2025, 1, 2), correlation_id="CORR-AR-0002"),
            _event("AE-0001", datetime(2025, 1, 1), correlation_id="CORR-AR-0001"),
        )
    )
    assert [e.event_id for e in log.events_in_order()] == ["AE-0001", "AE-0002"]

    groups = log.correlation_groups()
    assert [e.event_id for e in groups["CORR-AR-0001"]] == ["AE-0001"]
    assert [e.event_id for e in groups["CORR-AR-0002"]] == ["AE-0002"]
