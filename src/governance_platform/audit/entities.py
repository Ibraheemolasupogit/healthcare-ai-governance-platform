"""The typed audit event: one immutable record of a governance action.

An :class:`AuditEvent` is never edited — a correction is a new event, per
``governance/audit_evidence.md`` ("corrections are recorded as new events,
not edits to history"). This module only enforces invariants that hold for a
single event in isolation (its own field consistency); append-only storage,
uniqueness, and ordering are enforced by
:class:`~governance_platform.audit.log.AuditLog`, and cross-plane
completeness (e.g. "every request has an evaluation event") is checked by
:mod:`governance_platform.audit.completeness` — not here, to keep this
entity constructible without depending on the inventory or access planes.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from governance_platform.audit.enums import (
    ActorType,
    AuditAction,
    AuditEntityType,
    AuditEventType,
    AuditOutcome,
)

_EVENT_ID_PATTERN = re.compile(r"^AE-\d{4}$")
_REQUEST_ID_PATTERN = re.compile(r"^AR-\d{4}$")
_DECISION_ID_PATTERN = re.compile(r"^AD-\d{4}$")
_GRANT_ID_PATTERN = re.compile(r"^AG-\d{4}$")
_RESEARCH_PROJECT_ID_PATTERN = re.compile(r"^RP-\d{4}$")

#: Each event type concerns exactly one kind of primary entity — enforced
#: below rather than left to caller discipline.
_EVENT_TYPE_ENTITY_TYPES: dict[AuditEventType, AuditEntityType] = {
    AuditEventType.INVENTORY_CREATED: AuditEntityType.INVENTORY,
    AuditEventType.INVENTORY_VALIDATED: AuditEntityType.INVENTORY,
    AuditEventType.ACCESS_REQUESTED: AuditEntityType.ACCESS_REQUEST,
    AuditEventType.ACCESS_EVALUATED: AuditEntityType.ACCESS_REQUEST,
    AuditEventType.ACCESS_APPROVED: AuditEntityType.ACCESS_REQUEST,
    AuditEventType.ACCESS_REJECTED: AuditEntityType.ACCESS_REQUEST,
    AuditEventType.GRANT_CREATED: AuditEntityType.ACCESS_GRANT,
    AuditEventType.GRANT_REVOKED: AuditEntityType.ACCESS_GRANT,
    AuditEventType.GRANT_EXPIRED: AuditEntityType.ACCESS_GRANT,
}

#: Each event type maps to exactly one normalized action verb.
_EVENT_TYPE_ACTIONS: dict[AuditEventType, AuditAction] = {
    AuditEventType.INVENTORY_CREATED: AuditAction.CREATE,
    AuditEventType.INVENTORY_VALIDATED: AuditAction.VALIDATE,
    AuditEventType.ACCESS_REQUESTED: AuditAction.REQUEST,
    AuditEventType.ACCESS_EVALUATED: AuditAction.EVALUATE,
    AuditEventType.ACCESS_APPROVED: AuditAction.APPROVE,
    AuditEventType.ACCESS_REJECTED: AuditAction.REJECT,
    AuditEventType.GRANT_CREATED: AuditAction.CREATE,
    AuditEventType.GRANT_REVOKED: AuditAction.REVOKE,
    AuditEventType.GRANT_EXPIRED: AuditAction.EXPIRE,
}

_REQUEST_SCOPED_EVENT_TYPES = frozenset(
    {
        AuditEventType.ACCESS_REQUESTED,
        AuditEventType.ACCESS_EVALUATED,
        AuditEventType.ACCESS_APPROVED,
        AuditEventType.ACCESS_REJECTED,
    }
)
_DECISION_SCOPED_EVENT_TYPES = frozenset(
    {AuditEventType.ACCESS_APPROVED, AuditEventType.ACCESS_REJECTED}
)
_GRANT_SCOPED_EVENT_TYPES = frozenset(
    {AuditEventType.GRANT_CREATED, AuditEventType.GRANT_REVOKED, AuditEventType.GRANT_EXPIRED}
)
_INVENTORY_SCOPED_EVENT_TYPES = frozenset(
    {AuditEventType.INVENTORY_CREATED, AuditEventType.INVENTORY_VALIDATED}
)

#: Metadata is for small, non-sensitive contextual values only — this is a
#: best-effort structural guard, not a data-loss-prevention system.
_FORBIDDEN_METADATA_MARKERS = (
    "ssn",
    "social_security",
    "password",
    "secret",
    "api_key",
    "token",
    "mrn",
    "medical_record",
    "date_of_birth",
    "patient",
)


class AuditEvent(BaseModel):
    """One immutable, append-only record of a governance action."""

    model_config = {"frozen": True, "extra": "forbid"}

    event_id: str = Field(pattern=_EVENT_ID_PATTERN.pattern)
    event_type: AuditEventType
    occurred_at: datetime
    actor_id: str = Field(min_length=1)
    actor_type: ActorType
    entity_type: AuditEntityType
    entity_id: str = Field(min_length=1)
    action: AuditAction
    outcome: AuditOutcome
    reason: str | None = None
    correlation_id: str = Field(min_length=1)
    research_project_id: str | None = Field(
        default=None, pattern=_RESEARCH_PROJECT_ID_PATTERN.pattern
    )
    request_id: str | None = Field(default=None, pattern=_REQUEST_ID_PATTERN.pattern)
    decision_id: str | None = Field(default=None, pattern=_DECISION_ID_PATTERN.pattern)
    grant_id: str | None = Field(default=None, pattern=_GRANT_ID_PATTERN.pattern)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _entity_type_matches_event_type(self) -> AuditEvent:
        expected = _EVENT_TYPE_ENTITY_TYPES[self.event_type]
        if self.entity_type != expected:
            raise ValueError(
                f"event {self.event_id}: event_type={self.event_type.value} must have "
                f"entity_type={expected.value}, got {self.entity_type.value}"
            )
        return self

    @model_validator(mode="after")
    def _action_matches_event_type(self) -> AuditEvent:
        expected = _EVENT_TYPE_ACTIONS[self.event_type]
        if self.action != expected:
            raise ValueError(
                f"event {self.event_id}: event_type={self.event_type.value} must have "
                f"action={expected.value}, got {self.action.value}"
            )
        return self

    @model_validator(mode="after")
    def _scoped_identifiers_are_present(self) -> AuditEvent:
        if self.event_type in _REQUEST_SCOPED_EVENT_TYPES and self.request_id is None:
            raise ValueError(f"event {self.event_id}: {self.event_type.value} requires request_id")
        if self.event_type in _DECISION_SCOPED_EVENT_TYPES and self.decision_id is None:
            raise ValueError(f"event {self.event_id}: {self.event_type.value} requires decision_id")
        if self.event_type in _GRANT_SCOPED_EVENT_TYPES and self.grant_id is None:
            raise ValueError(f"event {self.event_id}: {self.event_type.value} requires grant_id")
        if self.event_type in _INVENTORY_SCOPED_EVENT_TYPES and (
            self.request_id is not None
            or self.decision_id is not None
            or self.grant_id is not None
            or self.research_project_id is not None
        ):
            raise ValueError(
                f"event {self.event_id}: {self.event_type.value} must not carry "
                f"request_id/decision_id/grant_id/research_project_id"
            )
        return self

    @model_validator(mode="after")
    def _metadata_contains_no_sensitive_markers(self) -> AuditEvent:
        for key, value in self.metadata.items():
            haystack = f"{key} {value}".lower()
            for marker in _FORBIDDEN_METADATA_MARKERS:
                if marker in haystack:
                    raise ValueError(
                        f"event {self.event_id}: metadata entry {key!r} looks like it may "
                        f"contain sensitive data (matched {marker!r}) — not permitted"
                    )
        return self
