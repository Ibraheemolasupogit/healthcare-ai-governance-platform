from governance_platform.inventory import (
    ApprovalStatus,
    InventoryPortfolio,
    build_summary,
    generate_portfolio,
)


def test_summary_entity_counts_match_portfolio() -> None:
    portfolio = generate_portfolio()
    summary = build_summary(portfolio)

    assert summary.entity_counts.datasets == len(portfolio.datasets)
    assert summary.entity_counts.models == len(portfolio.models)
    assert summary.entity_counts.research_projects == len(portfolio.research_projects)


def test_summary_dataset_approval_status_counts_are_correct() -> None:
    portfolio = generate_portfolio()
    summary = build_summary(portfolio)

    expected_approved = sum(
        1 for d in portfolio.datasets if d.approval_status == ApprovalStatus.APPROVED
    )
    expected_pending = sum(
        1 for d in portfolio.datasets if d.approval_status == ApprovalStatus.PENDING
    )

    assert summary.dataset_approval_status["approved"] == expected_approved
    assert summary.dataset_approval_status["pending"] == expected_pending
    # Every ApprovalStatus member is present, even at zero, for a stable shape.
    assert set(summary.dataset_approval_status) == {"pending", "approved", "rejected", "expired"}


def test_summary_on_empty_portfolio_has_zeroed_counts() -> None:
    summary = build_summary(InventoryPortfolio())

    assert summary.entity_counts.datasets == 0
    assert all(count == 0 for count in summary.dataset_approval_status.values())
    assert summary.all_datasets_synthetic_only is True


def test_summary_flags_all_datasets_synthetic_only() -> None:
    summary = build_summary(generate_portfolio())
    assert summary.all_datasets_synthetic_only is True
