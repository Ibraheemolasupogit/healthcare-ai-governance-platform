"""Deterministic governance eligibility checks for an access request against the inventory.

This is the only module in the access plane that reads
``governance_platform.inventory`` — everything else in this package operates
on access entities alone. Evaluation is a pure function of the request and
the inventory snapshot passed in: no wall-clock time, no hidden state, so the
same request against the same inventory always produces the same result.

This is a **local governance simulation** of the checks described in
``governance/access_review.md`` and ``governance/research_approval.md``, not
a live policy-as-code engine (see ADR 0005) and not enforcement against a
real identity or Snowflake RBAC system.
"""

from __future__ import annotations

from pydantic import BaseModel

from governance_platform.access.entities import AccessRequest
from governance_platform.access.enums import RejectionReasonCode
from governance_platform.inventory import ApprovalStatus, InventoryPortfolio


class Violation(BaseModel):
    """One reason an access request failed eligibility, with a human-readable detail."""

    model_config = {"frozen": True}

    code: RejectionReasonCode
    detail: str


class EligibilityResult(BaseModel):
    """The outcome of evaluating an :class:`AccessRequest` against the inventory.

    ``eligible`` is true only when ``violations`` is empty. A request can fail
    for more than one reason at once — every applicable rule is checked and
    reported, rather than stopping at the first violation, so a rejection is
    fully explainable.
    """

    model_config = {"frozen": True}

    eligible: bool
    violations: tuple[Violation, ...] = ()


def evaluate_eligibility(
    request: AccessRequest, inventory: InventoryPortfolio
) -> EligibilityResult:
    """Evaluate ``request`` against ``inventory`` and return every applicable violation.

    Implements, in order: (1) the referenced research project must exist,
    (2) it must be approved, (3) it must not be expired, (4)/(5) every
    requested dataset/model must exist, (6) every requested dataset/model
    must already be linked to the project, (7) requested datasets must permit
    research use, (8) requested datasets and models must themselves be in an
    approved governance state, and (9) the requested duration must not extend
    beyond the project's expiry.
    """
    violations: list[Violation] = []

    project = None
    for candidate in inventory.research_projects:
        if candidate.research_project_id == request.research_project_id:
            project = candidate
            break

    if project is None:
        violations.append(
            Violation(
                code=RejectionReasonCode.UNKNOWN_RESEARCH_PROJECT,
                detail=(
                    f"research project {request.research_project_id} does not exist "
                    f"in the inventory"
                ),
            )
        )
    elif project.approval_status == ApprovalStatus.EXPIRED:
        violations.append(
            Violation(
                code=RejectionReasonCode.RESEARCH_PROJECT_EXPIRED,
                detail=f"research project {project.research_project_id} approval_status is expired",
            )
        )
    elif project.approval_status != ApprovalStatus.APPROVED:
        violations.append(
            Violation(
                code=RejectionReasonCode.RESEARCH_PROJECT_NOT_APPROVED,
                detail=(
                    f"research project {project.research_project_id} approval_status is "
                    f"{project.approval_status.value}, not approved"
                ),
            )
        )

    dataset_by_id = {d.dataset_id: d for d in inventory.datasets}
    model_by_id = {m.model_id: m for m in inventory.models}

    for dataset_id in request.requested_dataset_ids:
        dataset = dataset_by_id.get(dataset_id)
        if dataset is None:
            violations.append(
                Violation(
                    code=RejectionReasonCode.UNKNOWN_DATASET,
                    detail=f"dataset {dataset_id} does not exist in the inventory",
                )
            )
            continue

        if project is not None and dataset_id not in project.linked_dataset_ids:
            violations.append(
                Violation(
                    code=RejectionReasonCode.DATASET_NOT_LINKED_TO_PROJECT,
                    detail=(
                        f"dataset {dataset_id} is not linked to research project "
                        f"{project.research_project_id}"
                    ),
                )
            )
        if not dataset.research_use_allowed:
            violations.append(
                Violation(
                    code=RejectionReasonCode.RESEARCH_USE_NOT_ALLOWED,
                    detail=f"dataset {dataset_id} does not permit research use",
                )
            )
        if dataset.approval_status != ApprovalStatus.APPROVED:
            violations.append(
                Violation(
                    code=RejectionReasonCode.DATASET_NOT_APPROVED,
                    detail=(
                        f"dataset {dataset_id} approval_status is "
                        f"{dataset.approval_status.value}, not approved"
                    ),
                )
            )

    for model_id in request.requested_model_ids:
        model = model_by_id.get(model_id)
        if model is None:
            violations.append(
                Violation(
                    code=RejectionReasonCode.UNKNOWN_MODEL,
                    detail=f"model {model_id} does not exist in the inventory",
                )
            )
            continue

        if project is not None and model_id not in project.linked_model_ids:
            violations.append(
                Violation(
                    code=RejectionReasonCode.MODEL_NOT_LINKED_TO_PROJECT,
                    detail=(
                        f"model {model_id} is not linked to research project "
                        f"{project.research_project_id}"
                    ),
                )
            )
        if model.approval_status != ApprovalStatus.APPROVED:
            violations.append(
                Violation(
                    code=RejectionReasonCode.MODEL_NOT_APPROVED,
                    detail=(
                        f"model {model_id} approval_status is "
                        f"{model.approval_status.value}, not approved"
                    ),
                )
            )

    if project is not None and request.requested_until.date() > project.expiry_date:
        violations.append(
            Violation(
                code=RejectionReasonCode.REQUESTED_DURATION_EXCEEDS_PROJECT_EXPIRY,
                detail=(
                    f"requested_until ({request.requested_until.date()}) is after research "
                    f"project {project.research_project_id} expiry_date ({project.expiry_date})"
                ),
            )
        )

    return EligibilityResult(eligible=not violations, violations=tuple(violations))
