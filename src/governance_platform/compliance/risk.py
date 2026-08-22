"""Deterministic risk scoring and posture derivation.

This is an explainable bounded score over control findings, not predictive
modelling and not a formal compliance rating.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from governance_platform.compliance.entities import ControlDefinition, ControlResult, RiskIndicator
from governance_platform.compliance.enums import (
    ControlDomain,
    ControlSeverity,
    ControlStatus,
    GovernancePosture,
    RiskCategory,
)

SEVERITY_SCORES: dict[ControlSeverity, int] = {
    ControlSeverity.LOW: 1,
    ControlSeverity.MEDIUM: 3,
    ControlSeverity.HIGH: 5,
    ControlSeverity.CRITICAL: 8,
}
MAX_TOTAL_RISK_SCORE = 100
ATTENTION_REQUIRED_SCORE_THRESHOLD = 5
HIGH_RISK_SCORE_THRESHOLD = 25
HIGH_RISK_FAILURE_THRESHOLD = 3

_DOMAIN_TO_CATEGORY: dict[ControlDomain, RiskCategory] = {
    ControlDomain.INVENTORY_GOVERNANCE: RiskCategory.INVENTORY,
    ControlDomain.DATASET_GOVERNANCE: RiskCategory.DATASET,
    ControlDomain.MODEL_GOVERNANCE: RiskCategory.MODEL,
    ControlDomain.RESEARCH_GOVERNANCE: RiskCategory.RESEARCH,
    ControlDomain.ACCESS_GOVERNANCE: RiskCategory.ACCESS,
    ControlDomain.AUDIT_COMPLETENESS: RiskCategory.AUDIT,
    ControlDomain.EVIDENCE_COMPLETENESS: RiskCategory.EVIDENCE,
    ControlDomain.RESPONSIBLE_AI_READINESS: RiskCategory.RESPONSIBLE_AI,
    ControlDomain.OPERATIONAL_GOVERNANCE: RiskCategory.OPERATIONAL,
}


def derive_risk_indicators(
    control_results: Iterable[ControlResult],
    control_definitions: Iterable[ControlDefinition],
    *,
    evaluated_at: datetime,
) -> tuple[RiskIndicator, ...]:
    """Create one bounded risk indicator for each warning or failed control result."""
    definitions_by_id = {control.control_id: control for control in control_definitions}
    indicators: list[RiskIndicator] = []

    for result in sorted(control_results, key=lambda r: r.result_id):
        if result.status == ControlStatus.PASS:
            continue
        definition = definitions_by_id[result.control_id]
        score = SEVERITY_SCORES[result.severity]
        indicators.append(
            RiskIndicator(
                indicator_id=f"RI-{len(indicators) + 1:04d}",
                entity_type=result.entity_type,
                entity_id=result.entity_id,
                category=_DOMAIN_TO_CATEGORY[definition.control_domain],
                severity=result.severity,
                score=score,
                rationale=(
                    f"{result.status.value} finding {result.finding_code.value}: {result.message}"
                ),
                evidence_refs=result.evidence_refs,
                evaluated_at=evaluated_at,
            )
        )

    return tuple(indicators)


def total_bounded_risk_score(indicators: Iterable[RiskIndicator]) -> int:
    """Return the total score capped at the documented maximum."""
    return min(sum(indicator.score for indicator in indicators), MAX_TOTAL_RISK_SCORE)


def derive_posture(
    control_results: Iterable[ControlResult], indicators: Iterable[RiskIndicator]
) -> GovernancePosture:
    """Classify overall posture using explicit deterministic thresholds."""
    results = tuple(control_results)
    risk_score = total_bounded_risk_score(indicators)
    failed = sum(1 for result in results if result.status == ControlStatus.FAIL)
    has_critical_failure = any(
        result.status == ControlStatus.FAIL and result.severity == ControlSeverity.CRITICAL
        for result in results
    )
    has_non_pass = any(result.status != ControlStatus.PASS for result in results)

    if (
        has_critical_failure
        or failed >= HIGH_RISK_FAILURE_THRESHOLD
        or risk_score >= HIGH_RISK_SCORE_THRESHOLD
    ):
        return GovernancePosture.HIGH_RISK
    if has_non_pass or risk_score >= ATTENTION_REQUIRED_SCORE_THRESHOLD:
        return GovernancePosture.ATTENTION_REQUIRED
    return GovernancePosture.HEALTHY
