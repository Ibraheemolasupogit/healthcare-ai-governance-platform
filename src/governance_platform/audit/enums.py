"""Enumerations for the audit/evidence plane's typed audit event."""

from __future__ import annotations

from enum import Enum


class ActorType(str, Enum):
    """The kind of actor that performed (or is attributed to) an audited action."""

    RESEARCHER = "researcher"
    APPROVER = "approver"
    SYSTEM = "system"


class AuditEntityType(str, Enum):
    """The kind of primary entity an audit event concerns."""

    INVENTORY = "inventory"
    ACCESS_REQUEST = "access_request"
    ACCESS_GRANT = "access_grant"


class AuditAction(str, Enum):
    """A normalized verb classification, shared across event types where meaningful.

    E.g. both ``inventory_created`` and ``grant_created`` events carry
    ``action=create`` — the entity type they act on differs, but "an entity
    was created" is a query worth answering across the whole audit log.
    """

    CREATE = "create"
    VALIDATE = "validate"
    REQUEST = "request"
    EVALUATE = "evaluate"
    APPROVE = "approve"
    REJECT = "reject"
    REVOKE = "revoke"
    EXPIRE = "expire"


class AuditEventType(str, Enum):
    """The restrained taxonomy of governance events this plane records.

    Limited to actions the inventory and access planes actually perform —
    see the root README's Explicit non-goals section for what is
    deliberately not represented (e.g. model deployment, live policy
    enforcement, security incidents).
    """

    INVENTORY_CREATED = "inventory_created"
    INVENTORY_VALIDATED = "inventory_validated"
    ACCESS_REQUESTED = "access_requested"
    ACCESS_EVALUATED = "access_evaluated"
    ACCESS_APPROVED = "access_approved"
    ACCESS_REJECTED = "access_rejected"
    GRANT_CREATED = "grant_created"
    GRANT_REVOKED = "grant_revoked"
    GRANT_EXPIRED = "grant_expired"


class AuditOutcome(str, Enum):
    """The governance-relevant result of the audited action."""

    SUCCESS = "success"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"
