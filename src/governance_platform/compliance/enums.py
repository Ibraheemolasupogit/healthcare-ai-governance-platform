"""Enumerations for the risk / compliance monitoring plane."""

from __future__ import annotations

from enum import Enum


class ControlDomain(str, Enum):
    """Restrained control domains evaluated by the local compliance plane."""

    INVENTORY_GOVERNANCE = "inventory_governance"
    DATASET_GOVERNANCE = "dataset_governance"
    MODEL_GOVERNANCE = "model_governance"
    RESEARCH_GOVERNANCE = "research_governance"
    ACCESS_GOVERNANCE = "access_governance"
    AUDIT_COMPLETENESS = "audit_completeness"
    EVIDENCE_COMPLETENESS = "evidence_completeness"
    RESPONSIBLE_AI_READINESS = "responsible_ai_readiness"
    OPERATIONAL_GOVERNANCE = "operational_governance"


class ControlSeverity(str, Enum):
    """Severity vocabulary shared by controls, findings, and risk indicators."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ControlStatus(str, Enum):
    """Outcome of one control evaluation."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class ComplianceEntityType(str, Enum):
    """Entity types a control result or risk indicator can refer to."""

    PORTFOLIO = "portfolio"
    DATASET = "dataset"
    MODEL = "model"
    RESEARCH_PROJECT = "research_project"
    ACCESS_REQUEST = "access_request"
    APPROVAL_DECISION = "approval_decision"
    ACCESS_GRANT = "access_grant"
    AUDIT_LOG = "audit_log"
    EVIDENCE_PACK = "evidence_pack"


class FindingCode(str, Enum):
    """Stable finding codes emitted by the deterministic evaluator."""

    CONTROL_PASSED = "control_passed"
    DUPLICATE_INVENTORY_ID = "duplicate_inventory_id"
    UNRESOLVED_INVENTORY_REFERENCE = "unresolved_inventory_reference"
    SYNTHETIC_DATA_INVARIANT_BROKEN = "synthetic_data_invariant_broken"
    MISSING_STEWARDSHIP_METADATA = "missing_stewardship_metadata"
    MISSING_REVIEW_DATE = "missing_review_date"
    RESEARCH_PROHIBITED_DATASET_GRANTED = "research_prohibited_dataset_granted"
    GRANTED_DATASET_NOT_APPROVED = "granted_dataset_not_approved"
    DATASET_SENSITIVITY_MISSING = "dataset_sensitivity_missing"
    DATASET_LIFECYCLE_INCOMPATIBLE = "dataset_lifecycle_incompatible"
    HIGH_RISK_MODEL_RAI_REVIEW_MISSING = "high_risk_model_rai_review_missing"
    HIGH_RISK_MODEL_MONITORING_MISSING = "high_risk_model_monitoring_missing"
    GRANTED_MODEL_NOT_APPROVED = "granted_model_not_approved"
    MODEL_DATASET_REFERENCE_UNRESOLVED = "model_dataset_reference_unresolved"
    HIGH_RISK_MODEL_REVIEW_PENDING = "high_risk_model_review_pending"
    ACTIVE_GRANT_PROJECT_NOT_APPROVED = "active_grant_project_not_approved"
    ACTIVE_GRANT_PROJECT_EXPIRED = "active_grant_project_expired"
    GRANTED_ASSET_OUT_OF_SCOPE = "granted_asset_out_of_scope"
    GRANT_MISSING_APPROVAL_EVIDENCE = "grant_missing_approval_evidence"
    REJECTED_REQUEST_HAS_GRANT = "rejected_request_has_grant"
    GRANT_NOT_TIME_BOUNDED = "grant_not_time_bounded"
    INACTIVE_GRANT_STILL_ACTIVE = "inactive_grant_still_active"
    AUDIT_COMPLETENESS_PROBLEM = "audit_completeness_problem"
    REQUIRED_LIFECYCLE_EVENT_MISSING = "required_lifecycle_event_missing"
    CORRELATION_CHAIN_NOT_TRACEABLE = "correlation_chain_not_traceable"
    DUPLICATE_AUDIT_EVENT_ID = "duplicate_audit_event_id"
    EVIDENCE_REFERENCE_UNRESOLVED = "evidence_reference_unresolved"


class RiskCategory(str, Enum):
    """Risk indicator categories derived from control findings."""

    INVENTORY = "inventory"
    DATASET = "dataset"
    MODEL = "model"
    RESEARCH = "research"
    ACCESS = "access"
    AUDIT = "audit"
    EVIDENCE = "evidence"
    RESPONSIBLE_AI = "responsible_ai"
    OPERATIONAL = "operational"


class GovernancePosture(str, Enum):
    """Overall posture for the local deterministic assessment."""

    HEALTHY = "healthy"
    ATTENTION_REQUIRED = "attention_required"
    HIGH_RISK = "high_risk"
