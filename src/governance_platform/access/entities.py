"""Typed access-control entities: requests, approval decisions, and grants.

These model the workflow ``Access Request -> Policy Validation -> Approval
Decision -> Time-Bounded Grant -> Revocation / Expiry`` described in
``governance/access_review.md`` and ``governance/research_approval.md``. Each
entity is an immutable record of one step, not a mutable row that gets edited
in place — consistent with the audit trail described in
``governance/audit_evidence.md`` ("corrections are recorded as new events,
not edits to history"), even though no audit plane reads these yet.

Entity-level validation here only enforces invariants that hold in
isolation (e.g. a grant's ``expires_at`` must be after its ``granted_at``).
Whether a request is *eligible* — its referenced research project exists, is
approved, is linked to the requested datasets/models, etc. — depends on the
inventory and is evaluated by
:mod:`governance_platform.access.policy`, not here. This keeps these entities
constructible and testable without any dependency on the inventory plane.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from governance_platform.access.enums import DecisionType, GrantStatus, RequesterRole, RequestStatus

_REQUEST_ID_PATTERN = re.compile(r"^AR-\d{4}$")
_DECISION_ID_PATTERN = re.compile(r"^AD-\d{4}$")
_GRANT_ID_PATTERN = re.compile(r"^AG-\d{4}$")
_RESEARCH_PROJECT_ID_PATTERN = re.compile(r"^RP-\d{4}$")


class AccessRequest(BaseModel):
    """A request for time-bounded access to one or more datasets/models under a research project."""

    model_config = {"frozen": True, "extra": "forbid"}

    request_id: str = Field(pattern=_REQUEST_ID_PATTERN.pattern)
    requester_id: str = Field(min_length=1)
    requester_role: RequesterRole
    research_project_id: str = Field(pattern=_RESEARCH_PROJECT_ID_PATTERN.pattern)
    requested_dataset_ids: tuple[str, ...] = Field(default_factory=tuple)
    requested_model_ids: tuple[str, ...] = Field(default_factory=tuple)
    purpose: str = Field(min_length=1)
    requested_at: datetime
    requested_until: datetime
    status: RequestStatus = RequestStatus.SUBMITTED

    @model_validator(mode="after")
    def _requests_something(self) -> AccessRequest:
        if not self.requested_dataset_ids and not self.requested_model_ids:
            raise ValueError(
                f"request {self.request_id}: must request at least one dataset or model"
            )
        return self

    @model_validator(mode="after")
    def _requested_until_after_requested_at(self) -> AccessRequest:
        if self.requested_until <= self.requested_at:
            raise ValueError(
                f"request {self.request_id}: requested_until ({self.requested_until}) "
                f"must be after requested_at ({self.requested_at})"
            )
        return self


class ApprovalDecision(BaseModel):
    """An immutable record of an approval or rejection decision for one :class:`AccessRequest`."""

    model_config = {"frozen": True, "extra": "forbid"}

    decision_id: str = Field(pattern=_DECISION_ID_PATTERN.pattern)
    request_id: str = Field(pattern=_REQUEST_ID_PATTERN.pattern)
    approver_id: str = Field(min_length=1)
    decision: DecisionType
    decision_reason: str = Field(min_length=1)
    decided_at: datetime


class AccessGrant(BaseModel):
    """A time-bounded grant of access, created only from an approved :class:`ApprovalDecision`."""

    model_config = {"frozen": True, "extra": "forbid"}

    grant_id: str = Field(pattern=_GRANT_ID_PATTERN.pattern)
    request_id: str = Field(pattern=_REQUEST_ID_PATTERN.pattern)
    research_project_id: str = Field(pattern=_RESEARCH_PROJECT_ID_PATTERN.pattern)
    requester_id: str = Field(min_length=1)
    dataset_ids: tuple[str, ...] = Field(default_factory=tuple)
    model_ids: tuple[str, ...] = Field(default_factory=tuple)
    granted_at: datetime
    expires_at: datetime
    status: GrantStatus = GrantStatus.ISSUED
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    @model_validator(mode="after")
    def _time_bounded(self) -> AccessGrant:
        if self.expires_at <= self.granted_at:
            raise ValueError(
                f"grant {self.grant_id}: expires_at ({self.expires_at}) must be after "
                f"granted_at ({self.granted_at}) — grants must be time-bounded"
            )
        return self

    @model_validator(mode="after")
    def _revocation_fields_are_consistent(self) -> AccessGrant:
        if self.status == GrantStatus.REVOKED:
            if self.revoked_at is None or self.revocation_reason is None:
                raise ValueError(
                    f"grant {self.grant_id}: status=revoked requires both revoked_at "
                    f"and revocation_reason to be set"
                )
            if self.revoked_at < self.granted_at:
                raise ValueError(
                    f"grant {self.grant_id}: revoked_at ({self.revoked_at}) is before "
                    f"granted_at ({self.granted_at})"
                )
        elif self.revoked_at is not None or self.revocation_reason is not None:
            raise ValueError(
                f"grant {self.grant_id}: revoked_at/revocation_reason must only be set "
                f"when status=revoked"
            )
        return self
