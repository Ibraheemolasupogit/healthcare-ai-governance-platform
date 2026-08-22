"""Deterministic synthetic inventory generation.

Generates a restrained, hand-authored portfolio of datasets, models, and
research projects that together exercise the governance situations the
inventory plane needs to support (multiple sensitivity classifications,
approved/pending/deprecated datasets, low/medium/high risk models, and
approved/pending/expired research projects) — not a maximally large
repository of records.

The portfolio is fixed data, not randomly sampled, so it is deterministic and
reproducible by construction: calling ``generate_portfolio()`` twice, in any
process, on any machine, returns identical data.

All identities are fictional and role-based (e.g. "Population Health Data
Owner"), never real people — see ADR 0001. All dates are fixed historical
placeholders, not derived from the current date, to keep generation
deterministic regardless of when it is run.
"""

from __future__ import annotations

from datetime import date

from governance_platform.inventory.entities import AIModel, Dataset, ResearchProject
from governance_platform.inventory.enums import (
    ApprovalStatus,
    DataCategory,
    LifecycleStatus,
    ModelType,
    ResponsibleAIReviewStatus,
    RetentionClass,
    RiskTier,
    SensitivityClassification,
    SourceType,
    WorkspaceStatus,
)
from governance_platform.inventory.portfolio import InventoryPortfolio


def _datasets() -> tuple[Dataset, ...]:
    return (
        Dataset(
            dataset_id="DS-0001",
            name="Ambulatory Scheduling Operational Analytics",
            description=(
                "Synthetic operational metrics on ambulatory appointment scheduling "
                "(volumes, lead time, no-show rate) used for operations reporting."
            ),
            domain="Operations",
            owner="Operations Analytics Data Owner",
            steward="Operations Data Governance Steward",
            sensitivity_classification=SensitivityClassification.INTERNAL,
            data_category=DataCategory.OPERATIONAL,
            source_type=SourceType.INTERNAL_SYSTEM,
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            research_use_allowed=True,
            retention_class=RetentionClass.STANDARD,
            contains_synthetic_data_only=True,
            created_at=date(2024, 2, 5),
            reviewed_at=date(2024, 8, 12),
        ),
        Dataset(
            dataset_id="DS-0002",
            name="Population Health Risk Signals",
            description=(
                "Synthetic cohort-level population health indicators (chronic condition "
                "prevalence, utilization signals) used for risk research at the cohort level."
            ),
            domain="Population Health",
            owner="Population Health Data Owner",
            steward="Population Health Governance Steward",
            sensitivity_classification=SensitivityClassification.CONFIDENTIAL,
            data_category=DataCategory.POPULATION_HEALTH,
            source_type=SourceType.INTERNAL_SYSTEM,
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            research_use_allowed=True,
            retention_class=RetentionClass.STANDARD,
            contains_synthetic_data_only=True,
            created_at=date(2024, 1, 22),
            reviewed_at=date(2024, 7, 30),
        ),
        Dataset(
            dataset_id="DS-0003",
            name="Synthetic Clinical Notes Corpus",
            description=(
                "Fully synthetic free-text clinical note corpus, generated for NLP research; "
                "contains no real patient narrative content."
            ),
            domain="Clinical Research",
            owner="Clinical Research Data Owner",
            steward="Clinical Research Governance Steward",
            sensitivity_classification=SensitivityClassification.RESTRICTED,
            data_category=DataCategory.CLINICAL_TEXT,
            source_type=SourceType.SYNTHETIC_GENERATED,
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            research_use_allowed=True,
            retention_class=RetentionClass.LONG_TERM,
            contains_synthetic_data_only=True,
            created_at=date(2024, 3, 1),
            reviewed_at=date(2024, 9, 4),
        ),
        Dataset(
            dataset_id="DS-0004",
            name="Readmission Research Feature Store",
            description=(
                "Synthetic engineered features (derived from population health and "
                "operational signals) prepared as model-ready research inputs."
            ),
            domain="Research & Development",
            owner="Research Feature Engineering Data Owner",
            steward="Research & Development Governance Steward",
            sensitivity_classification=SensitivityClassification.CONFIDENTIAL,
            data_category=DataCategory.RESEARCH_FEATURE,
            source_type=SourceType.INTERNAL_SYSTEM,
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            research_use_allowed=True,
            retention_class=RetentionClass.STANDARD,
            contains_synthetic_data_only=True,
            created_at=date(2024, 4, 10),
            reviewed_at=date(2024, 10, 2),
        ),
        Dataset(
            dataset_id="DS-0005",
            name="Synthetic Claims & Billing Extract",
            description=(
                "Synthetic claims and billing summary extract proposed for cost-of-care "
                "research; registration is awaiting governance steward review."
            ),
            domain="Finance",
            owner="Finance Data Owner",
            steward="Finance Governance Steward",
            sensitivity_classification=SensitivityClassification.CONFIDENTIAL,
            data_category=DataCategory.CLAIMS_BILLING,
            source_type=SourceType.THIRD_PARTY_LICENSED,
            lifecycle_status=LifecycleStatus.PROPOSED,
            approval_status=ApprovalStatus.PENDING,
            research_use_allowed=False,
            retention_class=RetentionClass.STANDARD,
            contains_synthetic_data_only=True,
            created_at=date(2025, 1, 14),
            reviewed_at=None,
        ),
        Dataset(
            dataset_id="DS-0006",
            name="Legacy Partner-Shared Imaging Metadata",
            description=(
                "Synthetic imaging study metadata (modality, study date, ordering "
                "department) shared under a since-lapsed partner agreement; superseded."
            ),
            domain="Radiology Research",
            owner="Radiology Research Data Owner",
            steward="Radiology Research Governance Steward",
            sensitivity_classification=SensitivityClassification.CONFIDENTIAL,
            data_category=DataCategory.IMAGING_METADATA,
            source_type=SourceType.PARTNER_SHARED,
            lifecycle_status=LifecycleStatus.DEPRECATED,
            approval_status=ApprovalStatus.APPROVED,
            research_use_allowed=False,
            retention_class=RetentionClass.SHORT_TERM,
            contains_synthetic_data_only=True,
            created_at=date(2023, 6, 18),
            reviewed_at=date(2024, 6, 1),
        ),
    )


