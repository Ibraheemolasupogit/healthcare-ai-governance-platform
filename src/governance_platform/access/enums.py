"""Enumerations shared by the access/research-control plane's typed entities."""

from __future__ import annotations

from enum import Enum


class RequesterRole(str, Enum):
    """The fictional, role-based capacity in which a requester is asking for access."""

    PRINCIPAL_INVESTIGATOR = "principal_investigator"
    RESEARCHER = "researcher"
    DATA_ANALYST = "data_analyst"
    MODEL_DEVELOPER = "model_developer"


class RequestStatus(str, Enum):
    """An access request's finalized outcome.

    ``SUBMITTED`` is the only status a request can have immediately after
    :meth:`~governance_platform.access.service.AccessControlService.submit_request`
    — it is filed but not yet decided. ``APPROVED``/``REJECTED`` are set once
    :meth:`~governance_platform.access.service.AccessControlService.decide`
    finalizes the request to match its :class:`ApprovalDecision`.
    """

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionType(str, Enum):
    """The outcome recorded by an :class:`~governance_platform.access.entities.ApprovalDecision`."""

    APPROVED = "approved"
    REJECTED = "rejected"


class GrantStatus(str, Enum):
    """A grant's stored *administrative* state — independent of the clock.

    This deliberately does not include an "expired" member: whether a grant
    is currently active is always a function of an explicitly supplied
    evaluation time against ``granted_at``/``expires_at`` (see
    :meth:`~governance_platform.access.service.AccessControlService.is_grant_active`),
    never a stored label that could silently go stale.
    """

    ISSUED = "issued"
    REVOKED = "revoked"


class RejectionReasonCode(str, Enum):
    """A structured, explainable reason an access request failed eligibility."""

    UNKNOWN_RESEARCH_PROJECT = "unknown_research_project"
    RESEARCH_PROJECT_NOT_APPROVED = "research_project_not_approved"
    RESEARCH_PROJECT_EXPIRED = "research_project_expired"
    UNKNOWN_DATASET = "unknown_dataset"
    UNKNOWN_MODEL = "unknown_model"
    DATASET_NOT_LINKED_TO_PROJECT = "dataset_not_linked_to_project"
    MODEL_NOT_LINKED_TO_PROJECT = "model_not_linked_to_project"
    RESEARCH_USE_NOT_ALLOWED = "research_use_not_allowed"
    DATASET_NOT_APPROVED = "dataset_not_approved"
    MODEL_NOT_APPROVED = "model_not_approved"
    REQUESTED_DURATION_EXCEEDS_PROJECT_EXPIRY = "requested_duration_exceeds_project_expiry"
