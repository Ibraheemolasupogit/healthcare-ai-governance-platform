"""Enumerations for the local governance reporting plane."""

from __future__ import annotations

from enum import Enum


class ReportingMetricDomain(str, Enum):
    """Subject areas represented in reporting-ready KPI rows."""

    INVENTORY_POSTURE = "inventory_posture"
    DATASET_GOVERNANCE = "dataset_governance"
    MODEL_GOVERNANCE = "model_governance"
    RESEARCH_GOVERNANCE = "research_governance"
    ACCESS_CONTROL = "access_control"
    AUDIT_EVIDENCE = "audit_evidence"
    COMPLIANCE = "compliance"
    RISK = "risk"
    GOVERNANCE_POSTURE = "governance_posture"


class MetricUnit(str, Enum):
    """Units used by deterministic reporting KPIs."""

    COUNT = "count"
    PERCENT = "percent"
    BOOLEAN = "boolean"
    SCORE = "score"
    STATUS = "status"
