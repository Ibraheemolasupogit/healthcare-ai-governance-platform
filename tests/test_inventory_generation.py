from governance_platform.inventory import (
    ApprovalStatus,
    DataCategory,
    LifecycleStatus,
    RiskTier,
    generate_portfolio,
)


def test_generation_is_deterministic() -> None:
    first = generate_portfolio()
    second = generate_portfolio()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_generated_portfolio_is_restrained() -> None:
    portfolio = generate_portfolio()

    # Restrained per Milestone 2 scope: enough to cover required governance
    # situations, not padded to inflate repository size.
    assert 4 <= len(portfolio.datasets) <= 10
    assert 3 <= len(portfolio.models) <= 10
    assert 3 <= len(portfolio.research_projects) <= 10


def test_generated_datasets_cover_required_categories() -> None:
    portfolio = generate_portfolio()
    categories = {d.data_category for d in portfolio.datasets}

    assert DataCategory.OPERATIONAL in categories
    assert DataCategory.POPULATION_HEALTH in categories
    assert DataCategory.CLINICAL_TEXT in categories
    assert DataCategory.RESEARCH_FEATURE in categories


def test_generated_datasets_cover_approved_and_pending() -> None:
    portfolio = generate_portfolio()
    statuses = {d.approval_status for d in portfolio.datasets}

    assert ApprovalStatus.APPROVED in statuses
    assert ApprovalStatus.PENDING in statuses


def test_generated_models_cover_all_risk_tiers() -> None:
    portfolio = generate_portfolio()
    tiers = {m.risk_tier for m in portfolio.models}

    assert tiers == {RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH}


def test_generated_research_projects_cover_approved_pending_and_expired() -> None:
    portfolio = generate_portfolio()
    statuses = {p.approval_status for p in portfolio.research_projects}

    assert ApprovalStatus.APPROVED in statuses
    assert ApprovalStatus.PENDING in statuses
    assert ApprovalStatus.EXPIRED in statuses


def test_generated_datasets_are_all_synthetic_only() -> None:
    portfolio = generate_portfolio()
    assert all(d.contains_synthetic_data_only for d in portfolio.datasets)


def test_generated_identities_are_role_based_not_real_names() -> None:
    portfolio = generate_portfolio()

    # Fictional role-based identities, not first+last "real person" names:
    # every owner/steward/principal_owner string names a role, not an
    # individual — a loose but useful heuristic is that each contains a
    # governance/organisational noun rather than looking like "Jane Smith".
    role_markers = ("Owner", "Steward", "Investigator")
    identities = (
        [d.owner for d in portfolio.datasets]
        + [d.steward for d in portfolio.datasets]
        + [m.owner for m in portfolio.models]
        + [p.principal_owner for p in portfolio.research_projects]
    )
    assert identities
    assert all(any(marker in identity for marker in role_markers) for identity in identities)


def test_generated_portfolio_has_no_deprecated_or_retired_dataset_flagged_for_research() -> None:
    portfolio = generate_portfolio()
    deprecated = [d for d in portfolio.datasets if d.lifecycle_status == LifecycleStatus.DEPRECATED]

    assert deprecated
    assert all(not d.research_use_allowed for d in deprecated)
