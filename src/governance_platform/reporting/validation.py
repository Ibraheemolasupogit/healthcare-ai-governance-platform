"""Validation helpers for reporting snapshots and source references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from governance_platform.access import AccessControlPortfolio
from governance_platform.audit import AuditLog, EvidencePack
from governance_platform.compliance import ComplianceAssessment
from governance_platform.inventory import InventoryPortfolio
from governance_platform.reporting.entities import ReportingSnapshot


def _format_error(error: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in error["loc"]) or "<reporting snapshot>"
    return f"{location}: {error['msg']}"


def validate_reporting_snapshot_data(data: dict[str, Any]) -> list[str]:
    """Validate raw reporting snapshot data without raising."""
    try:
        ReportingSnapshot.model_validate(data)
    except ValidationError as exc:
        return [_format_error(error) for error in exc.errors()]
    return []


def validate_reporting_snapshot_file(input_dir: str | Path) -> list[str]:
    """Validate the canonical reporting snapshot JSON in ``input_dir``."""
    from governance_platform.reporting.io import REPORTING_SNAPSHOT_FILENAME

    path = Path(input_dir) / REPORTING_SNAPSHOT_FILENAME
    if not path.is_file():
        return [f"reporting snapshot file not found: {path}"]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON ({exc})"]

    return validate_reporting_snapshot_data(raw)


def unresolved_source_refs(
    snapshot: ReportingSnapshot,
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
    audit_log: AuditLog,
    evidence_pack: EvidencePack,
    compliance_assessment: ComplianceAssessment,
) -> tuple[str, ...]:
    """Return source references from KPI rows that do not resolve in supplied state."""
    valid_refs = {
        "inventory_portfolio",
        "access_control_state",
        "audit_events",
        "control_results",
        "risk_indicators",
        "adr:0001",
        f"evidence_pack:{evidence_pack.evidence_pack_id}",
        f"compliance_assessment:{compliance_assessment.assessment_id}",
    }
    valid_refs.update(f"dataset:{dataset.dataset_id}" for dataset in inventory.datasets)
    valid_refs.update(f"model:{model.model_id}" for model in inventory.models)
    valid_refs.update(
        f"research_project:{project.research_project_id}" for project in inventory.research_projects
    )
    valid_refs.update(f"access_request:{request.request_id}" for request in access_state.requests)
    valid_refs.update(f"access_grant:{grant.grant_id}" for grant in access_state.grants)
    valid_refs.update(f"audit_event:{event.event_id}" for event in audit_log.events)

    unresolved = sorted(
        {
            ref
            for metric in snapshot.all_metrics
            for ref in metric.source_refs
            if ref not in valid_refs
        }
    )
    return tuple(unresolved)
