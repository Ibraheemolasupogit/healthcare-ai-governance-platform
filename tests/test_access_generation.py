from governance_platform.access import (
    REFERENCE_EVALUATION_TIME,
    AccessControlService,
    DecisionType,
    GrantStatus,
    RejectionReasonCode,
    RequestStatus,
    generate_access_control_state,
)
from governance_platform.access.policy import evaluate_eligibility
from governance_platform.inventory import generate_portfolio


def test_generation_is_deterministic() -> None:
    first = generate_access_control_state()
    second = generate_access_control_state()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_generated_state_is_restrained() -> None:
    state = generate_access_control_state()

    assert 5 <= len(state.requests) <= 15
    assert len(state.decisions) == len(state.requests)
    assert 2 <= len(state.grants) <= 6


def test_generated_state_has_approved_and_rejected_requests() -> None:
    state = generate_access_control_state()
    statuses = {r.status for r in state.requests}

    assert RequestStatus.APPROVED in statuses
    assert RequestStatus.REJECTED in statuses


def test_every_decision_matches_its_finalized_request_status() -> None:
    state = generate_access_control_state()

    for request in state.requests:
        decision = state.decision_for_request(request.request_id)
        assert decision is not None
        expected = (
            RequestStatus.APPROVED
            if decision.decision == DecisionType.APPROVED
            else RequestStatus.REJECTED
        )
        assert request.status == expected


def test_rejected_requests_cover_each_required_scenario() -> None:
    inventory = generate_portfolio()
    state = generate_access_control_state()

    all_codes: set[RejectionReasonCode] = set()
    for decision in state.decisions:
        if decision.decision != DecisionType.REJECTED:
            continue
        request = state.request_by_id(decision.request_id)
        result = evaluate_eligibility(request, inventory)
        all_codes.update(v.code for v in result.violations)

    assert RejectionReasonCode.UNKNOWN_RESEARCH_PROJECT in all_codes
    assert RejectionReasonCode.RESEARCH_PROJECT_NOT_APPROVED in all_codes
    assert RejectionReasonCode.RESEARCH_PROJECT_EXPIRED in all_codes
    assert RejectionReasonCode.UNKNOWN_DATASET in all_codes
    assert RejectionReasonCode.UNKNOWN_MODEL in all_codes
    assert RejectionReasonCode.DATASET_NOT_LINKED_TO_PROJECT in all_codes
    assert RejectionReasonCode.RESEARCH_USE_NOT_ALLOWED in all_codes
    assert RejectionReasonCode.REQUESTED_DURATION_EXCEEDS_PROJECT_EXPIRY in all_codes


def test_grants_cover_active_expired_and_revoked() -> None:
    state = generate_access_control_state()

    active = [
        g
        for g in state.grants
        if AccessControlService.is_grant_active(g, REFERENCE_EVALUATION_TIME)
    ]
    revoked = [g for g in state.grants if g.status == GrantStatus.REVOKED]
    expired = AccessControlService.expired_grants(state.grants, REFERENCE_EVALUATION_TIME)

    assert len(active) == 1
    assert len(revoked) == 1
    assert len(expired) == 1


def test_no_rejected_request_has_a_grant() -> None:
    state = generate_access_control_state()
    rejected_request_ids = {
        r.request_id for r in state.requests if r.status == RequestStatus.REJECTED
    }

    for grant in state.grants:
        assert grant.request_id not in rejected_request_ids


def test_identities_are_role_based_not_real_names() -> None:
    state = generate_access_control_state()

    identities = [r.requester_id for r in state.requests] + [d.approver_id for d in state.decisions]
    assert identities
    assert all(identity.startswith(("researcher-", "access-approver-")) for identity in identities)


def test_no_patient_level_fields_present() -> None:
    state = generate_access_control_state()
    dumped = state.model_dump(mode="json")

    forbidden_markers = ("patient", "mrn", "date_of_birth", "ssn")
    blob = str(dumped).lower()
    assert not any(marker in blob for marker in forbidden_markers)
