from datetime import datetime

from governance_platform.access import (
    AccessControlPortfolio,
    AccessGrant,
    AccessRequest,
    ApprovalDecision,
    DecisionType,
    RequesterRole,
    RequestStatus,
    generate_access_control_state,
)
from governance_platform.audit import (
    AuditEventType,
    AuditLog,
    build_evidence_pack,
    generate_audit_log,
)
from governance_platform.compliance import (
    ControlSeverity,
    ControlStatus,
    FindingCode,
    GovernancePosture,
    evaluate_compliance,
)
from governance_platform.compliance.risk import (
    MAX_TOTAL_RISK_SCORE,
    derive_posture,
    total_bounded_risk_score,
)
from governance_platform.inventory import (
    AIModel,
    ApprovalStatus,
    Dataset,
    InventoryPortfolio,
    ResponsibleAIReviewStatus,
    generate_portfolio,
)

EVALUATED_AT = datetime(2025, 3, 15)
EVIDENCE_AT = datetime(2025, 3, 20)


def _assessment(
    inventory: InventoryPortfolio | None = None,
    access_state: AccessControlPortfolio | None = None,
    audit_log: AuditLog | None = None,
):
    inventory = inventory or generate_portfolio()
    access_state = access_state or generate_access_control_state()
    audit_log = audit_log or generate_audit_log(inventory, access_state, evaluated_at=EVALUATED_AT)
    evidence_pack = build_evidence_pack(
        inventory,
        access_state,
        audit_log,
        evidence_pack_id="EVP-0001",
        generated_at=EVIDENCE_AT,
        evaluated_at=EVALUATED_AT,
    )
    return evaluate_compliance(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id="CA-0001",
        evaluated_at=EVALUATED_AT,
    )


def _active_bad_grant(dataset_ids=(), model_ids=()) -> AccessControlPortfolio:
    request = AccessRequest(
        request_id="AR-9001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        requested_dataset_ids=dataset_ids,
        requested_model_ids=model_ids,
        purpose="Used only in tests.",
        requested_at=datetime(2025, 1, 1),
        requested_until=datetime(2025, 4, 1),
        status=RequestStatus.APPROVED,
    )
    decision = ApprovalDecision(
        decision_id="AD-9001",
        request_id="AR-9001",
        approver_id="access-approver-test-01",
        decision=DecisionType.APPROVED,
        decision_reason="Test fixture.",
        decided_at=datetime(2025, 1, 2),
    )
    grant = AccessGrant(
        grant_id="AG-9001",
        request_id="AR-9001",
        research_project_id="RP-0001",
        requester_id="researcher-test-01",
        dataset_ids=dataset_ids,
        model_ids=model_ids,
        granted_at=datetime(2025, 1, 3),
        expires_at=datetime(2025, 4, 1),
    )
    return AccessControlPortfolio(requests=(request,), decisions=(decision,), grants=(grant,))


def test_canonical_assessment_is_deterministic_and_ordered() -> None:
    first = _assessment()
    second = _assessment()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [r.result_id for r in first.control_results] == [
        f"CR-{index:04d}" for index in range(1, len(first.control_results) + 1)
    ]
    assert [r.control_id for r in first.control_results] == sorted(
        r.control_id for r in first.control_results
    )


def test_canonical_assessment_warns_only_for_pending_high_risk_model_readiness() -> None:
    assessment = _assessment()

    findings = [r for r in assessment.control_results if r.status != ControlStatus.PASS]
    assert [(r.finding_code, r.entity_id) for r in findings] == [
        (FindingCode.HIGH_RISK_MODEL_REVIEW_PENDING, "MD-0003")
    ]
    assert assessment.summary.warning_controls == 1
    assert assessment.summary.failed_controls == 0
    assert assessment.summary.total_bounded_risk_score == 3
    assert assessment.posture == GovernancePosture.ATTENTION_REQUIRED


def test_inventory_controls_report_synthetic_safeguard_break() -> None:
    inventory = generate_portfolio()
    bad_dataset = Dataset.model_construct(
        **{**inventory.datasets[0].model_dump(mode="python"), "contains_synthetic_data_only": False}
    )
    bad_inventory = InventoryPortfolio.model_construct(
        datasets=(bad_dataset, *inventory.datasets[1:]),
        models=inventory.models,
        research_projects=inventory.research_projects,
    )
    assessment = _assessment(inventory=bad_inventory)

    assert any(
        result.finding_code == FindingCode.SYNTHETIC_DATA_INVARIANT_BROKEN
        and result.severity == ControlSeverity.CRITICAL
        for result in assessment.control_results
    )
    assert assessment.posture == GovernancePosture.HIGH_RISK


def test_dataset_controls_report_research_prohibited_active_grant() -> None:
    assessment = _assessment(access_state=_active_bad_grant(dataset_ids=("DS-0006",)))

    codes = {result.finding_code for result in assessment.control_results}
    assert FindingCode.RESEARCH_PROHIBITED_DATASET_GRANTED in codes
    assert FindingCode.DATASET_LIFECYCLE_INCOMPATIBLE in codes


