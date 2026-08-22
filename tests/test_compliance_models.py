from datetime import datetime

import pytest
from pydantic import ValidationError

from governance_platform.compliance import (
    ComplianceEntityType,
    ControlDefinition,
    ControlDomain,
    ControlResult,
    ControlSeverity,
    ControlStatus,
    FindingCode,
    RiskCategory,
    RiskIndicator,
)


def test_control_definition_is_frozen_and_forbids_extra_fields() -> None:
    control = ControlDefinition(
        control_id="CTRL-9999",
        name="Test control",
        description="Used only in tests.",
        control_domain=ControlDomain.INVENTORY_GOVERNANCE,
        severity=ControlSeverity.HIGH,
        applies_to=(ComplianceEntityType.PORTFOLIO,),
        evidence_requirements=("inventory_portfolio",),
    )

    with pytest.raises(ValidationError):
        ControlDefinition.model_validate({**control.model_dump(mode="json"), "extra": "nope"})
    with pytest.raises(ValidationError):
        control.name = "Changed"  # type: ignore[misc]


def test_control_result_requires_pass_code_for_passing_status() -> None:
    with pytest.raises(ValidationError):
        ControlResult(
            result_id="CR-0001",
            control_id="CTRL-0001",
            evaluated_at=datetime(2025, 3, 15),
            entity_type=ComplianceEntityType.PORTFOLIO,
            entity_id="synthetic_governance_state",
            status=ControlStatus.PASS,
            severity=ControlSeverity.HIGH,
            finding_code=FindingCode.DUPLICATE_INVENTORY_ID,
            message="Wrong code.",
        )


def test_risk_indicator_score_is_bounded() -> None:
    with pytest.raises(ValidationError):
        RiskIndicator(
            indicator_id="RI-0001",
            entity_type=ComplianceEntityType.DATASET,
            entity_id="DS-0001",
            category=RiskCategory.DATASET,
            severity=ControlSeverity.CRITICAL,
            score=9,
            rationale="Out of bounds.",
            evaluated_at=datetime(2025, 3, 15),
        )
