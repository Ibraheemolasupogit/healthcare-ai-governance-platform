"""Access / research-control plane — research access requests, decisions, and grants.

Milestone 3 (Access & Research Control Plane). This module implements a
**local governance simulation** of the workflow described in
``governance/access_review.md`` and ``governance/research_approval.md``:

    Access Request -> Policy Validation -> Approval Decision
    -> Time-Bounded Grant -> Revocation / Expiry

Typed, immutable entities (:mod:`governance_platform.access.entities`) model
each step. Eligibility is evaluated deterministically against the Milestone 2
inventory (:mod:`governance_platform.access.policy`), never against the
system clock, and orchestrated end-to-end by
:class:`~governance_platform.access.service.AccessControlService`
(:mod:`governance_platform.access.service`). Cross-entity referential
integrity within this plane — no duplicate IDs, no grant without an approved
decision — is enforced by
:class:`~governance_platform.access.portfolio.AccessControlPortfolio`.
Deterministic synthetic scenario generation, loading/export, standalone
validation, and an aggregate access-review summary live in
:mod:`governance_platform.access.generation`,
:mod:`governance_platform.access.io`,
:mod:`governance_platform.access.validation`, and
:mod:`governance_platform.access.summary` respectively.

This does not authenticate anyone, does not implement live Snowflake RBAC,
Entra ID, or any other identity system, does not provision real access, and
does not simulate audit events or compute a risk score. See
``governance/access_review.md`` and ``governance/research_approval.md`` for
the operating model this simulates, and the root README's Explicit
non-goals section for the full list of what is intentionally out of scope.
"""

from governance_platform.access.entities import AccessGrant, AccessRequest, ApprovalDecision
from governance_platform.access.enums import (
    DecisionType,
    GrantStatus,
    RejectionReasonCode,
    RequesterRole,
    RequestStatus,
)
from governance_platform.access.generation import (
    REFERENCE_EVALUATION_TIME,
    generate_access_control_state,
)
from governance_platform.access.io import export_access_state, load_access_state
from governance_platform.access.policy import EligibilityResult, Violation, evaluate_eligibility
from governance_platform.access.portfolio import AccessControlPortfolio
from governance_platform.access.service import AccessControlService
from governance_platform.access.summary import (
    AccessReviewSummary,
    GrantStatusCounts,
    build_access_summary,
)
from governance_platform.access.validation import (
    validate_access_state_data,
    validate_access_state_file,
)

__all__ = [
    "REFERENCE_EVALUATION_TIME",
    "AccessControlPortfolio",
    "AccessControlService",
    "AccessGrant",
    "AccessRequest",
    "AccessReviewSummary",
    "ApprovalDecision",
    "DecisionType",
    "EligibilityResult",
    "GrantStatus",
    "GrantStatusCounts",
    "RejectionReasonCode",
    "RequestStatus",
    "RequesterRole",
    "Violation",
    "build_access_summary",
    "evaluate_eligibility",
    "export_access_state",
    "generate_access_control_state",
    "load_access_state",
    "validate_access_state_data",
    "validate_access_state_file",
]
