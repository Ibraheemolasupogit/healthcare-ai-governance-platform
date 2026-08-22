"""Audit / evidence plane — an append-only audit trail and deterministic evidence generation.

Milestone 4 (Audit & Evidence Plane). This module implements a **local,
deterministic governance simulation** of the workflow described in
``governance/audit_evidence.md``:

    Governance Action -> Audit Event -> Immutable Event History
    -> Evidence Aggregation -> Reproducible Evidence Export

A typed, immutable :class:`~governance_platform.audit.entities.AuditEvent`
(:mod:`governance_platform.audit.entities`) records one governance action.
:mod:`governance_platform.audit.adapters` translates already-produced
Milestone 2/3 records (inventory, access requests, decisions, grants) into
audit events via pure functions — it does not wrap or modify
:class:`~governance_platform.access.AccessControlService`, keeping the
access plane independently testable. Events are deterministically correlated
by :func:`~governance_platform.audit.adapters.request_correlation_id` so a
whole request -> evaluation -> decision -> grant -> revocation/expiry
activity is traceable as one group. An append-only
:class:`~governance_platform.audit.log.AuditLog`
(:mod:`governance_platform.audit.log`) enforces event-ID uniqueness and
non-decreasing timestamps within each correlation group; there is no
update/remove method — :meth:`~governance_platform.audit.log.AuditLog.append`
always returns a new log. :mod:`governance_platform.audit.completeness`
checks the log against the inventory/access-control state for missing
expected evidence. :mod:`governance_platform.audit.evidence` derives a
reproducible, reviewer-readable :class:`~governance_platform.audit.evidence.EvidencePack`
(JSON and Markdown, via :mod:`governance_platform.audit.markdown`).
Deterministic generation, loading/export, and an aggregate audit summary
live in :mod:`governance_platform.audit.generation`,
:mod:`governance_platform.audit.io`, and
:mod:`governance_platform.audit.summary` respectively.

This does not implement a real SIEM, cloud audit service, Snowflake
query-history ingestion, Microsoft Purview or Entra ID audit-log ingestion,
real-time streaming, or an incident-response engine. See
``governance/audit_evidence.md`` for the operating model this simulates, and
the root README's Explicit non-goals section for the full list of what is
intentionally out of scope.
"""

from governance_platform.audit.adapters import request_correlation_id
from governance_platform.audit.completeness import check_completeness
from governance_platform.audit.entities import AuditEvent
from governance_platform.audit.enums import (
    ActorType,
    AuditAction,
    AuditEntityType,
    AuditEventType,
    AuditOutcome,
)
from governance_platform.audit.evidence import (
    AccessRequestEvidence,
    ApprovalDecisionEvidence,
    CompletenessEvidence,
    CorrelationGroupEvidence,
    EvidencePack,
    GrantEvidence,
    InventoryEvidence,
    RejectedAccessEvidence,
    build_evidence_pack,
)
from governance_platform.audit.generation import generate_audit_log
from governance_platform.audit.io import (
    export_audit_log,
    export_audit_summary,
    export_evidence_pack,
    load_audit_log,
    load_evidence_pack,
)
from governance_platform.audit.log import AuditLog
from governance_platform.audit.markdown import render_evidence_pack_markdown
from governance_platform.audit.summary import AuditCoverage, AuditSummary, build_audit_summary
from governance_platform.audit.validation import (
    validate_audit_log_data,
    validate_audit_log_file,
    validate_evidence_pack_file,
)

__all__ = [
    "AccessRequestEvidence",
    "ActorType",
    "ApprovalDecisionEvidence",
    "AuditAction",
    "AuditCoverage",
    "AuditEntityType",
    "AuditEvent",
    "AuditEventType",
    "AuditLog",
    "AuditOutcome",
    "AuditSummary",
    "CompletenessEvidence",
    "CorrelationGroupEvidence",
    "EvidencePack",
    "GrantEvidence",
    "InventoryEvidence",
    "RejectedAccessEvidence",
    "build_audit_summary",
    "build_evidence_pack",
    "check_completeness",
    "export_audit_log",
    "export_audit_summary",
    "export_evidence_pack",
    "generate_audit_log",
    "load_audit_log",
    "load_evidence_pack",
    "render_evidence_pack_markdown",
    "request_correlation_id",
    "validate_audit_log_data",
    "validate_audit_log_file",
    "validate_evidence_pack_file",
]
