"""Render an :class:`~governance_platform.audit.evidence.EvidencePack` as Markdown.

Pure presentation over already-derived evidence — no new data is computed
here, so the same pack always renders to byte-identical Markdown. Language is
kept factual: this states what was found in the local simulation, not that
it satisfies any regulatory framework or was produced by a production
system (see the pack's own ``limitations`` section, rendered last).
"""

from __future__ import annotations

from governance_platform.audit.evidence import EvidencePack


def _dict_table(rows: dict[str, int]) -> str:
    lines = ["| Value | Count |", "| --- | --- |"]
    lines.extend(f"| {key} | {count} |" for key, count in rows.items())
    return "\n".join(lines)


def render_evidence_pack_markdown(pack: EvidencePack) -> str:
    """Render ``pack`` as a Markdown governance evidence document."""
    lines: list[str] = []

    lines.append("# Governance Evidence Pack")
    lines.append("")
    lines.append(
        "> Local, deterministic governance simulation. Does not represent a production audit "
        "trail, a live Snowflake/Entra ID/SIEM integration, or any regulatory certification — "
        "see Limitations below."
    )
    lines.append("")
    lines.append(f"- **Evidence pack ID:** {pack.evidence_pack_id}")
    lines.append(
        f"- **Generated at:** {pack.generated_at.isoformat()} "
        f"(explicitly supplied by the caller, not read from the system clock)"
    )
    lines.append(f"- **Scope:** {pack.scope}")
    lines.append("")

    lines.append("## Source systems represented")
    lines.append("")
    lines.extend(f"- {system}" for system in pack.source_systems)
    lines.append("")

    lines.append("## Inventory summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | --- |")
    lines.append(f"| Datasets | {pack.inventory_evidence.dataset_count} |")
    lines.append(f"| Models | {pack.inventory_evidence.model_count} |")
    lines.append(f"| Research projects | {pack.inventory_evidence.research_project_count} |")
    lines.append("")
    lines.append("**Dataset approval status**")
    lines.append("")
    lines.append(_dict_table(pack.inventory_evidence.dataset_approval_status))
    lines.append("")
    lines.append("**Model risk tier**")
    lines.append("")
    lines.append(_dict_table(pack.inventory_evidence.model_risk_tier))
    lines.append("")

    lines.append("## Access-control summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | --- |")
    lines.append(f"| Total requests | {pack.access_summary.total_requests} |")
    lines.append(f"| Approved | {pack.access_summary.request_status['approved']} |")
    lines.append(f"| Rejected | {pack.access_summary.request_status['rejected']} |")
    lines.append(
        f"| Active grants (as of {pack.access_summary.evaluated_at.isoformat()}) | "
        f"{pack.access_summary.grant_status.active} |"
    )
    lines.append(f"| Expired grants | {pack.access_summary.grant_status.expired} |")
    lines.append(f"| Revoked grants | {pack.access_summary.grant_status.revoked} |")
    lines.append("")

    lines.append("## Key audit events")
    lines.append("")
    lines.append(
        f"{pack.audit_summary.total_events} audit events recorded, grouped below by "
        f"correlation ID — each row is one traceable governance activity from first event to "
        f"last."
    )
    lines.append("")
    lines.append("| Correlation ID | Event chain | Final outcome |")
    lines.append("| --- | --- | --- |")
    for group in pack.correlation_groups:
        chain = " -> ".join(group.event_types)
        lines.append(f"| {group.correlation_id} | {chain} | {group.final_outcome} |")
    lines.append("")

    lines.append("## Rejected-access evidence")
    lines.append("")
    if pack.rejected_access:
        lines.append("| Request | Research Project | Decision | Reason |")
        lines.append("| --- | --- | --- | --- |")
        for r in pack.rejected_access:
            lines.append(
                f"| {r.request_id} | {r.research_project_id} | {r.decision_id} | "
                f"{r.decision_reason} |"
            )
    else:
        lines.append("No rejected access requests in scope.")
    lines.append("")

    lines.append("## Grant evidence: active / expired / revoked")
    lines.append("")
    lines.append(
        "| Grant | Request | Research Project | Granted | Expires | "
        "Status (as of evaluation) | Revoked at | Revocation reason |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for g in pack.grants:
        revoked_at = g.revoked_at.isoformat() if g.revoked_at else ""
        revocation_reason = g.revocation_reason or ""
        lines.append(
            f"| {g.grant_id} | {g.request_id} | {g.research_project_id} | "
            f"{g.granted_at.isoformat()} | {g.expires_at.isoformat()} | "
            f"{g.status_as_of_evaluation} | {revoked_at} | {revocation_reason} |"
        )
    lines.append("")

    coverage = pack.audit_summary.coverage
    lines.append("## Control-assurance summary")
    lines.append("")
    lines.append(
        f"- {coverage.requests_with_evaluation_event}/{coverage.requests_total} access "
        f"requests have a recorded evaluation event."
    )
    lines.append(
        f"- {coverage.rejected_requests_with_rejection_event}/{coverage.rejected_requests_total} "
        f"rejected requests have recorded rejection evidence."
    )
    lines.append(
        f"- {coverage.grants_with_creation_event}/{coverage.grants_total} grants have a "
        f"recorded creation event."
    )
    lines.append(
        f"- {coverage.revoked_grants_with_revocation_event}/{coverage.revoked_grants_total} "
        f"revoked grants have a recorded revocation event."
    )
    if pack.completeness.complete:
        lines.append("- **Overall audit completeness: COMPLETE** — no missing evidence found.")
    else:
        lines.append(
            f"- **Overall audit completeness: INCOMPLETE** — "
            f"{len(pack.completeness.problems)} problem(s) found:"
        )
        lines.extend(f"  - {problem}" for problem in pack.completeness.problems)
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.extend(f"- {limitation}" for limitation in pack.limitations)
    lines.append("")

    return "\n".join(lines)
