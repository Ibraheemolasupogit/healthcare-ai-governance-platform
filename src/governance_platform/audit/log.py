"""The append-only audit log.

Mirrors the inventory/access planes' portfolio containers: a frozen pydantic
model holding a tuple of events, with cross-event invariants (uniqueness,
timestamp ordering) enforced by validators rather than caller discipline.
There is no update/remove method on the public API — the only way to add an
event is :meth:`AuditLog.append`, which returns a **new** ``AuditLog``
rather than mutating the existing one, so a reference to a previously
observed log is never silently changed out from under its holder.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import BaseModel, model_validator

from governance_platform.audit.entities import AuditEvent
from governance_platform.audit.enums import AuditEventType


class AuditLog(BaseModel):
    """An append-only, internally-consistent sequence of audit events."""

    model_config = {"frozen": True, "extra": "forbid"}

    events: tuple[AuditEvent, ...] = ()

    @model_validator(mode="after")
    def _unique_event_ids(self) -> AuditLog:
        duplicates = sorted(
            {
                event_id
                for event_id, count in Counter(e.event_id for e in self.events).items()
                if count > 1
            }
        )
        if duplicates:
            raise ValueError(f"duplicate event_id values found: {duplicates}")
        return self

    @model_validator(mode="after")
    def _timestamps_are_non_decreasing_within_each_correlation_group(self) -> AuditLog:
        last_seen: dict[str, tuple[str, object]] = {}
        for event in self.events:
            previous = last_seen.get(event.correlation_id)
            if previous is not None:
                previous_event_id, previous_occurred_at = previous
                if event.occurred_at < previous_occurred_at:
                    raise ValueError(
                        f"event {event.event_id} (occurred_at={event.occurred_at}) is "
                        f"recorded after but timestamped before event {previous_event_id} "
                        f"(occurred_at={previous_occurred_at}) in correlation group "
                        f"{event.correlation_id!r} — timestamps within one governance "
                        f"activity must not go backwards"
                    )
            last_seen[event.correlation_id] = (event.event_id, event.occurred_at)
        return self

    def append(self, event: AuditEvent) -> AuditLog:
        """Return a new ``AuditLog`` with ``event`` appended.

        Never mutates this log — appending re-validates uniqueness and
        timestamp ordering against the full resulting sequence.
        """
        return AuditLog(events=(*self.events, event))

    def events_in_order(self) -> tuple[AuditEvent, ...]:
        """All events in deterministic chronological order (``occurred_at``, then ``event_id``)."""
        return tuple(sorted(self.events, key=lambda e: (e.occurred_at, e.event_id)))

    def filter_by_entity_id(self, entity_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self.events_in_order() if e.entity_id == entity_id)

    def filter_by_research_project(self, research_project_id: str) -> tuple[AuditEvent, ...]:
        return tuple(
            e for e in self.events_in_order() if e.research_project_id == research_project_id
        )

    def filter_by_request(self, request_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self.events_in_order() if e.request_id == request_id)

    def filter_by_grant(self, grant_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self.events_in_order() if e.grant_id == grant_id)

    def filter_by_event_type(self, event_type: AuditEventType) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self.events_in_order() if e.event_type == event_type)

    def filter_by_correlation_id(self, correlation_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self.events_in_order() if e.correlation_id == correlation_id)

    def correlation_groups(self) -> dict[str, tuple[AuditEvent, ...]]:
        """All events grouped by ``correlation_id``, each group in chronological order."""
        grouped: dict[str, list[AuditEvent]] = defaultdict(list)
        for event in self.events_in_order():
            grouped[event.correlation_id].append(event)
        return {correlation_id: tuple(events) for correlation_id, events in grouped.items()}
