"""Aggregate audit summary computed from an audit log.

Deliberately limited to counts and coverage indicators — no enterprise risk
score is produced here (see the root README's Explicit non-goals section).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel

from governance_platform.access import AccessControlPortfolio, DecisionType, GrantStatus
from governance_platform.audit.enums import AuditEntityType, AuditEventType, AuditOutcome
from governance_platform.audit.log import AuditLog

_E = TypeVar("_E", bound=Enum)


def _counts_by_enum(enum_cls: type[_E], values: Iterable[_E]) -> dict[str, int]:
    """Count occurrences of each ``enum_cls`` member, in enum definition order (0 if unused)."""
    tally = Counter(values)
    return {member.value: tally.get(member, 0) for member in enum_cls}


class AuditCoverage(BaseModel):
    """How much of the expected evidence is actually present — the summary view of
    :func:`~governance_platform.audit.completeness.check_completeness`'s underlying checks."""

    requests_total: int
    requests_with_evaluation_event: int
    rejected_requests_total: int
    rejected_requests_with_rejection_event: int
    grants_total: int
    grants_with_creation_event: int
    revoked_grants_total: int
    revoked_grants_with_revocation_event: int


class AuditSummary(BaseModel):
    """Aggregate governance information derived from an :class:`AuditLog`."""

    model_config = {"frozen": True}

    total_events: int
    events_by_type: dict[str, int]
    events_by_outcome: dict[str, int]
    events_by_entity_type: dict[str, int]
    events_by_research_project: dict[str, int]
    coverage: AuditCoverage


def build_audit_summary(audit_log: AuditLog, access_state: AccessControlPortfolio) -> AuditSummary:
    """Compute the aggregate audit summary for ``audit_log``."""
    events = audit_log.events

    events_by_research_project: dict[str, int] = {}
    for event in events:
        if event.research_project_id is not None:
            events_by_research_project[event.research_project_id] = (
                events_by_research_project.get(event.research_project_id, 0) + 1
            )

    rejected_requests = [
        r
        for r in access_state.requests
        if (decision := access_state.decision_for_request(r.request_id)) is not None
        and decision.decision == DecisionType.REJECTED
    ]
    revoked_grants = [g for g in access_state.grants if g.status == GrantStatus.REVOKED]

    coverage = AuditCoverage(
        requests_total=len(access_state.requests),
        requests_with_evaluation_event=sum(
            1
            for r in access_state.requests
            if any(
                e.event_type == AuditEventType.ACCESS_EVALUATED
                for e in audit_log.filter_by_request(r.request_id)
            )
        ),
        rejected_requests_total=len(rejected_requests),
        rejected_requests_with_rejection_event=sum(
            1
            for r in rejected_requests
            if any(
                e.event_type == AuditEventType.ACCESS_REJECTED
                for e in audit_log.filter_by_request(r.request_id)
            )
        ),
        grants_total=len(access_state.grants),
        grants_with_creation_event=sum(
            1
            for g in access_state.grants
            if any(
                e.event_type == AuditEventType.GRANT_CREATED
                for e in audit_log.filter_by_grant(g.grant_id)
            )
        ),
        revoked_grants_total=len(revoked_grants),
        revoked_grants_with_revocation_event=sum(
            1
            for g in revoked_grants
            if any(
                e.event_type == AuditEventType.GRANT_REVOKED
                for e in audit_log.filter_by_grant(g.grant_id)
            )
        ),
    )

    return AuditSummary(
        total_events=len(events),
        events_by_type=_counts_by_enum(AuditEventType, (e.event_type for e in events)),
        events_by_outcome=_counts_by_enum(AuditOutcome, (e.outcome for e in events)),
        events_by_entity_type=_counts_by_enum(AuditEntityType, (e.entity_type for e in events)),
        events_by_research_project=events_by_research_project,
        coverage=coverage,
    )
