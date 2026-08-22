"""Aggregate access-review summary computed from an access-control state.

Deliberately limited to counts and breakdowns — no enterprise risk score is
produced here (see the root README's Explicit non-goals section).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel

from governance_platform.access.enums import DecisionType, RejectionReasonCode, RequestStatus
from governance_platform.access.policy import evaluate_eligibility
from governance_platform.access.portfolio import AccessControlPortfolio
from governance_platform.access.service import AccessControlService
from governance_platform.inventory import InventoryPortfolio

_E = TypeVar("_E", bound=Enum)


def _counts_by_enum(enum_cls: type[_E], values: Iterable[_E]) -> dict[str, int]:
    """Count occurrences of each ``enum_cls`` member, in enum definition order.

    Every member appears in the result (with a count of 0 if unused), so the
    summary has a complete, stable shape rather than only listing whichever
    values happen to occur in the current state.
    """
    tally = Counter(values)
    return {member.value: tally.get(member, 0) for member in enum_cls}


class GrantStatusCounts(BaseModel):
    """Grant status as of the summary's ``evaluated_at`` instant."""

    active: int
    expired: int
    revoked: int


class AccessReviewSummary(BaseModel):
    """Aggregate governance information derived from an :class:`AccessControlPortfolio`."""

    model_config = {"frozen": True}

    evaluated_at: datetime
    total_requests: int
    request_status: dict[str, int]
    decision_type: dict[str, int]
    grant_status: GrantStatusCounts
    rejection_reason_categories: dict[str, int]


def build_access_summary(
    state: AccessControlPortfolio,
    inventory: InventoryPortfolio,
    *,
    evaluated_at: datetime,
) -> AccessReviewSummary:
    """Compute the aggregate access-review summary for ``state``.

    ``evaluated_at`` is the explicit instant grants are evaluated as active/
    expired against (see
    :meth:`~governance_platform.access.service.AccessControlService.is_grant_active`)
    — never the wall-clock "now". Rejection reason categories are recovered by
    re-running :func:`~governance_platform.access.policy.evaluate_eligibility`
    for each rejected request against ``inventory``, the same deterministic
    check already used to produce the recorded decision.
    """
    active = 0
    expired = 0
    revoked = 0
    for grant in state.grants:
        if AccessControlService.is_grant_active(grant, evaluated_at):
            active += 1
        elif grant.status.value == "revoked":
            revoked += 1
        else:
            expired += 1

    rejection_reason_categories = {code.value: 0 for code in RejectionReasonCode}
    for decision in state.decisions:
        if decision.decision != DecisionType.REJECTED:
            continue
        request = state.request_by_id(decision.request_id)
        eligibility = evaluate_eligibility(request, inventory)
        for violation in eligibility.violations:
            rejection_reason_categories[violation.code.value] += 1

    return AccessReviewSummary(
        evaluated_at=evaluated_at,
        total_requests=len(state.requests),
        request_status=_counts_by_enum(RequestStatus, (r.status for r in state.requests)),
        decision_type=_counts_by_enum(DecisionType, (d.decision for d in state.decisions)),
        grant_status=GrantStatusCounts(active=active, expired=expired, revoked=revoked),
        rejection_reason_categories=rejection_reason_categories,
    )
