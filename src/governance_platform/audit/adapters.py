"""Audit-event adapters: translate existing inventory/access records into audit events.

These are pure functions over already-produced
:class:`~governance_platform.inventory.InventoryPortfolio`,
:class:`~governance_platform.access.AccessRequest`,
:class:`~governance_platform.access.ApprovalDecision`, and
:class:`~governance_platform.access.AccessGrant` objects — nothing here calls
into or wraps :class:`~governance_platform.access.AccessControlService`.
That keeps the access-control plane's own service and tests completely
unaware of the audit plane, and lets audit-event construction be unit tested
against hand-built records without running a full scenario.

Every ``event_id``/``correlation_id`` is supplied by the caller (typically
:mod:`governance_platform.audit.generation`, which assigns them
deterministically in scenario order) rather than generated here — these
adapters do not invent identifiers.
"""

from __future__ import annotations

from datetime import datetime

from governance_platform.access import (
    AccessControlService,
    AccessGrant,
    AccessRequest,
    ApprovalDecision,
    DecisionType,
)
from governance_platform.audit.entities import AuditEvent
from governance_platform.audit.enums import (
    ActorType,
    AuditAction,
    AuditEntityType,
    AuditEventType,
    AuditOutcome,
)
from governance_platform.inventory import InventoryPortfolio

#: A fixed marker identifying the single synthetic inventory portfolio this
#: platform generates — there is one inventory, so one entity_id for it.
INVENTORY_ENTITY_ID = "INVENTORY-PORTFOLIO"

#: A fixed correlation group for the two inventory-plane events — they are
#: both part of one "establish and validate the inventory" activity.
INVENTORY_CORRELATION_ID = "CORR-INVENTORY-0001"

_SYSTEM_INVENTORY_GENERATOR = "system-inventory-generator"
_SYSTEM_POLICY_ENGINE = "system-policy-engine"
_SYSTEM_ACCESS_CONTROL_SERVICE = "system-access-control-service"
_SYSTEM_AUDIT_EVIDENCE_GENERATOR = "system-audit-evidence-generator"


def request_correlation_id(request_id: str) -> str:
    """The deterministic correlation id shared by one request's whole lifecycle.

    Derived from ``request_id`` (not randomly generated) so every event tied
    to the same request — its submission, evaluation, decision, and any
    grant/revocation/expiry that follows — is discoverable as one activity.
    """
    return f"CORR-{request_id}"


def inventory_created_event(
    event_id: str, inventory: InventoryPortfolio, *, occurred_at: datetime
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.INVENTORY_CREATED,
        occurred_at=occurred_at,
        actor_id=_SYSTEM_INVENTORY_GENERATOR,
        actor_type=ActorType.SYSTEM,
        entity_type=AuditEntityType.INVENTORY,
        entity_id=INVENTORY_ENTITY_ID,
        action=AuditAction.CREATE,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=INVENTORY_CORRELATION_ID,
        metadata={
            "dataset_count": str(len(inventory.datasets)),
            "model_count": str(len(inventory.models)),
            "research_project_count": str(len(inventory.research_projects)),
        },
    )


def inventory_validated_event(event_id: str, *, occurred_at: datetime) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.INVENTORY_VALIDATED,
        occurred_at=occurred_at,
        actor_id=_SYSTEM_INVENTORY_GENERATOR,
        actor_type=ActorType.SYSTEM,
        entity_type=AuditEntityType.INVENTORY,
        entity_id=INVENTORY_ENTITY_ID,
        action=AuditAction.VALIDATE,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=INVENTORY_CORRELATION_ID,
    )


def access_requested_event(event_id: str, request: AccessRequest) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.ACCESS_REQUESTED,
        occurred_at=request.requested_at,
        actor_id=request.requester_id,
        actor_type=ActorType.RESEARCHER,
        entity_type=AuditEntityType.ACCESS_REQUEST,
        entity_id=request.request_id,
        action=AuditAction.REQUEST,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=request_correlation_id(request.request_id),
        research_project_id=request.research_project_id,
        request_id=request.request_id,
        metadata={"requester_role": request.requester_role.value},
    )