def test_model_controls_report_non_approved_granted_model_and_high_risk_review_gap() -> None:
    inventory = generate_portfolio()
    bad_model = AIModel.model_construct(
        **{
            **inventory.models[2].model_dump(mode="python"),
            "approval_status": ApprovalStatus.APPROVED,
            "responsible_ai_review_status": ResponsibleAIReviewStatus.IN_PROGRESS,
            "monitoring_required": False,
        }
    )
    bad_inventory = InventoryPortfolio.model_construct(
        datasets=inventory.datasets,
        models=(*inventory.models[:2], bad_model, *inventory.models[3:]),
        research_projects=inventory.research_projects,
    )
    assessment = _assessment(
        inventory=bad_inventory,
        access_state=_active_bad_grant(dataset_ids=("DS-0003",), model_ids=("MD-0003",)),
    )
    codes = {result.finding_code for result in assessment.control_results}

    assert FindingCode.HIGH_RISK_MODEL_RAI_REVIEW_MISSING in codes
    assert FindingCode.HIGH_RISK_MODEL_MONITORING_MISSING in codes


def test_research_controls_report_out_of_scope_asset() -> None:
    assessment = _assessment(access_state=_active_bad_grant(dataset_ids=("DS-0001",)))

    assert any(
        result.finding_code == FindingCode.GRANTED_ASSET_OUT_OF_SCOPE
        for result in assessment.control_results
    )


def test_access_controls_report_grant_without_audit_creation_evidence() -> None:
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    audit_log = generate_audit_log(inventory, access_state, evaluated_at=EVALUATED_AT)
    incomplete_log = AuditLog(
        events=tuple(
            event
            for event in audit_log.events
            if not (
                event.event_type == AuditEventType.GRANT_CREATED and event.grant_id == "AG-0001"
            )
        )
    )
    assessment = _assessment(
        inventory=inventory, access_state=access_state, audit_log=incomplete_log
    )

    codes = {result.finding_code for result in assessment.control_results}
    assert FindingCode.GRANT_MISSING_APPROVAL_EVIDENCE in codes
    assert FindingCode.AUDIT_COMPLETENESS_PROBLEM in codes
    assert FindingCode.REQUIRED_LIFECYCLE_EVENT_MISSING in codes


def test_access_controls_report_rejected_request_with_grant() -> None:
    request = AccessRequest(
        request_id="AR-9001",
        requester_id="researcher-test-01",
        requester_role=RequesterRole.RESEARCHER,
        research_project_id="RP-0001",
        requested_dataset_ids=("DS-0002",),
        purpose="Used only in tests.",
        requested_at=datetime(2025, 1, 1),
        requested_until=datetime(2025, 4, 1),
        status=RequestStatus.REJECTED,
    )
    decision = ApprovalDecision(
        decision_id="AD-9001",
        request_id="AR-9001",
        approver_id="access-approver-test-01",
        decision=DecisionType.APPROVED,
        decision_reason="Malformed fixture to test compliance monitoring.",
        decided_at=datetime(2025, 1, 2),
    )
    grant = AccessGrant(
        grant_id="AG-9001",
        request_id="AR-9001",
        research_project_id="RP-0001",
        requester_id="researcher-test-01",
        dataset_ids=("DS-0002",),
        granted_at=datetime(2025, 1, 3),
        expires_at=datetime(2025, 4, 1),
    )
    access_state = AccessControlPortfolio(
        requests=(request,), decisions=(decision,), grants=(grant,)
    )
    assessment = _assessment(access_state=access_state)

    assert any(
        result.finding_code == FindingCode.REJECTED_REQUEST_HAS_GRANT
        for result in assessment.control_results
    )


def test_risk_score_is_bounded_and_posture_thresholds_are_explicit() -> None:
    assessment = _assessment(access_state=_active_bad_grant(dataset_ids=("DS-0006",)))

    assert total_bounded_risk_score(assessment.risk_indicators) <= MAX_TOTAL_RISK_SCORE
    assert derive_posture((), ()) == GovernancePosture.HEALTHY
    assert assessment.posture in {
        GovernancePosture.ATTENTION_REQUIRED,
        GovernancePosture.HIGH_RISK,
    }


def test_evidence_references_resolve_for_canonical_assessment() -> None:
    assessment = _assessment()

    evidence_ref_results = [
        result for result in assessment.control_results if result.control_id == "CTRL-0026"
    ]
    assert evidence_ref_results[0].status == ControlStatus.PASS


def test_canonical_assessment_keeps_synthetic_data_safeguards_visible() -> None:
    assessment = _assessment()

    synthetic_results = [
        result for result in assessment.control_results if result.control_id == "CTRL-0003"
    ]
    assert len(synthetic_results) == len(generate_portfolio().datasets)
    assert all("adr:0001" in result.evidence_refs for result in synthetic_results)
