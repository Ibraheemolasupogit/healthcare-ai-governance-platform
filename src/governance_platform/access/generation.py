"""Deterministic synthetic access-control scenario generation.

Builds a restrained, hand-authored set of access requests against the
Milestone 2 synthetic inventory (``governance_platform.inventory.generate_portfolio``),
runs each through :class:`~governance_platform.access.service.AccessControlService`,
and returns the resulting :class:`~governance_platform.access.portfolio.AccessControlPortfolio`.

Every scenario is fixed data processed through the real service/policy code
— not randomly sampled and not hand-written outcomes — so the recorded
decisions and grants are exactly what :mod:`governance_platform.access.policy`
actually computes, and rerunning this function always produces identical
output. All identities are fictional, role-based access-plane identifiers
(e.g. ``"researcher-population-health-01"``), never real people — see ADR
0001. All timestamps are fixed historical placeholders chosen to sit inside
or outside specific projects' windows on purpose; none are derived from the
current date.
"""

from __future__ import annotations

from datetime import datetime

from governance_platform.access.entities import AccessGrant, AccessRequest, ApprovalDecision
from governance_platform.access.enums import RequesterRole
from governance_platform.access.portfolio import AccessControlPortfolio
from governance_platform.access.service import AccessControlService
from governance_platform.inventory import generate_portfolio

#: The fixed instant later used to evaluate grant activity (e.g. by the
#: summary and the CLI script) — a synthetic reference point, not "now".
REFERENCE_EVALUATION_TIME = datetime(2025, 3, 15)

_APPROVER_GOVERNANCE_1 = "access-approver-governance-01"
_APPROVER_GOVERNANCE_2 = "access-approver-governance-02"


