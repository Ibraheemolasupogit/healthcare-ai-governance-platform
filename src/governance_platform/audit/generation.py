"""Deterministic audit-log generation from the existing inventory and access scenarios.

This does **not** create a separate synthetic universe: it takes the exact
:class:`~governance_platform.inventory.InventoryPortfolio` and
:class:`~governance_platform.access.AccessControlPortfolio` produced by the
Milestone 2/3 generators (or any equivalent state, e.g. reloaded from disk)
and translates them into an :class:`~governance_platform.audit.log.AuditLog`
via the pure adapter functions in :mod:`governance_platform.audit.adapters`.
``event_id``s are assigned sequentially in a fixed, deterministic order
(inventory events first, then each request's lifecycle in ``request_id``
order, then each grant's lifecycle in ``grant_id`` order), so re-running this
against the same inputs and the same ``evaluated_at`` always produces a
byte-identical log.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from governance_platform.access import AccessControlPortfolio, AccessControlService
from governance_platform.audit import adapters
from governance_platform.audit.log import AuditLog
from governance_platform.inventory import InventoryPortfolio

#: A fixed, synthetic "inventory established" instant — chosen to sit before
#: every Milestone 3 access scenario's earliest timestamp, not derived from
#: any real generation wall-clock.
INVENTORY_CREATED_AT = datetime(2024, 1, 1)
INVENTORY_VALIDATED_AT = INVENTORY_CREATED_AT + timedelta(seconds=1)


def generate_audit_log(
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
    *,
    evaluated_at: datetime,
) -> AuditLog:
    """Build the deterministic audit log for ``inventory`` and ``access_state``.

    ``evaluated_at`` is the same explicit reference instant used to evaluate
    grant activity elsewhere (see
    ``governance_platform.access.REFERENCE_EVALUATION_TIME``) — it decides
    which issued-but-not-revoked grants get a ``grant_expired`` event.
    """
    log = AuditLog()
    next_sequence = 1

    def next_event_id() -> str:
        nonlocal next_sequence
        event_id = f"AE-{next_sequence:04d}"
        next_sequence += 1
        return event_id

    log = log.append(
        adapters.inventory_created_event(
            next_event_id(), inventory, occurred_at=INVENTORY_CREATED_AT
        )
    )
    log = log.append(
        adapters.inventory_validated_event(next_event_id(), occurred_at=INVENTORY_VALIDATED_AT)
    )

    for request in sorted(access_state.requests, key=lambda r: r.request_id):
        decision = access_state.decision_for_request(request.request_id)
        log = log.append(adapters.access_requested_event(next_event_id(), request))
        if decision is None:
            continue
        log = log.append(adapters.access_evaluated_event(next_event_id(), request, decision))
        log = log.append(adapters.access_decision_event(next_event_id(), request, decision))

    for grant in sorted(access_state.grants, key=lambda g: g.grant_id):
        decision = access_state.decision_for_request(grant.request_id)
        if decision is None:
            continue
        log = log.append(adapters.grant_created_event(next_event_id(), grant, decision))
        if grant.status.value == "revoked":
            log = log.append(adapters.grant_revoked_event(next_event_id(), grant, decision))
        elif not AccessControlService.is_grant_active(grant, evaluated_at):
            log = log.append(
                adapters.grant_expired_event(next_event_id(), grant, evaluated_at=evaluated_at)
            )

    return log
