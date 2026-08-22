"""Deterministic compliance control evaluation over existing governance state."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from governance_platform.access import (
    AccessControlPortfolio,
    AccessControlService,
    DecisionType,
    GrantStatus,
    RequestStatus,
)
from governance_platform.audit import AuditEventType, AuditLog, EvidencePack, check_completeness
from governance_platform.audit.adapters import request_correlation_id
from governance_platform.compliance.controls import default_control_definitions
from governance_platform.compliance.entities import (
    ComplianceAssessment,
    ComplianceSummary,
    ControlDefinition,
    ControlResult,
)
from governance_platform.compliance.enums import (
    ComplianceEntityType,
    ControlDomain,
    ControlSeverity,
    ControlStatus,
    FindingCode,
)
from governance_platform.compliance.risk import (
    derive_posture,
    derive_risk_indicators,
    total_bounded_risk_score,
)
from governance_platform.inventory import (
    ApprovalStatus,
    InventoryPortfolio,
    LifecycleStatus,
    ResponsibleAIReviewStatus,
    RiskTier,
)

COMPLIANCE_LIMITATIONS: tuple[str, ...] = (
    "This is a local deterministic portfolio simulation, not formal regulatory compliance.",
    "No NHS DSPT, UK GDPR, MHRA, ISO, or other certification is asserted.",
    "No live monitoring, cloud integration, alerting, or production policy enforcement exists.",
    "Risk scores are bounded, explainable control-derived indicators, not predictive modelling.",
)


def _entity_ref(entity_type: ComplianceEntityType, entity_id: str) -> str:
    return f"{entity_type.value}:{entity_id}"


def _audit_ref(event_id: str) -> str:
    return f"audit_event:{event_id}"


def _pass(
    control: ControlDefinition,
    *,
    evaluated_at: datetime,
    entity_type: ComplianceEntityType,
    entity_id: str,
    message: str,
    evidence_refs: tuple[str, ...],
) -> ControlResult:
    return ControlResult(
        result_id="CR-0000",
        control_id=control.control_id,
        evaluated_at=evaluated_at,
        entity_type=entity_type,
        entity_id=entity_id,
        status=ControlStatus.PASS,
        severity=control.severity,
        finding_code=FindingCode.CONTROL_PASSED,
        message=message,
        evidence_refs=evidence_refs,
    )


def _finding(
    control: ControlDefinition,
    *,
    evaluated_at: datetime,
    entity_type: ComplianceEntityType,
    entity_id: str,
    status: ControlStatus,
    finding_code: FindingCode,
    message: str,
    evidence_refs: tuple[str, ...],
) -> ControlResult:
    return ControlResult(
        result_id="CR-0000",
        control_id=control.control_id,
        evaluated_at=evaluated_at,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        severity=control.severity,
        finding_code=finding_code,
        message=message,
        evidence_refs=evidence_refs,
    )


def _active_grants(access_state: AccessControlPortfolio, evaluated_at: datetime):
    return tuple(
        grant
        for grant in sorted(access_state.grants, key=lambda g: g.grant_id)
        if AccessControlService.is_grant_active(grant, evaluated_at)
    )


def _resolve_evidence_refs(
    refs: tuple[str, ...],
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
    audit_log: AuditLog,
    evidence_pack: EvidencePack,
) -> tuple[str, ...]:
    dataset_ids = {d.dataset_id for d in inventory.datasets}
    model_ids = {m.model_id for m in inventory.models}
    project_ids = {p.research_project_id for p in inventory.research_projects}
    request_ids = {r.request_id for r in access_state.requests}
    decision_ids = {d.decision_id for d in access_state.decisions}
    grant_ids = {g.grant_id for g in access_state.grants}
    event_ids = {e.event_id for e in audit_log.events}

    unresolved: list[str] = []
    for ref in refs:
        kind, _, value = ref.partition(":")
        resolved = (
            (kind == "portfolio" and value == "synthetic_governance_state")
            or (kind == "dataset" and value in dataset_ids)
            or (kind == "model" and value in model_ids)
            or (kind == "research_project" and value in project_ids)
            or (kind == "access_request" and value in request_ids)
            or (kind == "approval_decision" and value in decision_ids)
            or (kind == "access_grant" and value in grant_ids)
            or (kind == "audit_log" and value == "audit_events")
            or (kind == "audit_event" and value in event_ids)
            or (kind == "evidence_pack" and value == evidence_pack.evidence_pack_id)
            or (kind == "adr" and value == "0001")
        )
        if not resolved:
            unresolved.append(ref)
    return tuple(unresolved)


class ComplianceEvaluator:
    """Evaluate the fixed Milestone 5 controls and derive posture."""

    def __init__(self, control_definitions: tuple[ControlDefinition, ...] | None = None) -> None:
        self.control_definitions = control_definitions or default_control_definitions()

    def evaluate(
        self,
        inventory: InventoryPortfolio,
        access_state: AccessControlPortfolio,
        audit_log: AuditLog,
        evidence_pack: EvidencePack,
        *,
        assessment_id: str,
        evaluated_at: datetime,
    ) -> ComplianceAssessment:
        raw_results: list[ControlResult] = []
        for control in self.control_definitions:
            if not control.enabled:
                continue
            raw_results.extend(
                self._evaluate_control(
                    control, inventory, access_state, audit_log, evidence_pack, evaluated_at
                )
            )

        results = tuple(
            result.model_copy(update={"result_id": f"CR-{index:04d}"})
            for index, result in enumerate(raw_results, start=1)
        )
        risk_indicators = derive_risk_indicators(
            results, self.control_definitions, evaluated_at=evaluated_at
        )
        posture = derive_posture(results, risk_indicators)
        summary = build_compliance_summary(results, self.control_definitions, posture)

        return ComplianceAssessment(
            assessment_id=assessment_id,
            evaluated_at=evaluated_at,
            scope=(
                "Milestones 2-4 synthetic governance state: inventory, access-control state, "
                "audit log, and evidence pack."
            ),
            control_results=results,
            risk_indicators=risk_indicators,
            posture=posture,
            summary=summary,
            limitations=COMPLIANCE_LIMITATIONS,
        )

    def _evaluate_control(
        self,
        control: ControlDefinition,
        inventory: InventoryPortfolio,
        access_state: AccessControlPortfolio,
        audit_log: AuditLog,
        evidence_pack: EvidencePack,
        evaluated_at: datetime,
    ) -> tuple[ControlResult, ...]:
        dispatch = {
            "CTRL-0001": self._inventory_unique_ids,
            "CTRL-0002": self._inventory_refs_resolve,
            "CTRL-0003": self._synthetic_only,
            "CTRL-0004": self._ownership_metadata,
            "CTRL-0005": self._review_dates,
            "CTRL-0006": self._research_prohibited_not_granted,
            "CTRL-0007": self._granted_datasets_approved,
            "CTRL-0008": self._dataset_sensitivity_present,
            "CTRL-0009": self._dataset_lifecycle_compatible,
            "CTRL-0010": self._approved_high_risk_rai_review,
            "CTRL-0011": self._approved_high_risk_monitoring,
            "CTRL-0012": self._granted_models_approved,
            "CTRL-0013": self._model_dataset_refs_resolve,
            "CTRL-0014": self._high_risk_readiness_tracked,
            "CTRL-0015": self._active_grant_project_approved,
            "CTRL-0016": self._active_grant_project_not_expired,
            "CTRL-0017": self._granted_assets_within_scope,
            "CTRL-0018": self._grant_decision_evidence,
            "CTRL-0019": self._rejected_requests_no_grants,
            "CTRL-0020": self._grants_time_bounded,
            "CTRL-0021": self._inactive_grants_not_active,
            "CTRL-0022": self._audit_completeness,
            "CTRL-0023": self._required_lifecycle_events,
            "CTRL-0024": self._correlation_traceable,
            "CTRL-0025": self._duplicate_audit_ids_absent,
            "CTRL-0026": self._evidence_refs_resolve,
        }
        return dispatch[control.control_id](
            control, inventory, access_state, audit_log, evidence_pack, evaluated_at
        )

    def _inventory_unique_ids(self, control, inventory, *_args):
        ids = (
            [d.dataset_id for d in inventory.datasets]
            + [m.model_id for m in inventory.models]
            + [p.research_project_id for p in inventory.research_projects]
        )
        duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
        if duplicates:
            return tuple(
                _finding(
                    control,
                    evaluated_at=_args[-1],
                    entity_type=ComplianceEntityType.PORTFOLIO,
                    entity_id="synthetic_governance_state",
                    status=ControlStatus.FAIL,
                    finding_code=FindingCode.DUPLICATE_INVENTORY_ID,
                    message=f"Duplicate inventory identifier found: {duplicate}.",
                    evidence_refs=("portfolio:synthetic_governance_state",),
                )
                for duplicate in duplicates
            )
        return (
            _pass(
                control,
                evaluated_at=_args[-1],
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Inventory dataset, model, and project identifiers are unique.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _inventory_refs_resolve(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        dataset_ids = {d.dataset_id for d in inventory.datasets}
        model_ids = {m.model_id for m in inventory.models}
        findings = []
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            for dataset_id in sorted(set(model.linked_dataset_ids) - dataset_ids):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.UNRESOLVED_INVENTORY_REFERENCE,
                        message=f"Model {model.model_id} references unknown dataset {dataset_id}.",
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        for project in sorted(inventory.research_projects, key=lambda p: p.research_project_id):
            for dataset_id in sorted(set(project.linked_dataset_ids) - dataset_ids):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.RESEARCH_PROJECT,
                        entity_id=project.research_project_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.UNRESOLVED_INVENTORY_REFERENCE,
                        message=(
                            f"Project {project.research_project_id} references unknown "
                            f"dataset {dataset_id}."
                        ),
                        evidence_refs=(
                            _entity_ref(
                                ComplianceEntityType.RESEARCH_PROJECT,
                                project.research_project_id,
                            ),
                        ),
                    )
                )
            for model_id in sorted(set(project.linked_model_ids) - model_ids):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.RESEARCH_PROJECT,
                        entity_id=project.research_project_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.UNRESOLVED_INVENTORY_REFERENCE,
                        message=(
                            f"Project {project.research_project_id} references unknown "
                            f"model {model_id}."
                        ),
                        evidence_refs=(
                            _entity_ref(
                                ComplianceEntityType.RESEARCH_PROJECT,
                                project.research_project_id,
                            ),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Inventory references resolve.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _synthetic_only(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        results = []
        for dataset in sorted(inventory.datasets, key=lambda d: d.dataset_id):
            synthetic_only = bool(getattr(dataset, "contains_synthetic_data_only", False))
            if synthetic_only:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        message=f"Dataset {dataset.dataset_id} is marked synthetic only.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                            "adr:0001",
                        ),
                    )
                )
            else:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.SYNTHETIC_DATA_INVARIANT_BROKEN,
                        message=f"Dataset {dataset.dataset_id} is not marked synthetic only.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                        ),
                    )
                )
        return tuple(results)

    def _ownership_metadata(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        results = []
        for dataset in sorted(inventory.datasets, key=lambda d: d.dataset_id):
            if dataset.owner and dataset.steward:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        message=f"Dataset {dataset.dataset_id} has owner and steward metadata.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                        ),
                    )
                )
            else:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.MISSING_STEWARDSHIP_METADATA,
                        message=(
                            f"Dataset {dataset.dataset_id} is missing owner or steward " "metadata."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                        ),
                    )
                )
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            if model.owner:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        message=f"Model {model.model_id} has owner metadata.",
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
            else:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.MISSING_STEWARDSHIP_METADATA,
                        message=f"Model {model.model_id} is missing owner metadata.",
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        return tuple(results)

    def _review_dates(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        results = []
        for dataset in sorted(inventory.datasets, key=lambda d: d.dataset_id):
            if (
                dataset.approval_status == ApprovalStatus.APPROVED
                and dataset.lifecycle_status == LifecycleStatus.ACTIVE
                and dataset.reviewed_at is None
            ):
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        status=ControlStatus.WARNING,
                        finding_code=FindingCode.MISSING_REVIEW_DATE,
                        message=f"Approved active dataset {dataset.dataset_id} has no review date.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                        ),
                    )
                )
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            if (
                model.approval_status == ApprovalStatus.APPROVED
                and model.lifecycle_status == LifecycleStatus.ACTIVE
                and model.reviewed_at is None
            ):
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.WARNING,
                        finding_code=FindingCode.MISSING_REVIEW_DATE,
                        message=f"Approved active model {model.model_id} has no review date.",
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        return tuple(results) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Approved active datasets and models have recorded review dates.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _grant_dataset_control(
        self,
        control,
        inventory,
        access_state,
        evaluated_at,
        *,
        predicate,
        finding_code,
        message,
    ):
        datasets = {d.dataset_id: d for d in inventory.datasets}
        findings = []
        for grant in _active_grants(access_state, evaluated_at):
            for dataset_id in grant.dataset_ids:
                dataset = datasets.get(dataset_id)
                if dataset is not None and predicate(dataset):
                    findings.append(
                        _finding(
                            control,
                            evaluated_at=evaluated_at,
                            entity_type=ComplianceEntityType.ACCESS_GRANT,
                            entity_id=grant.grant_id,
                            status=ControlStatus.FAIL,
                            finding_code=finding_code,
                            message=message(grant.grant_id, dataset_id),
                            evidence_refs=(
                                _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                                _entity_ref(ComplianceEntityType.DATASET, dataset_id),
                            ),
                        )
                    )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="No active grant violates this dataset control.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _research_prohibited_not_granted(self, control, inventory, access_state, *_args):
        return self._grant_dataset_control(
            control,
            inventory,
            access_state,
            _args[-1],
            predicate=lambda dataset: not dataset.research_use_allowed,
            finding_code=FindingCode.RESEARCH_PROHIBITED_DATASET_GRANTED,
            message=lambda grant_id, dataset_id: (
                f"Active grant {grant_id} includes research-prohibited dataset {dataset_id}."
            ),
        )

    def _granted_datasets_approved(self, control, inventory, access_state, *_args):
        return self._grant_dataset_control(
            control,
            inventory,
            access_state,
            _args[-1],
            predicate=lambda dataset: dataset.approval_status != ApprovalStatus.APPROVED,
            finding_code=FindingCode.GRANTED_DATASET_NOT_APPROVED,
            message=lambda grant_id, dataset_id: (
                f"Active grant {grant_id} includes non-approved dataset {dataset_id}."
            ),
        )

    def _dataset_sensitivity_present(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        results = []
        for dataset in sorted(inventory.datasets, key=lambda d: d.dataset_id):
            if getattr(dataset, "sensitivity_classification", None) is None:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.DATASET_SENSITIVITY_MISSING,
                        message=f"Dataset {dataset.dataset_id} has no sensitivity classification.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                        ),
                    )
                )
            else:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.DATASET,
                        entity_id=dataset.dataset_id,
                        message=f"Dataset {dataset.dataset_id} has a sensitivity classification.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.DATASET, dataset.dataset_id),
                        ),
                    )
                )
        return tuple(results)

    def _dataset_lifecycle_compatible(self, control, inventory, access_state, *_args):
        return self._grant_dataset_control(
            control,
            inventory,
            access_state,
            _args[-1],
            predicate=lambda dataset: dataset.lifecycle_status != LifecycleStatus.ACTIVE,
            finding_code=FindingCode.DATASET_LIFECYCLE_INCOMPATIBLE,
            message=lambda grant_id, dataset_id: (
                f"Active grant {grant_id} includes inactive-lifecycle dataset {dataset_id}."
            ),
        )

    def _approved_high_risk_rai_review(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        findings = []
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            if (
                model.risk_tier == RiskTier.HIGH
                and model.approval_status == ApprovalStatus.APPROVED
                and model.responsible_ai_review_status != ResponsibleAIReviewStatus.APPROVED
            ):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.HIGH_RISK_MODEL_RAI_REVIEW_MISSING,
                        message=(
                            f"Approved high-risk model {model.model_id} lacks approved "
                            "responsible-AI review."
                        ),
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="No approved high-risk model lacks approved responsible-AI review.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _approved_high_risk_monitoring(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        findings = []
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            if (
                model.risk_tier == RiskTier.HIGH
                and model.approval_status == ApprovalStatus.APPROVED
                and not model.monitoring_required
            ):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.HIGH_RISK_MODEL_MONITORING_MISSING,
                        message=f"Approved high-risk model {model.model_id} lacks monitoring.",
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Approved high-risk models require monitoring.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _granted_models_approved(self, control, inventory, access_state, *_args):
        evaluated_at = _args[-1]
        models = {m.model_id: m for m in inventory.models}
        findings = []
        for grant in _active_grants(access_state, evaluated_at):
            for model_id in grant.model_ids:
                model = models.get(model_id)
                if model is not None and model.approval_status != ApprovalStatus.APPROVED:
                    findings.append(
                        _finding(
                            control,
                            evaluated_at=evaluated_at,
                            entity_type=ComplianceEntityType.ACCESS_GRANT,
                            entity_id=grant.grant_id,
                            status=ControlStatus.FAIL,
                            finding_code=FindingCode.GRANTED_MODEL_NOT_APPROVED,
                            message=(
                                f"Active grant {grant.grant_id} includes non-approved model "
                                f"{model_id}."
                            ),
                            evidence_refs=(
                                _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                                _entity_ref(ComplianceEntityType.MODEL, model_id),
                            ),
                        )
                    )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="No active grant includes a non-approved model.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _model_dataset_refs_resolve(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        dataset_ids = {d.dataset_id for d in inventory.datasets}
        findings = []
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            for dataset_id in sorted(set(model.linked_dataset_ids) - dataset_ids):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.MODEL_DATASET_REFERENCE_UNRESOLVED,
                        message=f"Model {model.model_id} references unknown dataset {dataset_id}.",
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Model linked dataset references resolve.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _high_risk_readiness_tracked(self, control, inventory, *_args):
        evaluated_at = _args[-1]
        results = []
        for model in sorted(inventory.models, key=lambda m: m.model_id):
            if model.risk_tier != RiskTier.HIGH:
                continue
            if model.approval_status == ApprovalStatus.APPROVED:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        message=(
                            f"High-risk model {model.model_id} is approved and readiness-gated."
                        ),
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
            else:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.MODEL,
                        entity_id=model.model_id,
                        status=ControlStatus.WARNING,
                        finding_code=FindingCode.HIGH_RISK_MODEL_REVIEW_PENDING,
                        message=(
                            f"High-risk model {model.model_id} is {model.approval_status.value}; "
                            "not ready for approved use."
                        ),
                        evidence_refs=(_entity_ref(ComplianceEntityType.MODEL, model.model_id),),
                    )
                )
        return tuple(results) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="No high-risk models require readiness tracking.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _active_grant_project_approved(self, control, inventory, access_state, *_args):
        evaluated_at = _args[-1]
        projects = {p.research_project_id: p for p in inventory.research_projects}
        findings = []
        for grant in _active_grants(access_state, evaluated_at):
            project = projects.get(grant.research_project_id)
            if project is None or project.approval_status != ApprovalStatus.APPROVED:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.ACTIVE_GRANT_PROJECT_NOT_APPROVED,
                        message=(
                            f"Active grant {grant.grant_id} does not reference an approved "
                            "project."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Active grants reference approved projects.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _active_grant_project_not_expired(self, control, inventory, access_state, *_args):
        evaluated_at = _args[-1]
        projects = {p.research_project_id: p for p in inventory.research_projects}
        findings = []
        for grant in _active_grants(access_state, evaluated_at):
            project = projects.get(grant.research_project_id)
            if project is not None and evaluated_at.date() > project.expiry_date:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.ACTIVE_GRANT_PROJECT_EXPIRED,
                        message=(
                            f"Active grant {grant.grant_id} references project "
                            f"{project.research_project_id} expired on {project.expiry_date}."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                            _entity_ref(
                                ComplianceEntityType.RESEARCH_PROJECT,
                                project.research_project_id,
                            ),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Active grant projects are unexpired at evaluation time.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _granted_assets_within_scope(self, control, inventory, access_state, *_args):
        evaluated_at = _args[-1]
        projects = {p.research_project_id: p for p in inventory.research_projects}
        findings = []
        for grant in _active_grants(access_state, evaluated_at):
            project = projects.get(grant.research_project_id)
            if project is None:
                continue
            extra_datasets = sorted(set(grant.dataset_ids) - set(project.linked_dataset_ids))
            extra_models = sorted(set(grant.model_ids) - set(project.linked_model_ids))
            if extra_datasets or extra_models:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.GRANTED_ASSET_OUT_OF_SCOPE,
                        message=(
                            f"Active grant {grant.grant_id} has out-of-scope datasets "
                            f"{extra_datasets} and models {extra_models}."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                            _entity_ref(
                                ComplianceEntityType.RESEARCH_PROJECT,
                                project.research_project_id,
                            ),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Granted assets are within project scope.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _grant_decision_evidence(self, control, _inventory, access_state, audit_log, *_args):
        evaluated_at = _args[-1]
        findings = []
        events_by_grant = {
            grant_id: audit_log.filter_by_grant(grant_id)
            for grant_id in sorted(g.grant_id for g in access_state.grants)
        }
        for grant in sorted(access_state.grants, key=lambda g: g.grant_id):
            decision = access_state.decision_for_request(grant.request_id)
            grant_events = events_by_grant[grant.grant_id]
            created_events = [
                event for event in grant_events if event.event_type == AuditEventType.GRANT_CREATED
            ]
            if decision is None or decision.decision != DecisionType.APPROVED or not created_events:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.GRANT_MISSING_APPROVAL_EVIDENCE,
                        message=(
                            f"Grant {grant.grant_id} lacks approved decision or creation "
                            "evidence."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
            else:
                findings.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        message=f"Grant {grant.grant_id} traces to approved decision evidence.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                            _entity_ref(
                                ComplianceEntityType.APPROVAL_DECISION,
                                decision.decision_id,
                            ),
                            _audit_ref(created_events[0].event_id),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="No grants are present.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _rejected_requests_no_grants(self, control, _inventory, access_state, *_args):
        evaluated_at = _args[-1]
        findings = []
        grants_by_request = {
            request_id: access_state.grants_for_request(request_id)
            for request_id in sorted(r.request_id for r in access_state.requests)
        }
        for request in sorted(access_state.requests, key=lambda r: r.request_id):
            if request.status == RequestStatus.REJECTED and grants_by_request[request.request_id]:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_REQUEST,
                        entity_id=request.request_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.REJECTED_REQUEST_HAS_GRANT,
                        message=f"Rejected request {request.request_id} has a grant.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_REQUEST, request.request_id),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.PORTFOLIO,
                entity_id="synthetic_governance_state",
                message="Rejected requests do not produce grants.",
                evidence_refs=("portfolio:synthetic_governance_state",),
            ),
        )

    def _grants_time_bounded(self, control, _inventory, access_state, *_args):
        evaluated_at = _args[-1]
        results = []
        for grant in sorted(access_state.grants, key=lambda g: g.grant_id):
            if grant.expires_at <= grant.granted_at:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.GRANT_NOT_TIME_BOUNDED,
                        message=f"Grant {grant.grant_id} is not time-bounded.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
            else:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        message=f"Grant {grant.grant_id} is time-bounded.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
        return tuple(results)

    def _inactive_grants_not_active(self, control, _inventory, access_state, *_args):
        evaluated_at = _args[-1]
        results = []
        for grant in sorted(access_state.grants, key=lambda g: g.grant_id):
            is_active = AccessControlService.is_grant_active(grant, evaluated_at)
            should_be_inactive = (
                grant.status == GrantStatus.REVOKED or evaluated_at > grant.expires_at
            )
            if should_be_inactive and is_active:
                results.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.INACTIVE_GRANT_STILL_ACTIVE,
                        message=(
                            f"Grant {grant.grant_id} is revoked or expired but evaluates " "active."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
            else:
                results.append(
                    _pass(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        message=f"Grant {grant.grant_id} activity classification is coherent.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
        return tuple(results)

    def _audit_completeness(self, control, inventory, access_state, audit_log, *_args):
        evaluated_at = _args[-1]
        problems = check_completeness(audit_log, inventory, access_state)
        if problems:
            return tuple(
                _finding(
                    control,
                    evaluated_at=evaluated_at,
                    entity_type=ComplianceEntityType.AUDIT_LOG,
                    entity_id="audit_events",
                    status=ControlStatus.FAIL,
                    finding_code=FindingCode.AUDIT_COMPLETENESS_PROBLEM,
                    message=problem,
                    evidence_refs=("audit_log:audit_events",),
                )
                for problem in problems
            )
        return (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.AUDIT_LOG,
                entity_id="audit_events",
                message="Audit completeness checker reports no missing expected evidence.",
                evidence_refs=("audit_log:audit_events",),
            ),
        )

    def _required_lifecycle_events(self, control, _inventory, access_state, audit_log, *_args):
        evaluated_at = _args[-1]
        findings = []
        for request in sorted(access_state.requests, key=lambda r: r.request_id):
            event_types = {
                event.event_type for event in audit_log.filter_by_request(request.request_id)
            }
            required = {AuditEventType.ACCESS_REQUESTED, AuditEventType.ACCESS_EVALUATED}
            decision = access_state.decision_for_request(request.request_id)
            if decision is not None:
                required.add(
                    AuditEventType.ACCESS_APPROVED
                    if decision.decision == DecisionType.APPROVED
                    else AuditEventType.ACCESS_REJECTED
                )
            missing = sorted(event.value for event in required - event_types)
            if missing:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_REQUEST,
                        entity_id=request.request_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.REQUIRED_LIFECYCLE_EVENT_MISSING,
                        message=f"Request {request.request_id} is missing events: {missing}.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_REQUEST, request.request_id),
                        ),
                    )
                )
        for grant in sorted(access_state.grants, key=lambda g: g.grant_id):
            event_types = {event.event_type for event in audit_log.filter_by_grant(grant.grant_id)}
            required = {AuditEventType.GRANT_CREATED}
            if grant.status == GrantStatus.REVOKED:
                required.add(AuditEventType.GRANT_REVOKED)
            elif not AccessControlService.is_grant_active(grant, evaluated_at):
                required.add(AuditEventType.GRANT_EXPIRED)
            missing = sorted(event.value for event in required - event_types)
            if missing:
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_GRANT,
                        entity_id=grant.grant_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.REQUIRED_LIFECYCLE_EVENT_MISSING,
                        message=f"Grant {grant.grant_id} is missing events: {missing}.",
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_GRANT, grant.grant_id),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.AUDIT_LOG,
                entity_id="audit_events",
                message="Required lifecycle events exist.",
                evidence_refs=("audit_log:audit_events",),
            ),
        )

    def _correlation_traceable(self, control, _inventory, access_state, audit_log, *_args):
        evaluated_at = _args[-1]
        findings = []
        for request in sorted(access_state.requests, key=lambda r: r.request_id):
            correlation_id = request_correlation_id(request.request_id)
            group = audit_log.filter_by_correlation_id(correlation_id)
            if not group or any(event.request_id != request.request_id for event in group):
                findings.append(
                    _finding(
                        control,
                        evaluated_at=evaluated_at,
                        entity_type=ComplianceEntityType.ACCESS_REQUEST,
                        entity_id=request.request_id,
                        status=ControlStatus.FAIL,
                        finding_code=FindingCode.CORRELATION_CHAIN_NOT_TRACEABLE,
                        message=(
                            f"Request {request.request_id} lacks a traceable correlation " "chain."
                        ),
                        evidence_refs=(
                            _entity_ref(ComplianceEntityType.ACCESS_REQUEST, request.request_id),
                        ),
                    )
                )
        return tuple(findings) or (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.AUDIT_LOG,
                entity_id="audit_events",
                message="Request correlation chains are traceable.",
                evidence_refs=("audit_log:audit_events",),
            ),
        )

    def _duplicate_audit_ids_absent(self, control, _inventory, _access_state, audit_log, *_args):
        evaluated_at = _args[-1]
        duplicates = sorted(
            event_id
            for event_id, count in Counter(e.event_id for e in audit_log.events).items()
            if count > 1
        )
        if duplicates:
            return tuple(
                _finding(
                    control,
                    evaluated_at=evaluated_at,
                    entity_type=ComplianceEntityType.AUDIT_LOG,
                    entity_id="audit_events",
                    status=ControlStatus.FAIL,
                    finding_code=FindingCode.DUPLICATE_AUDIT_EVENT_ID,
                    message=f"Duplicate audit event id found: {event_id}.",
                    evidence_refs=("audit_log:audit_events",),
                )
                for event_id in duplicates
            )
        return (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.AUDIT_LOG,
                entity_id="audit_events",
                message="Audit event identifiers are unique.",
                evidence_refs=("audit_log:audit_events",),
            ),
        )

    def _evidence_refs_resolve(
        self, control, inventory, access_state, audit_log, evidence_pack, evaluated_at
    ):
        prior_results = []
        for existing_control in self.control_definitions:
            if existing_control.control_id == control.control_id:
                break
            if existing_control.enabled:
                prior_results.extend(
                    self._evaluate_control(
                        existing_control,
                        inventory,
                        access_state,
                        audit_log,
                        evidence_pack,
                        evaluated_at,
                    )
                )
        refs = tuple(ref for result in prior_results for ref in result.evidence_refs)
        unresolved = _resolve_evidence_refs(refs, inventory, access_state, audit_log, evidence_pack)
        if unresolved:
            return tuple(
                _finding(
                    control,
                    evaluated_at=evaluated_at,
                    entity_type=ComplianceEntityType.EVIDENCE_PACK,
                    entity_id=evidence_pack.evidence_pack_id,
                    status=ControlStatus.FAIL,
                    finding_code=FindingCode.EVIDENCE_REFERENCE_UNRESOLVED,
                    message=f"Evidence reference does not resolve: {ref}.",
                    evidence_refs=(f"evidence_pack:{evidence_pack.evidence_pack_id}",),
                )
                for ref in unresolved
            )
        return (
            _pass(
                control,
                evaluated_at=evaluated_at,
                entity_type=ComplianceEntityType.EVIDENCE_PACK,
                entity_id=evidence_pack.evidence_pack_id,
                message="Compliance evidence references resolve in source state.",
                evidence_refs=(f"evidence_pack:{evidence_pack.evidence_pack_id}",),
            ),
        )


def build_compliance_summary(
    control_results: tuple[ControlResult, ...],
    control_definitions: tuple[ControlDefinition, ...],
    posture,
) -> ComplianceSummary:
    """Compute deterministic aggregate metrics for assessment outputs."""
    definitions_by_id = {control.control_id: control for control in control_definitions}
    non_pass = [result for result in control_results if result.status != ControlStatus.PASS]
    total = len(control_results)
    passed = sum(1 for result in control_results if result.status == ControlStatus.PASS)
    warnings = sum(1 for result in control_results if result.status == ControlStatus.WARNING)
    failed = sum(1 for result in control_results if result.status == ControlStatus.FAIL)
    indicators = derive_risk_indicators(
        control_results,
        control_definitions,
        evaluated_at=control_results[0].evaluated_at if control_results else datetime(1970, 1, 1),
    )

    return ComplianceSummary(
        total_controls_evaluated=total,
        passed_controls=passed,
        warning_controls=warnings,
        failed_controls=failed,
        pass_rate=round(passed / total, 4) if total else 0,
        findings_by_severity={
            severity.value: sum(1 for result in non_pass if result.severity == severity)
            for severity in ControlSeverity
        },
        findings_by_domain={
            domain.value: sum(
                1
                for result in non_pass
                if definitions_by_id[result.control_id].control_domain == domain
            )
            for domain in ControlDomain
        },
        number_of_risk_indicators=len(indicators),
        total_bounded_risk_score=total_bounded_risk_score(indicators),
        overall_posture=posture,
    )


def evaluate_compliance(
    inventory: InventoryPortfolio,
    access_state: AccessControlPortfolio,
    audit_log: AuditLog,
    evidence_pack: EvidencePack,
    *,
    assessment_id: str,
    evaluated_at: datetime,
    control_definitions: tuple[ControlDefinition, ...] | None = None,
) -> ComplianceAssessment:
    """Evaluate all enabled controls and return the full assessment."""
    return ComplianceEvaluator(control_definitions).evaluate(
        inventory,
        access_state,
        audit_log,
        evidence_pack,
        assessment_id=assessment_id,
        evaluated_at=evaluated_at,
    )