def generate_access_control_state() -> AccessControlPortfolio:
    """Return the deterministic synthetic access-control state.

    Runs ten fixed scenarios through the real service against the Milestone 2
    synthetic inventory, covering: a valid approved request; requests against
    a pending and an expired project; a dataset not linked to its project; a
    dataset whose research use is prohibited; a request whose duration
    exceeds its project's expiry; unknown dataset/model references; an
    unknown research project; and, among the approved requests, one grant
    left active, one left to expire by the reference evaluation time, and one
    explicitly revoked.
    """
    inventory = generate_portfolio()
    service = AccessControlService(inventory)

    requests: list[AccessRequest] = []
    decisions: list[ApprovalDecision] = []
    grants: list[AccessGrant] = []

    def submit_and_decide(
        *,
        request_id: str,
        decision_id: str,
        requester_id: str,
        requester_role: RequesterRole,
        research_project_id: str,
        purpose: str,
        requested_at: datetime,
        requested_until: datetime,
        approver_id: str,
        decided_at: datetime,
        requested_dataset_ids: tuple[str, ...] = (),
        requested_model_ids: tuple[str, ...] = (),
    ) -> tuple[AccessRequest, ApprovalDecision]:
        submitted = service.submit_request(
            request_id=request_id,
            requester_id=requester_id,
            requester_role=requester_role,
            research_project_id=research_project_id,
            purpose=purpose,
            requested_at=requested_at,
            requested_until=requested_until,
            requested_dataset_ids=requested_dataset_ids,
            requested_model_ids=requested_model_ids,
        )
        finalized, decision = service.decide(
            submitted, decision_id=decision_id, approver_id=approver_id, decided_at=decided_at
        )
        requests.append(finalized)
        decisions.append(decision)
        return finalized, decision

    # 1. Valid approved research access -> becomes the ACTIVE grant.
    request_01, decision_01 = submit_and_decide(
        request_id="AR-0001",
        decision_id="AD-0001",
        requester_id="researcher-population-health-01",
        requester_role=RequesterRole.PRINCIPAL_INVESTIGATOR,
        research_project_id="RP-0001",
        purpose="Cohort-level readmission risk analysis using approved population health data.",
        requested_at=datetime(2025, 1, 5),
        requested_until=datetime(2025, 4, 10),
        requested_dataset_ids=("DS-0002", "DS-0004"),
        requested_model_ids=("MD-0001",),
        approver_id=_APPROVER_GOVERNANCE_1,
        decided_at=datetime(2025, 1, 8),
    )
    grants.append(
        service.create_grant(
            request_01,
            decision_01,
            grant_id="AG-0001",
            granted_at=datetime(2025, 1, 10),
            expires_at=datetime(2025, 4, 10),
        )
    )

    # 2. Request against a pending project (RP-0003) -> rejected.
    submit_and_decide(
        request_id="AR-0002",
        decision_id="AD-0002",
        requester_id="researcher-clinical-nlp-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0003",
        purpose="Feasibility review of synthetic clinical note summarization.",
        requested_at=datetime(2025, 2, 5),
        requested_until=datetime(2025, 6, 1),
        requested_dataset_ids=("DS-0003",),
        requested_model_ids=("MD-0003",),
        approver_id=_APPROVER_GOVERNANCE_1,
        decided_at=datetime(2025, 2, 7),
    )

    # 3. Request against an expired project (RP-0004) -> rejected.
    submit_and_decide(
        request_id="AR-0003",
        decision_id="AD-0003",
        requester_id="researcher-finance-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0004",
        purpose="Retrospective review of the retired legacy claims risk model.",
        requested_at=datetime(2024, 8, 1),
        requested_until=datetime(2024, 9, 1),
        requested_dataset_ids=("DS-0006",),
        requested_model_ids=("MD-0005",),
        approver_id=_APPROVER_GOVERNANCE_2,
        decided_at=datetime(2024, 8, 3),
    )

    # 4. Dataset not linked to the (approved) project -> rejected.
    submit_and_decide(
        request_id="AR-0004",
        decision_id="AD-0004",
        requester_id="researcher-population-health-02",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        purpose="Exploratory look at operational scheduling data for care-transition context.",
        requested_at=datetime(2025, 1, 12),
        requested_until=datetime(2025, 4, 1),
        requested_dataset_ids=("DS-0001",),
        approver_id=_APPROVER_GOVERNANCE_1,
        decided_at=datetime(2025, 1, 14),
    )

    # 5. Dataset not linked to the project, and research use is prohibited -> rejected.
    submit_and_decide(
        request_id="AR-0005",
        decision_id="AD-0005",
        requester_id="researcher-operations-02",
        requester_role=RequesterRole.DATA_ANALYST,
        research_project_id="RP-0002",
        purpose="Assess feasibility of extending scheduling research to legacy imaging metadata.",
        requested_at=datetime(2025, 1, 20),
        requested_until=datetime(2025, 3, 20),
        requested_dataset_ids=("DS-0006",),
        approver_id=_APPROVER_GOVERNANCE_1,
        decided_at=datetime(2025, 1, 22),
    )

    # 6. Requested duration extends beyond the project's expiry -> rejected.
    submit_and_decide(
        request_id="AR-0006",
        decision_id="AD-0006",
        requester_id="researcher-operations-03",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0002",
        purpose="Extended scheduling-policy research beyond the pilot's original window.",
        requested_at=datetime(2025, 1, 5),
        requested_until=datetime(2025, 6, 1),
        requested_dataset_ids=("DS-0001",),
        requested_model_ids=("MD-0002",),
        approver_id=_APPROVER_GOVERNANCE_2,
        decided_at=datetime(2025, 1, 7),
    )

    # 7. Unknown dataset and model references -> rejected.
    submit_and_decide(
        request_id="AR-0007",
        decision_id="AD-0007",
        requester_id="researcher-population-health-03",
        requester_role=RequesterRole.MODEL_DEVELOPER,
        research_project_id="RP-0001",
        purpose="Prototype a new derived signal not yet present in the inventory.",
        requested_at=datetime(2025, 1, 15),
        requested_until=datetime(2025, 4, 1),
        requested_dataset_ids=("DS-9999",),
        requested_model_ids=("MD-9999",),
        approver_id=_APPROVER_GOVERNANCE_1,
        decided_at=datetime(2025, 1, 17),
    )

    # 8. Unknown research project -> rejected.
    submit_and_decide(
        request_id="AR-0008",
        decision_id="AD-0008",
        requester_id="researcher-operations-04",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-9999",
        purpose="Access requested against a project not present in the inventory.",
        requested_at=datetime(2025, 1, 18),
        requested_until=datetime(2025, 3, 1),
        requested_dataset_ids=("DS-0001",),
        approver_id=_APPROVER_GOVERNANCE_2,
        decided_at=datetime(2025, 1, 19),
    )

    # 9. Approved, but its grant's window is entirely in the past by the
    #    reference evaluation time -> EXPIRED grant (not revoked).
    request_09, decision_09 = submit_and_decide(
        request_id="AR-0009",
        decision_id="AD-0009",
        requester_id="researcher-operations-05",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0002",
        purpose="Short-window no-show prediction analysis for a scheduling policy brief.",
        requested_at=datetime(2024, 5, 25),
        requested_until=datetime(2024, 9, 1),
        requested_dataset_ids=("DS-0001",),
        requested_model_ids=("MD-0002",),
        approver_id=_APPROVER_GOVERNANCE_1,
        decided_at=datetime(2024, 5, 28),
    )
    grants.append(
        service.create_grant(
            request_09,
            decision_09,
            grant_id="AG-0002",
            granted_at=datetime(2024, 6, 1),
            expires_at=datetime(2024, 9, 1),
        )
    )

    # 10. Approved, then explicitly revoked -> REVOKED grant.
    request_10, decision_10 = submit_and_decide(
        request_id="AR-0010",
        decision_id="AD-0010",
        requester_id="researcher-population-health-04",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        purpose="Supplementary population health segmentation analysis.",
        requested_at=datetime(2025, 1, 25),
        requested_until=datetime(2025, 4, 1),
        requested_dataset_ids=("DS-0002",),
        requested_model_ids=("MD-0001",),
        approver_id=_APPROVER_GOVERNANCE_2,
        decided_at=datetime(2025, 1, 28),
    )
    grant_10 = service.create_grant(
        request_10,
        decision_10,
        grant_id="AG-0003",
        granted_at=datetime(2025, 2, 1),
        expires_at=datetime(2025, 4, 1),
    )
    grants.append(
        service.revoke_grant(
            grant_10,
            revoked_at=datetime(2025, 2, 20),
            revocation_reason="Requester left the research team; access no longer required.",
        )
    )

    return AccessControlPortfolio(
        requests=tuple(requests),
        decisions=tuple(decisions),
        grants=tuple(grants),
    )
