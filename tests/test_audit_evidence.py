from datetime import datetime

from governance_platform.access import REFERENCE_EVALUATION_TIME, generate_access_control_state
from governance_platform.audit import build_evidence_pack, generate_audit_log
from governance_platform.inventory import generate_portfolio

_GENERATED_AT = datetime(2025, 3, 20)


def _pack():
    inventory = generate_portfolio()
    access_state = generate_access_control_state()
    log = generate_audit_log(inventory, access_state, evaluated_at=REFERENCE_EVALUATION_TIME)
    return build_evidence_pack(
        inventory,
        access_state,
        log,
        evidence_pack_id="EVP-0001",
        generated_at=_GENERATED_AT,
        evaluated_at=REFERENCE_EVALUATION_TIME,
    )


def test_evidence_pack_generation_is_deterministic() -> None:
    first = _pack()
    second = _pack()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_evidence_pack_header_fields() -> None:
    pack = _pack()
    assert pack.evidence_pack_id == "EVP-0001"
    assert pack.generated_at == _GENERATED_AT
    assert pack.scope
    assert pack.source_systems


def test_evidence_pack_inventory_evidence_matches_inventory() -> None:
    pack = _pack()
    assert pack.inventory_evidence.dataset_count == 6
    assert pack.inventory_evidence.model_count == 5
    assert pack.inventory_evidence.research_project_count == 4


def test_evidence_pack_rejected_access_matches_rejected_requests() -> None:
    pack = _pack()
    assert len(pack.rejected_access) == 7
    assert {r.request_id for r in pack.rejected_access} == {
        f"AR-{i:04d}" for i in (2, 3, 4, 5, 6, 7, 8)
    }


def test_evidence_pack_grant_statuses() -> None:
    pack = _pack()
    statuses = {g.grant_id: g.status_as_of_evaluation for g in pack.grants}
    assert statuses == {"AG-0001": "active", "AG-0002": "expired", "AG-0003": "revoked"}


def test_evidence_pack_correlation_groups_cover_every_request_and_inventory() -> None:
    pack = _pack()
    correlation_ids = {g.correlation_id for g in pack.correlation_groups}
    assert "CORR-INVENTORY-0001" in correlation_ids
    assert all(f"CORR-AR-{i:04d}" in correlation_ids for i in range(1, 11))


def test_evidence_pack_is_complete_for_generated_scenarios() -> None:
    pack = _pack()
    assert pack.completeness.complete is True
    assert pack.completeness.problems == ()


def test_evidence_pack_has_limitations() -> None:
    pack = _pack()
    assert len(pack.limitations) > 0
    assert any("simulation" in limitation.lower() for limitation in pack.limitations)


def test_evidence_pack_does_not_claim_production_or_regulatory_status() -> None:
    pack = _pack()
    # These positive-claim phrasings must never appear — the pack should only
    # ever *disclaim* production/regulatory status, never assert it.
    forbidden_claims = (
        "has regulatory approval",
        "is a production audit trail",
        "is certified",
        "regulatory certification obtained",
    )
    full_text = str(pack.model_dump(mode="json")).lower()
    assert not any(claim in full_text for claim in forbidden_claims)
    # The limitations section explicitly disclaims both.
    limitations_text = " ".join(pack.limitations).lower()
    assert "not a production audit trail" in limitations_text
    assert "no enterprise risk score, regulatory certification" in limitations_text


def test_evidence_pack_contains_no_patient_level_markers() -> None:
    pack = _pack()
    blob = str(pack.model_dump(mode="json")).lower()
    forbidden_markers = ("patient", "mrn", "date_of_birth", "ssn")
    assert not any(marker in blob for marker in forbidden_markers)


def test_evidence_pack_does_not_duplicate_full_dataset_records() -> None:
    pack = _pack()
    # Inventory evidence is counts/breakdowns only — no dataset name/description
    # fields are carried into the pack.
    dumped = pack.inventory_evidence.model_dump()
    assert "name" not in dumped
    assert "description" not in dumped