def access_evaluated_event(
    event_id: str, request: AccessRequest, decision: ApprovalDecision
) -> AuditEvent:
    eligible = decision.decision == DecisionType.APPROVED
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.ACCESS_EVALUATED,
        occurred_at=decision.decided_at,
        actor_id=_SYSTEM_POLICY_ENGINE,
        actor_type=ActorType.SYSTEM,
        entity_type=AuditEntityType.ACCESS_REQUEST,
        entity_id=request.request_id,
        action=AuditAction.EVALUATE,
        outcome=AuditOutcome.SUCCESS if eligible else AuditOutcome.DENIED,
        reason=None if eligible else decision.decision_reason,
        correlation_id=request_correlation_id(request.request_id),
        research_project_id=request.research_project_id,
        request_id=request.request_id,
    )


def access_decision_event(
    event_id: str, request: AccessRequest, decision: ApprovalDecision
) -> AuditEvent:
    approved = decision.decision == DecisionType.APPROVED
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.ACCESS_APPROVED if approved else AuditEventType.ACCESS_REJECTED,
        occurred_at=decision.decided_at,
        actor_id=decision.approver_id,
        actor_type=ActorType.APPROVER,
        entity_type=AuditEntityType.ACCESS_REQUEST,
        entity_id=request.request_id,
        action=AuditAction.APPROVE if approved else AuditAction.REJECT,
        outcome=AuditOutcome.SUCCESS if approved else AuditOutcome.DENIED,
        reason=None if approved else decision.decision_reason,
        correlation_id=request_correlation_id(request.request_id),
        research_project_id=request.research_project_id,
        request_id=request.request_id,
        decision_id=decision.decision_id,
    )


def grant_created_event(
    event_id: str, grant: AccessGrant, decision: ApprovalDecision
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.GRANT_CREATED,
        occurred_at=grant.granted_at,
        actor_id=decision.approver_id,
        actor_type=ActorType.APPROVER,
        entity_type=AuditEntityType.ACCESS_GRANT,
        entity_id=grant.grant_id,
        action=AuditAction.CREATE,
        outcome=AuditOutcome.SUCCESS,
        correlation_id=request_correlation_id(grant.request_id),
        research_project_id=grant.research_project_id,
        request_id=grant.request_id,
        decision_id=decision.decision_id,
        grant_id=grant.grant_id,
        metadata={
            "dataset_count": str(len(grant.dataset_ids)),
            "model_count": str(len(grant.model_ids)),
        },
    )


def grant_revoked_event(
    event_id: str, grant: AccessGrant, decision: ApprovalDecision
) -> AuditEvent:
    if grant.revoked_at is None or grant.revocation_reason is None:
        raise ValueError(f"grant {grant.grant_id} is not revoked — no revocation to record")
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.GRANT_REVOKED,
        occurred_at=grant.revoked_at,
        # AccessGrant does not record who performed the revocation (a
        # Milestone 3 entity limitation this plane does not redesign), so
        # the revocation is honestly attributed to the system rather than
        # guessing an approver identity.
        actor_id=_SYSTEM_ACCESS_CONTROL_SERVICE,
        actor_type=ActorType.SYSTEM,
        entity_type=AuditEntityType.ACCESS_GRANT,
        entity_id=grant.grant_id,
        action=AuditAction.REVOKE,
        outcome=AuditOutcome.REVOKED,
        reason=grant.revocation_reason,
        correlation_id=request_correlation_id(grant.request_id),
        research_project_id=grant.research_project_id,
        request_id=grant.request_id,
        decision_id=decision.decision_id,
        grant_id=grant.grant_id,
    )


def grant_expired_event(event_id: str, grant: AccessGrant, *, evaluated_at: datetime) -> AuditEvent:
    if AccessControlService.is_grant_active(grant, evaluated_at):
        raise ValueError(f"grant {grant.grant_id} is still active as of {evaluated_at}")
    if grant.status.value == "revoked":
        raise ValueError(f"grant {grant.grant_id} was revoked, not expired")
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.GRANT_EXPIRED,
        # Expiry is a passive fact of the clock, not a moment the grant
        # itself records — dated to when this evidence run observed it.
        occurred_at=evaluated_at,
        actor_id=_SYSTEM_AUDIT_EVIDENCE_GENERATOR,
        actor_type=ActorType.SYSTEM,
        entity_type=AuditEntityType.ACCESS_GRANT,
        entity_id=grant.grant_id,
        action=AuditAction.EXPIRE,
        outcome=AuditOutcome.EXPIRED,
        correlation_id=request_correlation_id(grant.request_id),
        research_project_id=grant.research_project_id,
        request_id=grant.request_id,
        grant_id=grant.grant_id,
    )