def _models() -> tuple[AIModel, ...]:
    return (
        AIModel(
            model_id="MD-0001",
            name="Readmission Risk Scorer",
            version="2.1.0",
            model_type=ModelType.MACHINE_LEARNING,
            intended_use=(
                "Cohort-level readmission risk scoring to support population health "
                "research; not used for individual patient decisions."
            ),
            owner="Population Health Research Model Owner",
            linked_dataset_ids=("DS-0002", "DS-0004"),
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            risk_tier=RiskTier.MEDIUM,
            responsible_ai_review_status=ResponsibleAIReviewStatus.APPROVED,
            monitoring_required=True,
            created_at=date(2024, 5, 1),
            reviewed_at=date(2024, 11, 3),
        ),
        AIModel(
            model_id="MD-0002",
            name="Ambulatory No-Show Predictor",
            version="1.3.0",
            model_type=ModelType.STATISTICAL,
            intended_use="Predict appointment no-show likelihood for scheduling operations.",
            owner="Operations Analytics Model Owner",
            linked_dataset_ids=("DS-0001",),
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            risk_tier=RiskTier.LOW,
            responsible_ai_review_status=ResponsibleAIReviewStatus.NOT_REQUIRED,
            monitoring_required=False,
            created_at=date(2024, 3, 20),
            reviewed_at=date(2024, 9, 15),
        ),
        AIModel(
            model_id="MD-0003",
            name="Clinical Note Summarization LLM",
            version="0.9.0",
            model_type=ModelType.LARGE_LANGUAGE_MODEL,
            intended_use=(
                "Summarize synthetic clinical notes for research review workflows; "
                "under evaluation, not yet approved for use."
            ),
            owner="Clinical Research Model Owner",
            linked_dataset_ids=("DS-0003",),
            lifecycle_status=LifecycleStatus.PROPOSED,
            approval_status=ApprovalStatus.PENDING,
            risk_tier=RiskTier.HIGH,
            responsible_ai_review_status=ResponsibleAIReviewStatus.IN_PROGRESS,
            monitoring_required=True,
            created_at=date(2025, 2, 3),
            reviewed_at=None,
        ),
        AIModel(
            model_id="MD-0004",
            name="Population Health Segmentation Model",
            version="1.0.0",
            model_type=ModelType.MACHINE_LEARNING,
            intended_use="Segment synthetic population health cohorts for research targeting.",
            owner="Population Health Research Model Owner",
            linked_dataset_ids=("DS-0002",),
            lifecycle_status=LifecycleStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
            risk_tier=RiskTier.MEDIUM,
            responsible_ai_review_status=ResponsibleAIReviewStatus.APPROVED,
            monitoring_required=True,
            created_at=date(2024, 6, 11),
            reviewed_at=date(2024, 12, 5),
        ),
        AIModel(
            model_id="MD-0005",
            name="Legacy Claims Risk Model",
            version="3.4.2",
            model_type=ModelType.STATISTICAL,
            intended_use="Retired legacy cost-of-care risk model, retained for audit continuity.",
            owner="Finance Model Owner",
            linked_dataset_ids=("DS-0006",),
            lifecycle_status=LifecycleStatus.RETIRED,
            approval_status=ApprovalStatus.EXPIRED,
            risk_tier=RiskTier.LOW,
            responsible_ai_review_status=ResponsibleAIReviewStatus.NOT_REQUIRED,
            monitoring_required=False,
            created_at=date(2022, 9, 1),
            reviewed_at=date(2024, 6, 1),
        ),
    )


