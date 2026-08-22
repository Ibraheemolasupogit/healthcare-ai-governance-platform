"""The access-control service: request -> decision -> grant -> revocation/expiry.

This is a **local governance simulation**: it evaluates the deterministic
rules in :mod:`governance_platform.access.policy` against an in-memory
:class:`~governance_platform.inventory.InventoryPortfolio` snapshot and
produces immutable :class:`~governance_platform.access.entities.AccessRequest`,
:class:`~governance_platform.access.entities.ApprovalDecision`, and
:class:`~governance_platform.access.entities.AccessGrant` records. It does
not authenticate anyone, does not call out to Snowflake, Entra ID, or any
other identity system, and does not enforce access to anything — see the
root README's Explicit non-goals section.

Every timestamp this service acts on (``requested_at``, ``decided_at``,
``granted_at``, ``expires_at``, the evaluation instant passed to
:meth:`AccessControlService.is_grant_active`) is supplied explicitly by the
caller. Nothing here reads the system clock, so evaluation is reproducible
regardless of when it runs.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from governance_platform.access.entities import AccessGrant, AccessRequest, ApprovalDecision
from governance_platform.access.enums import DecisionType, GrantStatus, RequesterRole, RequestStatus
from governance_platform.access.policy import EligibilityResult, evaluate_eligibility
from governance_platform.inventory import InventoryPortfolio


def _reason_summary(eligibility: EligibilityResult) -> str:
    if eligibility.eligible:
        return "All governance eligibility checks passed."
    return "; ".join(violation.detail for violation in eligibility.violations)


class AccessControlService:
    """Evaluates and records access requests against a fixed inventory snapshot."""

    def __init__(self, inventory: InventoryPortfolio) -> None:
        self._inventory = inventory

    def submit_request(
        self,
        *,
        request_id: str,
        requester_id: str,
        requester_role: RequesterRole,
        research_project_id: str,
        purpose: str,
        requested_at: datetime,
        requested_until: datetime,
        requested_dataset_ids: tuple[str, ...] = (),
        requested_model_ids: tuple[str, ...] = (),
    ) -> AccessRequest:
        """Create a new, freshly-submitted :class:`AccessRequest`.

        Does not evaluate eligibility — call :meth:`evaluate_eligibility` or
        :meth:`decide` for that. Raises ``pydantic.ValidationError`` if the
        request itself is malformed (e.g. ``requested_until`` before
        ``requested_at``).
        """
        return AccessRequest(
            request_id=request_id,
            requester_id=requester_id,
            requester_role=requester_role,
            research_project_id=research_project_id,
            requested_dataset_ids=requested_dataset_ids,
            requested_model_ids=requested_model_ids,
            purpose=purpose,
            requested_at=requested_at,
            requested_until=requested_until,
            status=RequestStatus.SUBMITTED,
        )

    def evaluate_eligibility(self, request: AccessRequest) -> EligibilityResult:
        """Evaluate ``request`` against this service's inventory snapshot."""
        return evaluate_eligibility(request, self._inventory)

    def decide(
        self,
        request: AccessRequest,
        *,
        decision_id: str,
        approver_id: str,
        decided_at: datetime,
    ) -> tuple[AccessRequest, ApprovalDecision]:
        """Evaluate ``request``, record an :class:`ApprovalDecision`, and finalize its status.

        Returns ``(finalized_request, decision)`` — ``finalized_request`` is a
        new :class:`AccessRequest` with ``status`` set to match the decision
        (``request`` itself is left untouched, since it is frozen). The
        decision's ``decision_reason`` is derived from the eligibility
        evaluation's violations, so a rejection is always explainable.
        """
        eligibility = self.evaluate_eligibility(request)
        decision_type = DecisionType.APPROVED if eligibility.eligible else DecisionType.REJECTED

        decision = ApprovalDecision(
            decision_id=decision_id,
            request_id=request.request_id,
            approver_id=approver_id,
            decision=decision_type,
            decision_reason=_reason_summary(eligibility),
            decided_at=decided_at,
        )

        finalized_status = (
            RequestStatus.APPROVED if eligibility.eligible else RequestStatus.REJECTED
        )
        finalized_request = AccessRequest(
            **{**request.model_dump(mode="python"), "status": finalized_status}
        )
        return finalized_request, decision

    def create_grant(
        self,
        request: AccessRequest,
        decision: ApprovalDecision,
        *,
        grant_id: str,
        granted_at: datetime,
        expires_at: datetime,
    ) -> AccessGrant:
        """Create a time-bounded :class:`AccessGrant` from an approved decision.

        Raises ``ValueError`` if ``decision`` does not correspond to
        ``request`` or was not an approval — a rejected or unrelated decision
        can never produce a grant.
        """
        if decision.request_id != request.request_id:
            raise ValueError(
                f"decision {decision.decision_id} does not correspond to "
                f"request {request.request_id}"
            )
        if decision.decision != DecisionType.APPROVED:
            raise ValueError(
                f"cannot create a grant from a {decision.decision.value} decision "
                f"(request {request.request_id})"
            )

        return AccessGrant(
            grant_id=grant_id,
            request_id=request.request_id,
            research_project_id=request.research_project_id,
            requester_id=request.requester_id,
            dataset_ids=request.requested_dataset_ids,
            model_ids=request.requested_model_ids,
            granted_at=granted_at,
            expires_at=expires_at,
            status=GrantStatus.ISSUED,
        )

    @staticmethod
    def is_grant_active(grant: AccessGrant, at: datetime) -> bool:
        """Whether ``grant`` is active at the explicitly supplied instant ``at``.

        A grant is active only if it has not been revoked and ``at`` falls
        within ``[granted_at, expires_at]`` — revoked and time-expired grants
        are both inactive (rule 12).
        """
        return grant.status != GrantStatus.REVOKED and grant.granted_at <= at <= grant.expires_at

    @staticmethod
    def revoke_grant(
        grant: AccessGrant, *, revoked_at: datetime, revocation_reason: str
    ) -> AccessGrant:
        """Return a new, revoked copy of ``grant`` (``grant`` itself is left untouched).

        Raises ``ValueError`` if ``grant`` is already revoked.
        """
        if grant.status == GrantStatus.REVOKED:
            raise ValueError(f"grant {grant.grant_id} is already revoked")

        return AccessGrant(
            **{
                **grant.model_dump(mode="python"),
                "status": GrantStatus.REVOKED,
                "revoked_at": revoked_at,
                "revocation_reason": revocation_reason,
            }
        )

    @staticmethod
    def expired_grants(grants: Iterable[AccessGrant], at: datetime) -> list[AccessGrant]:
        """Grants that are not revoked but whose ``expires_at`` has passed as of ``at``."""
        return [g for g in grants if g.status != GrantStatus.REVOKED and at > g.expires_at]
