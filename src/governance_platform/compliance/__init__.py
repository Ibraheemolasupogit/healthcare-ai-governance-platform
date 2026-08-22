"""Risk / compliance monitoring plane for the local governance simulation.

Milestone 5 evaluates fixed, deterministic controls over the already-existing
Milestone 2 inventory, Milestone 3 access-control state, and Milestone 4 audit
/ evidence state:

    Governance State -> Control Evaluation -> Compliance Findings
    -> Risk Indicators -> Governance Posture

This package does not implement regulatory certification, live monitoring,
alerting, production policy enforcement, or predictive risk modelling.
"""

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
    "FindingCode",
    "GovernancePosture",
    "RiskCategory",
    "RiskIndicator",
    "build_compliance_summary",
    "default_control_definitions",
    "derive_posture",
    "derive_risk_indicators",
    "evaluate_compliance",
    "export_compliance_assessment",
    "load_compliance_assessment",
    "render_governance_posture_markdown",
    "total_bounded_risk_score",
    "validate_compliance_assessment_data",
    "validate_compliance_assessment_file",
]
