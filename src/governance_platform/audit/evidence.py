"""Deterministic evidence-pack derivation from the audit log and source-of-truth state.

The evidence pack does not copy full datasets or model/project records — it
carries references, identifiers, timestamps, decisions, and control outcomes
(per ``governance/audit_evidence.md``), reading the inventory and
access-control state as the source of truth and the audit log as the record
of what was observed happening. Everything here is a pure function of its
inputs: the same inventory, access state, audit log, and explicitly supplied
timestamps always produce a byte-identical pack.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from governance_platform.access import (
    AccessControlPortfolio,
    AccessControlService,
    AccessGrant,
    AccessReviewSummary,
    DecisionType,
    GrantStatus,
    build_access_summary,
)
from governance_platform.audit.adapters import request_correlation_id
from governance_platform.audit.completeness import check_completeness
from governance_platform.audit.log import AuditLog
from governance_platform.audit.summary import AuditSummary, build_audit_summary
from governance_platform.inventory import InventoryPortfolio
from governance_platform.inventory import build_summary as build_inventory_summary

#: This platform's fixed non-goals, restated in every evidence pack so a
#: reviewer never has to guess the claim boundary from the data alone.
EVIDENCE_PACK_LIMITATIONS: tuple[str, ...] = (
    "This is a local, deterministic governance simulation, not a production audit trail.",
    "No live Snowflake query-history ingestion, SIEM, Microsoft Purview, or Entra ID audit-log "
    "integration exists.",
    "AccessGrant does not record a revoker identity (a Milestone 3 entity limitation this plane "
    "does not redesign); grant_revoked events are attributed to the system, not a specific person.",
    "No enterprise risk score, regulatory certification, or real-time monitoring is produced or "
    "implied.",
)

SOURCE_SYSTEMS: tuple[str, ...] = (
    "governance_platform.inventory (local, synthetic)",
    "governance_platform.access (local, synthetic, simulated)",
)


class InventoryEvidence(BaseModel):
    """A restrained view of the inventory's governance-relevant shape — counts and status
    breakdowns, not the full dataset/model/project records."""

    model_config = {"frozen": True}

    dataset_count: int
    model_count: int
    research_project_count: int
    dataset_approval_status: dict[str, int]
    model_risk_tier: dict[str, int]
    research_project_approval_status: dict[str, int]


class AccessRequestEvidence(BaseModel):
    model_config = {"frozen": True}

    request_id: str
    research_project_id: str
    requester_id: str
    status: str
    requested_dataset_ids: tuple[str, ...]
    requested_model_ids: tuple[str, ...]
    correlation_id: str


class ApprovalDecisionEvidence(BaseModel):
    model_config = {"frozen": True}

    decision_id: str
    request_id: str
    approver_id: str
    decision: str
    decision_reason: str
    decided_at: datetime


class GrantEvidence(BaseModel):
    model_config = {"frozen": True}

    grant_id: str
    request_id: str
    research_project_id: str
    granted_at: datetime
    expires_at: datetime
    status_as_of_evaluation: str
    revoked_at: datetime | None
    revocation_reason: str | None


class RejectedAccessEvidence(BaseModel):
    model_config = {"frozen": True}

    request_id: str
    research_project_id: str
    decision_id: str
    decision_reason: str
    decided_at: datetime


class CorrelationGroupEvidence(BaseModel):
    """One traceable governance activity: every event type recorded under one correlation id,
    in chronological order, and the outcome of the last event in that chain."""

    model_config = {"frozen": True}

    correlation_id: str
    event_types: tuple[str, ...]
    final_outcome: str


class CompletenessEvidence(BaseModel):
    model_config = {"frozen": True}

    complete: bool
    problems: tuple[str, ...]


class EvidencePack(BaseModel):
    """A reproducible, reviewer-readable snapshot of governance evidence.

    Not itself the audit log or the inventory/access state — a derived,
    restrained summary of them, suitable for the ``evidence_pack.json`` /
    ``evidence_pack.md`` outputs.
    """

    model_config = {"frozen": True}

    evidence_pack_id: str
    generated_at: datetime
    scope: str
    source_systems: tuple[str, ...]
    inventory_evidence: InventoryEvidence
    access_summary: AccessReviewSummary
    audit_summary: AuditSummary
    access_requests: tuple[AccessRequestEvidence, ...]
    approval_decisions: tuple[ApprovalDecisionEvidence, ...]
    grants: tuple[GrantEvidence, ...]
    rejected_access: tuple[RejectedAccessEvidence, ...]
    correlation_groups: tuple[CorrelationGroupEvidence, ...]
    completeness: CompletenessEvidence
    limitations: tuple[str, ...]


def _grant_status_as_of_evaluation(grant: AccessGrant, evaluated_at: datetime) -> str:
    if AccessControlService.is_grant_active(grant, evaluated_at):
        return "active"
    if grant.status == GrantStatus.REVOKED:
        return "revoked"
    return "expired"


def build_evidence_pack(
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
    audit_log: AuditLog,
    *,
    evidence_pack_id: str,
    generated_at: datetime,
    evaluated_at: datetime,
) -> EvidencePack:
    """Derive the deterministic evidence pack from source-of-truth state and the audit log.

    ``generated_at`` and ``evaluated_at`` are both explicitly supplied by the
    caller — this never reads the system clock. They are conceptually
    distinct: ``evaluated_at`` is the instant grant activity is evaluated as
    of (matching ``governance_platform.access.REFERENCE_EVALUATION_TIME``),
    ``generated_at`` is the instant this evidence pack claims to represent.
    """
    inventory_summary = build_inventory_summary(inventory)
    access_summary = build_access_summary(access_state, inventory, evaluated_at=evaluated_at)
    audit_summary = build_audit_summary(audit_log, access_state)
    completeness_problems = check_completeness(audit_log, inventory, access_state)

    inventory_evidence = InventoryEvidence(
        dataset_count=inventory_summary.entity_counts.datasets,
        model_count=inventory_summary.entity_counts.models,
        research_project_count=inventory_summary.entity_counts.research_projects,
        dataset_approval_status=inventory_summary.dataset_approval_status,
        model_risk_tier=inventory_summary.model_risk_tier,
        research_project_approval_status=inventory_summary.research_project_approval_status,
    )

    access_requests_evidence = tuple(
        AccessRequestEvidence(
            request_id=r.request_id,
            research_project_id=r.research_project_id,
            requester_id=r.requester_id,
            status=r.status.value,
            requested_dataset_ids=r.requested_dataset_ids,
            requested_model_ids=r.requested_model_ids,
            correlation_id=request_correlation_id(r.request_id),
        )
        for r in sorted(access_state.requests, key=lambda r: r.request_id)
    )

    decisions_evidence = tuple(
        ApprovalDecisionEvidence(
            decision_id=d.decision_id,
            request_id=d.request_id,
            approver_id=d.approver_id,
            decision=d.decision.value,
            decision_reason=d.decision_reason,
            decided_at=d.decided_at,
        )
        for d in sorted(access_state.decisions, key=lambda d: d.decision_id)
    )

    grants_evidence = tuple(
        GrantEvidence(
            grant_id=g.grant_id,
            request_id=g.request_id,
            research_project_id=g.research_project_id,
            granted_at=g.granted_at,
            expires_at=g.expires_at,
            status_as_of_evaluation=_grant_status_as_of_evaluation(g, evaluated_at),
            revoked_at=g.revoked_at,
            revocation_reason=g.revocation_reason,
        )
        for g in sorted(access_state.grants, key=lambda g: g.grant_id)
    )

    rejected_access_evidence = tuple(
        RejectedAccessEvidence(
            request_id=r.request_id,
            research_project_id=r.research_project_id,
            decision_id=decision.decision_id,
            decision_reason=decision.decision_reason,
            decided_at=decision.decided_at,
        )
        for r in sorted(access_state.requests, key=lambda r: r.request_id)
        if (decision := access_state.decision_for_request(r.request_id)) is not None
        and decision.decision == DecisionType.REJECTED
    )

    correlation_groups_evidence = tuple(
        CorrelationGroupEvidence(
            correlation_id=correlation_id,
            event_types=tuple(e.event_type.value for e in events),
            final_outcome=events[-1].outcome.value,
        )
        for correlation_id, events in sorted(audit_log.correlation_groups().items())
    )

    return EvidencePack(
        evidence_pack_id=evidence_pack_id,
        generated_at=generated_at,
        scope=(
            "Synthetic healthcare AI governance inventory (Milestone 2) and access-control "
            "activity (Milestone 3), as recorded in the audit log (Milestone 4)."
        ),
        source_systems=SOURCE_SYSTEMS,
        inventory_evidence=inventory_evidence,
        access_summary=access_summary,
        audit_summary=audit_summary,
        access_requests=access_requests_evidence,
        approval_decisions=decisions_evidence,
        grants=grants_evidence,
        rejected_access=rejected_access_evidence,
        correlation_groups=correlation_groups_evidence,
        completeness=CompletenessEvidence(
            complete=not completeness_problems, problems=tuple(completeness_problems)
        ),
        limitations=EVIDENCE_PACK_LIMITATIONS,
    )
