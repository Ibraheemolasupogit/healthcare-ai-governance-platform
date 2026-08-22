from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.audit import (
    ActorType,
    AuditAction,
    AuditEntityType,
    AuditEvent,
    AuditEventType,
    AuditOutcome,
)


def _event(**overrides: object) -> AuditEvent:
    fields: dict[str, object] = dict(
        event_id="AE-0001",
        event_type=AuditEventType.ACCESS_REQUESTED,
        occurred_at=datetime(2025, 1, 1),
        actor_id="researcher-test-01",
        actor_type=ActorType.RESEARCHER,
        entity_type=AuditEntityType.ACCESS_REQUEST,
        entity_id="AR-0001",
        action=AuditAction.REQUEST,
        outcome=AuditOutcome.SUCCESS,
        correlation_id="CORR-AR-0001",
        research_project_id="RP-0001",
        request_id="AR-0001",
    )
    fields.update(overrides)
    return AuditEvent(**fields)


def test_valid_event_constructs() -> None:
    event = _event()
    assert event.event_id == "AE-0001"
    assert event.event_type is AuditEventType.ACCESS_REQUESTED


def test_rejects_malformed_event_id() -> None:
    with pytest.raises(ValidationError):
        _event(event_id="evt-1")


def test_rejects_unknown_extra_field() -> None:
    with pytest.raises(ValidationError):
        _event(unexpected_field="nope")


def test_frozen_event_cannot_be_mutated() -> None:
    event = _event()
    with pytest.raises(ValidationError):
        event.outcome = AuditOutcome.DENIED


def test_rejects_entity_type_mismatched_with_event_type() -> None:
    with pytest.raises(ValidationError, match="must have entity_type"):
        _event(entity_type=AuditEntityType.ACCESS_GRANT)


def test_rejects_action_mismatched_with_event_type() -> None:
    with pytest.raises(ValidationError, match="must have action"):
        _event(action=AuditAction.APPROVE)


def test_request_scoped_event_requires_request_id() -> None:
    with pytest.raises(ValidationError, match="requires request_id"):
        _event(request_id=None)


def test_decision_scoped_event_requires_decision_id() -> None:
    with pytest.raises(ValidationError, match="requires decision_id"):
        _event(
            event_type=AuditEventType.ACCESS_APPROVED,
            entity_type=AuditEntityType.ACCESS_REQUEST,
            action=AuditAction.APPROVE,
            outcome=AuditOutcome.SUCCESS,
        )


def test_grant_scoped_event_requires_grant_id() -> None:
    with pytest.raises(ValidationError, match="requires grant_id"):
        _event(
            event_id="AE-0002",
            event_type=AuditEventType.GRANT_CREATED,
            entity_type=AuditEntityType.ACCESS_GRANT,
            entity_id="AG-0001",
            action=AuditAction.CREATE,
            outcome=AuditOutcome.SUCCESS,
            correlation_id="CORR-AR-0001",
            research_project_id="RP-0001",
            request_id="AR-0001",
        )


def test_inventory_scoped_event_rejects_access_identifiers() -> None:
    with pytest.raises(ValidationError, match="must not carry"):
        _event(
            event_id="AE-0003",
            event_type=AuditEventType.INVENTORY_CREATED,
            entity_type=AuditEntityType.INVENTORY,
            entity_id="INVENTORY-PORTFOLIO",
            action=AuditAction.CREATE,
            outcome=AuditOutcome.SUCCESS,
            correlation_id="CORR-INVENTORY-0001",
        )


def test_inventory_scoped_event_without_access_identifiers_is_valid() -> None:
    event = _event(
        event_id="AE-0003",
        event_type=AuditEventType.INVENTORY_CREATED,
        entity_type=AuditEntityType.INVENTORY,
        entity_id="INVENTORY-PORTFOLIO",
        action=AuditAction.CREATE,
        outcome=AuditOutcome.SUCCESS,
        correlation_id="CORR-INVENTORY-0001",
        research_project_id=None,
        request_id=None,
    )
    assert event.entity_type is AuditEntityType.INVENTORY


@pytest.mark.parametrize(
    "metadata",
    [
        {"note": "patient outcome improved"},
        {"password": "irrelevant"},
        {"ssn": "irrelevant"},
        {"detail": "contains a token value"},
    ],
)
def test_rejects_metadata_with_sensitive_markers(metadata: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="sensitive data"):
        _event(metadata=metadata)


def test_accepts_benign_metadata() -> None:
    event = _event(metadata={"requester_role": "researcher"})
    assert event.metadata == {"requester_role": "researcher"}
