"""Risk / compliance monitoring plane for the local governance simulation.

Milestone 5 evaluates fixed, deterministic controls over the already-existing
Milestone 2 inventory, Milestone 3 access-control state, and Milestone 4 audit
/ evidence state:

    Governance State -> Control Evaluation -> Compliance Findings
    -> Risk Indicators -> Governance Posture

This package does not implement regulatory certification, live monitoring,
alerting, production policy enforcement, or predictive risk modelling.
"""

from governance_platform.compliance.catalog import (
    ControlCatalogEntry,
    EvaluationType,
    EvidenceRequirement,
    PolicyAssuranceSummary,
    PolicyCatalogBundle,
    PolicyDefinition,
    PolicyDomain,
    PolicyStatus,
    SourcePlane,
    build_control_catalog,
    build_policy_assurance_summary,
    build_policy_catalog_bundle,
    build_policy_definitions,
    build_traceability_matrix,
    export_policy_catalog_bundle,
    load_control_catalog,
    load_policy_assurance_summary,
    load_policy_catalog,
    render_policy_assurance_summary_markdown,
    validate_policy_catalog,
    validate_policy_catalog_files,
)
from governance_platform.compliance.controls import default_control_definitions
from governance_platform.compliance.entities import (
    ComplianceAssessment,
    ComplianceSummary,
    ControlDefinition,
    ControlResult,
    RiskIndicator,
)
from governance_platform.compliance.enums import (
    ComplianceEntityType,
    ControlDomain,
    ControlSeverity,
    ControlStatus,
    FindingCode,
    GovernancePosture,
    RiskCategory,
)
from governance_platform.compliance.evaluation import (
    COMPLIANCE_LIMITATIONS,
    ComplianceEvaluator,
    build_compliance_summary,
    evaluate_compliance,
)
from governance_platform.compliance.io import (
    export_compliance_assessment,
    load_compliance_assessment,
)
from governance_platform.compliance.markdown import render_governance_posture_markdown
from governance_platform.compliance.risk import (
    ATTENTION_REQUIRED_SCORE_THRESHOLD,
    HIGH_RISK_FAILURE_THRESHOLD,
    HIGH_RISK_SCORE_THRESHOLD,
    MAX_TOTAL_RISK_SCORE,
    SEVERITY_SCORES,
    derive_posture,
    derive_risk_indicators,
    total_bounded_risk_score,
)
from governance_platform.compliance.validation import (
    validate_compliance_assessment_data,
    validate_compliance_assessment_file,
)

__all__ = [
    "ATTENTION_REQUIRED_SCORE_THRESHOLD",
    "COMPLIANCE_LIMITATIONS",
    "ControlCatalogEntry",
    "HIGH_RISK_FAILURE_THRESHOLD",
    "HIGH_RISK_SCORE_THRESHOLD",
    "MAX_TOTAL_RISK_SCORE",
    "SEVERITY_SCORES",
    "ComplianceAssessment",
    "ComplianceEntityType",
    "ComplianceEvaluator",
    "ComplianceSummary",
    "ControlDefinition",
    "ControlDomain",
    "ControlResult",
    "ControlSeverity",
    "ControlStatus",
    "EvaluationType",
    "EvidenceRequirement",
    "FindingCode",
    "GovernancePosture",
    "PolicyAssuranceSummary",
    "PolicyCatalogBundle",
    "PolicyDefinition",
    "PolicyDomain",
    "PolicyStatus",
    "RiskCategory",
    "RiskIndicator",
    "SourcePlane",
    "build_compliance_summary",
    "build_control_catalog",
    "build_policy_assurance_summary",
    "build_policy_catalog_bundle",
    "build_policy_definitions",
    "build_traceability_matrix",
    "default_control_definitions",
    "derive_posture",
    "derive_risk_indicators",
    "evaluate_compliance",
    "export_compliance_assessment",
    "export_policy_catalog_bundle",
    "load_control_catalog",
    "load_compliance_assessment",
    "load_policy_assurance_summary",
    "load_policy_catalog",
    "render_policy_assurance_summary_markdown",
    "render_governance_posture_markdown",
    "total_bounded_risk_score",
    "validate_compliance_assessment_data",
    "validate_compliance_assessment_file",
    "validate_policy_catalog",
    "validate_policy_catalog_files",
]