def _research_projects() -> tuple[ResearchProject, ...]:
    return (
        ResearchProject(
            research_project_id="RP-0001",
            title="Readmission Reduction Research Study",
            principal_owner="Population Health Research Principal Investigator",
            purpose=(
                "Evaluate synthetic cohort-level readmission risk signals to inform "
                "population health research on care-transition interventions."
            ),
            linked_dataset_ids=("DS-0002", "DS-0004"),
            linked_model_ids=("MD-0001",),
            approval_status=ApprovalStatus.APPROVED,
            risk_classification=RiskTier.MEDIUM,
            start_date=date(2024, 5, 1),
            expiry_date=date(2025, 5, 1),
            workspace_status=WorkspaceStatus.ACTIVE,
        ),
        ResearchProject(
            research_project_id="RP-0002",
            title="Ambulatory Scheduling Optimization Pilot",
            principal_owner="Operations Research Principal Investigator",
            purpose="Assess synthetic no-show prediction to inform scheduling policy research.",
            linked_dataset_ids=("DS-0001",),
            linked_model_ids=("MD-0002",),
            approval_status=ApprovalStatus.APPROVED,
            risk_classification=RiskTier.LOW,
            start_date=date(2024, 4, 1),
            expiry_date=date(2025, 4, 1),
            workspace_status=WorkspaceStatus.ACTIVE,
        ),
        ResearchProject(
            research_project_id="RP-0003",
            title="Clinical Note Summarization Feasibility Review",
            principal_owner="Clinical Research Principal Investigator",
            purpose=(
                "Assess feasibility of LLM-based summarization of synthetic clinical "
                "notes ahead of a formal responsible AI review."
            ),
            linked_dataset_ids=("DS-0003",),
            linked_model_ids=("MD-0003",),
            approval_status=ApprovalStatus.PENDING,
            risk_classification=RiskTier.HIGH,
            start_date=date(2025, 2, 1),
            expiry_date=date(2025, 8, 1),
            workspace_status=WorkspaceStatus.NOT_PROVISIONED,
        ),
        ResearchProject(
            research_project_id="RP-0004",
            title="Legacy Claims Risk Retrospective",
            principal_owner="Finance Research Principal Investigator",
            purpose="Retrospective review of the retired legacy claims risk model's outputs.",
            linked_dataset_ids=("DS-0005", "DS-0006"),
            linked_model_ids=("MD-0005",),
            approval_status=ApprovalStatus.EXPIRED,
            risk_classification=RiskTier.LOW,
            start_date=date(2023, 7, 1),
            expiry_date=date(2024, 7, 1),
            workspace_status=WorkspaceStatus.DECOMMISSIONED,
        ),
    )


def generate_portfolio() -> InventoryPortfolio:
    """Return the deterministic synthetic inventory portfolio.

    Always returns the same, fully-validated portfolio — datasets, models, and
    research projects are fixed data, not randomly generated, so this function
    is reproducible across processes and machines by construction.
    """
    return InventoryPortfolio(
        datasets=_datasets(),
        models=_models(),
        research_projects=_research_projects(),
    )
