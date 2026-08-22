"""The inventory portfolio: a validated collection of datasets, models, and research projects.

This is where cross-entity referential integrity is enforced — invariants that
can't be checked by looking at a single entity in isolation (duplicate IDs,
dangling dataset/model references). Per-entity invariants live on the entities
themselves in ``governance_platform.inventory.entities``.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, model_validator

from governance_platform.inventory.entities import AIModel, Dataset, ResearchProject


class InventoryPortfolio(BaseModel):
    """A complete, internally-consistent inventory: datasets, models, and research projects."""

    model_config = {"frozen": True, "extra": "forbid"}

    datasets: tuple[Dataset, ...] = ()
    models: tuple[AIModel, ...] = ()
    research_projects: tuple[ResearchProject, ...] = ()

    @model_validator(mode="after")
    def _no_duplicate_ids(self) -> InventoryPortfolio:
        for label, ids in (
            ("dataset_id", [d.dataset_id for d in self.datasets]),
            ("model_id", [m.model_id for m in self.models]),
            ("research_project_id", [p.research_project_id for p in self.research_projects]),
        ):
            duplicates = sorted({item for item, count in Counter(ids).items() if count > 1})
            if duplicates:
                raise ValueError(f"duplicate {label} values found: {duplicates}")
        return self

    @model_validator(mode="after")
    def _references_resolve(self) -> InventoryPortfolio:
        dataset_ids = {d.dataset_id for d in self.datasets}
        model_ids = {m.model_id for m in self.models}

        for m in self.models:
            unknown = sorted(set(m.linked_dataset_ids) - dataset_ids)
            if unknown:
                raise ValueError(f"model {m.model_id} references unknown dataset_id(s): {unknown}")

        for p in self.research_projects:
            unknown_datasets = sorted(set(p.linked_dataset_ids) - dataset_ids)
            if unknown_datasets:
                raise ValueError(
                    f"research project {p.research_project_id} references unknown "
                    f"dataset_id(s): {unknown_datasets}"
                )
            unknown_models = sorted(set(p.linked_model_ids) - model_ids)
            if unknown_models:
                raise ValueError(
                    f"research project {p.research_project_id} references unknown "
                    f"model_id(s): {unknown_models}"
                )
        return self

    def dataset_by_id(self, dataset_id: str) -> Dataset:
        for d in self.datasets:
            if d.dataset_id == dataset_id:
                return d
        raise KeyError(f"no dataset with dataset_id={dataset_id!r}")

    def model_by_id(self, model_id: str) -> AIModel:
        for m in self.models:
            if m.model_id == model_id:
                return m
        raise KeyError(f"no model with model_id={model_id!r}")

    def research_project_by_id(self, research_project_id: str) -> ResearchProject:
        for p in self.research_projects:
            if p.research_project_id == research_project_id:
                return p
        raise KeyError(f"no research project with research_project_id={research_project_id!r}")
