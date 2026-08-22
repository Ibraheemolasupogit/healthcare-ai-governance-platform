"""Metadata / inventory plane — dataset, model, and research project inventory.

Milestone 2 (Synthetic Research & AI Inventory). This module implements the
governed metadata/inventory plane described in ``reports/architecture.md``:
typed dataset, AI/ML model, and research project entities
(:mod:`governance_platform.inventory.entities`), cross-entity referential
integrity (:mod:`governance_platform.inventory.portfolio`), deterministic
synthetic generation (:mod:`governance_platform.inventory.generation`),
loading/export (:mod:`governance_platform.inventory.io`), standalone
validation (:mod:`governance_platform.inventory.validation`), and an
aggregate governance summary (:mod:`governance_platform.inventory.summary`).

This is metadata about datasets, models, and research projects — not the
datasets, models, or projects themselves. No model training, deployment,
inference, or monitoring; no research workspace provisioning; no access,
audit, or risk-scoring logic is implemented here. See
``governance/dataset_governance.md``, ``governance/model_governance.md``, and
``governance/research_approval.md`` for the operating model this inventory
is a concrete dependency of.
"""

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
from governance_platform.inventory.generation import generate_portfolio
from governance_platform.inventory.io import export_portfolio, load_portfolio
from governance_platform.inventory.portfolio import InventoryPortfolio
from governance_platform.inventory.summary import EntityCounts, InventorySummary, build_summary
from governance_platform.inventory.validation import (
    validate_portfolio_data,
    validate_portfolio_file,
)

__all__ = [
    "AIModel",
    "ApprovalStatus",
    "DataCategory",
    "Dataset",
    "EntityCounts",
    "InventoryPortfolio",
    "InventorySummary",
    "LifecycleStatus",
    "ModelType",
    "ResearchProject",
    "ResponsibleAIReviewStatus",
    "RetentionClass",
    "RiskTier",
    "SensitivityClassification",
    "SourceType",
    "WorkspaceStatus",
    "build_summary",
    "export_portfolio",
    "generate_portfolio",
    "load_portfolio",
    "validate_portfolio_data",
    "validate_portfolio_file",
]
