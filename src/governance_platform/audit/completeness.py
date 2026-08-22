"""Audit-evidence completeness checks.

This is **evidence completeness validation, not a generic policy engine**:
it answers "is the audit log missing evidence we would expect it to have,
given what the inventory and access-control state actually contain?" — not
"was the governed activity itself correct" (that is
:mod:`governance_platform.access.policy`'s job). Each check returns a plain,
human-readable problem string; an empty list means the audit log is complete
with respect to the source-of-truth state passed in.
"""

from __future__ import annotations

from governance_platform.access import AccessControlPortfolio, DecisionType, GrantStatus
from governance_platform.audit.enums import AuditEventType
from governance_platform.audit.log import AuditLog
from governance_platform.inventory import InventoryPortfolio

#: A request/evaluation/rejection event may legitimately carry a
#: research_project_id that does not resolve — e.g. a request rejected
#: specifically *because* it named an unknown project. The audit trail is
#: correctly preserving what was claimed, not asserting it was valid. Only
#: events that could only exist once a project was validated (approval,
#: grant lifecycle) are expected to always resolve.
_PROJECT_MUST_RESOLVE_EVENT_TYPES = frozenset(
    {
        AuditEventType.ACCESS_APPROVED,
        AuditEventType.GRANT_CREATED,
        AuditEventType.GRANT_REVOKED,
        AuditEventType.GRANT_EXPIRED,
    }
)


def check_completeness(
    audit_log: AuditLog,
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
) -> list[str]:
    """Return every evidence-completeness problem found; an empty list means the log is complete."""
    problems: list[str] = []

    event_ids = [e.event_id for e in audit_log.events]
    if len(event_ids) != len(set(event_ids)):
        problems.append("audit log contains duplicate event_id values")

    known_request_ids = {r.request_id for r in access_state.requests}
    known_decision_ids = {d.decision_id for d in access_state.decisions}
    known_grant_ids = {g.grant_id for g in access_state.grants}
    known_project_ids = {p.research_project_id for p in inventory.research_projects}

    for event in audit_log.events:
        if event.request_id is not None and event.request_id not in known_request_ids:
            problems.append(
                f"event {event.event_id} references unknown request_id: {event.request_id}"
            )
        if event.decision_id is not None and event.decision_id not in known_decision_ids:
            problems.append(
                f"event {event.event_id} references unknown decision_id: {event.decision_id}"
            )
        if event.grant_id is not None and event.grant_id not in known_grant_ids:
            problems.append(f"event {event.event_id} references unknown grant_id: {event.grant_id}")
        if (
            event.event_type in _PROJECT_MUST_RESOLVE_EVENT_TYPES
            and event.research_project_id is not None
            and event.research_project_id not in known_project_ids
        ):
            problems.append(
                f"event {event.event_id} references unknown research_project_id: "
                f"{event.research_project_id}"
            )

    for request in access_state.requests:
        evaluated = audit_log.filter_by_request(request.request_id)
        if not any(e.event_type == AuditEventType.ACCESS_EVALUATED for e in evaluated):
            problems.append(f"request {request.request_id} has no access_evaluated event")

        decision = access_state.decision_for_request(request.request_id)
        rejected = decision is not None and decision.decision == DecisionType.REJECTED
        if rejected and not any(e.event_type == AuditEventType.ACCESS_REJECTED for e in evaluated):
            problems.append(f"rejected request {request.request_id} has no access_rejected event")

    for grant in access_state.grants:
        grant_events = audit_log.filter_by_grant(grant.grant_id)
        if not any(e.event_type == AuditEventType.GRANT_CREATED for e in grant_events):
            problems.append(f"grant {grant.grant_id} has no grant_created event")

        if grant.status == GrantStatus.REVOKED and not any(
            e.event_type == AuditEventType.GRANT_REVOKED for e in grant_events
        ):
            problems.append(f"revoked grant {grant.grant_id} has no grant_revoked event")

    return problems
