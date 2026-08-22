"""The access-control state: a validated collection of requests, decisions, and grants.

Mirrors ``governance_platform.inventory.portfolio.InventoryPortfolio``: this is
where cross-entity referential integrity *within the access plane* is
enforced (duplicate IDs, decisions/grants referencing unknown requests, a
grant existing for a request that was never approved). Whether a request was
*correctly* approved against the inventory (project exists, is approved,
datasets are linked, etc.) is a policy question evaluated by
:mod:`governance_platform.access.policy` before a decision is recorded —
by the time a decision/grant lands in this portfolio, that call has already
been made. Keeping this portfolio's own validation independent of the
inventory keeps the access plane's core entities cheap to construct and test
in isolation, per the "minimal coupling to the inventory layer" goal.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, model_validator

from governance_platform.access.entities import AccessGrant, AccessRequest, ApprovalDecision
from governance_platform.access.enums import DecisionType


class AccessControlPortfolio(BaseModel):
    """A complete, internally-consistent set of access requests, decisions, and grants."""

    model_config = {"frozen": True, "extra": "forbid"}

    requests: tuple[AccessRequest, ...] = ()
    decisions: tuple[ApprovalDecision, ...] = ()
    grants: tuple[AccessGrant, ...] = ()

    @model_validator(mode="after")
    def _no_duplicate_ids(self) -> AccessControlPortfolio:
        for label, ids in (
            ("request_id", [r.request_id for r in self.requests]),
            ("decision_id", [d.decision_id for d in self.decisions]),
            ("grant_id", [g.grant_id for g in self.grants]),
        ):
            duplicates = sorted({item for item, count in Counter(ids).items() if count > 1})
            if duplicates:
                raise ValueError(f"duplicate {label} values found: {duplicates}")
        return self

    @model_validator(mode="after")
    def _decisions_reference_known_requests(self) -> AccessControlPortfolio:
        request_ids = {r.request_id for r in self.requests}
        seen_request_ids: set[str] = set()
        for d in self.decisions:
            if d.request_id not in request_ids:
                raise ValueError(
                    f"decision {d.decision_id} references unknown request_id: {d.request_id}"
                )
            if d.request_id in seen_request_ids:
                raise ValueError(
                    f"request {d.request_id} has more than one decision recorded against it"
                )
            seen_request_ids.add(d.request_id)
        return self

    @model_validator(mode="after")
    def _grants_reference_approved_decisions(self) -> AccessControlPortfolio:
        requests_by_id = {r.request_id: r for r in self.requests}
        decisions_by_request_id = {d.request_id: d for d in self.decisions}

        for g in self.grants:
            request = requests_by_id.get(g.request_id)
            if request is None:
                raise ValueError(
                    f"grant {g.grant_id} references unknown request_id: {g.request_id}"
                )

            decision = decisions_by_request_id.get(g.request_id)
            if decision is None or decision.decision != DecisionType.APPROVED:
                raise ValueError(
                    f"grant {g.grant_id} exists for request {g.request_id}, which has no "
                    f"approved decision — rejected or undecided requests cannot have grants"
                )

            if g.research_project_id != request.research_project_id:
                raise ValueError(
                    f"grant {g.grant_id}: research_project_id ({g.research_project_id}) does "
                    f"not match request {request.request_id}'s ({request.research_project_id})"
                )

            unrequested_datasets = sorted(set(g.dataset_ids) - set(request.requested_dataset_ids))
            if unrequested_datasets:
                raise ValueError(
                    f"grant {g.grant_id} includes dataset_id(s) not requested by "
                    f"{request.request_id}: {unrequested_datasets}"
                )
            unrequested_models = sorted(set(g.model_ids) - set(request.requested_model_ids))
            if unrequested_models:
                raise ValueError(
                    f"grant {g.grant_id} includes model_id(s) not requested by "
                    f"{request.request_id}: {unrequested_models}"
                )
        return self

    def request_by_id(self, request_id: str) -> AccessRequest:
        for r in self.requests:
            if r.request_id == request_id:
                return r
        raise KeyError(f"no access request with request_id={request_id!r}")

    def decision_for_request(self, request_id: str) -> ApprovalDecision | None:
        for d in self.decisions:
            if d.request_id == request_id:
                return d
        return None

    def grants_for_request(self, request_id: str) -> tuple[AccessGrant, ...]:
        return tuple(g for g in self.grants if g.request_id == request_id)
