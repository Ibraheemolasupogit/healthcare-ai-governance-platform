"""Governance reporting plane — local KPIs and future semantic-model contracts.

Milestone 6 implements a local deterministic reporting layer over the
existing synthetic inventory, access, audit/evidence, and compliance state.
It produces reporting-ready KPI rows and a snapshot/export for reviewer and
executive views. It does not deploy Microsoft Fabric, create Power BI files,
or perform live refresh.
"""

from governance_platform.reporting.entities import GovernanceKPI, ReportingSnapshot
from governance_platform.reporting.enums import MetricUnit, ReportingMetricDomain
from governance_platform.reporting.io import (
    export_reporting_snapshot,
    load_reporting_snapshot,
)
from governance_platform.reporting.markdown import render_executive_summary_markdown
from governance_platform.reporting.snapshot import (
    REPORTING_LIMITATIONS,
    build_reporting_snapshot,
)
from governance_platform.reporting.validation import (
    unresolved_source_refs,
    validate_reporting_snapshot_data,
    validate_reporting_snapshot_file,
)

__all__ = [
    "REPORTING_LIMITATIONS",
    "GovernanceKPI",
    "MetricUnit",
    "ReportingMetricDomain",
    "ReportingSnapshot",
    "build_reporting_snapshot",
    "export_reporting_snapshot",
    "load_reporting_snapshot",
    "render_executive_summary_markdown",
    "unresolved_source_refs",
    "validate_reporting_snapshot_data",
    "validate_reporting_snapshot_file",
]
