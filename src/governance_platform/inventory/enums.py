"""Enumerations shared by the inventory plane's typed entities.

Kept in one module so datasets, models, and research projects reuse the same
vocabulary (e.g. a single ``ApprovalStatus``) rather than each entity growing
its own near-duplicate status enum.
"""

from __future__ import annotations

from enum import Enum


class SensitivityClassification(str, Enum):
    """How sensitive an inventoried dataset is, per ``governance/dataset_governance.md``."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataCategory(str, Enum):
    """The kind of governance situation a dataset represents in the portfolio."""

    OPERATIONAL = "operational"
    POPULATION_HEALTH = "population_health"
    CLINICAL_TEXT = "clinical_text"
    RESEARCH_FEATURE = "research_feature"
    CLAIMS_BILLING = "claims_billing"
    IMAGING_METADATA = "imaging_metadata"


class SourceType(str, Enum):
    """Where a dataset's (synthetic) data originates from."""

    INTERNAL_SYSTEM = "internal_system"
    THIRD_PARTY_LICENSED = "third_party_licensed"
    SYNTHETIC_GENERATED = "synthetic_generated"
    PARTNER_SHARED = "partner_shared"


class RetentionClass(str, Enum):
    """How long a dataset is retained once it stops being actively used."""

    SHORT_TERM = "short_term"
    STANDARD = "standard"
    LONG_TERM = "long_term"
    INDEFINITE = "indefinite"


class LifecycleStatus(str, Enum):
    """Generic lifecycle stage shared by datasets and models.

    Deliberately coarser than the per-domain chains described in
    ``governance/dataset_governance.md`` and ``governance/model_governance.md``
    (e.g. a model's "under review" and "deployed" stages both fall under
    ``ACTIVE`` here) — the approval gate itself is tracked separately by
    ``ApprovalStatus``.
    """

    PROPOSED = "proposed"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ApprovalStatus(str, Enum):
    """The governance approval gate shared by datasets, models, and research projects."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ModelType(str, Enum):
    """The kind of model registered, per ``governance/model_governance.md``."""

    STATISTICAL = "statistical"
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    LARGE_LANGUAGE_MODEL = "large_language_model"


class RiskTier(str, Enum):
    """Shared risk tier for models (``risk_tier``) and projects (``risk_classification``)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResponsibleAIReviewStatus(str, Enum):
    """Status of the responsible AI review described in ``governance/responsible_ai.md``."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    FLAGGED = "flagged"


class WorkspaceStatus(str, Enum):
    """State of a research project's (not-yet-implemented) workspace provisioning."""

    NOT_PROVISIONED = "not_provisioned"
    ACTIVE = "active"
    DECOMMISSIONED = "decommissioned"
