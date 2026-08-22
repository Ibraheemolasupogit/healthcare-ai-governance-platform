"""Smoke checks for the local reviewer demo handoff."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from governance_platform.reviewer.data import (
    MissingGeneratedOutputError,
    default_outputs_root,
    drillthrough_by_grant,
    drillthrough_by_project,
    drillthrough_by_request,
    evidence_reference_rows,
    load_reviewer_assurance_pack_state,
    load_reviewer_assurance_state,
    load_reviewer_policy_state,
    load_reviewer_readiness_state,
    load_reviewer_state,
    missing_assurance_output_paths,
    missing_assurance_pack_output_paths,
    missing_output_paths,
    missing_policy_output_paths,
    missing_readiness_output_paths,
)
from governance_platform.reviewer.exports import (
    build_filtered_reviewer_views,
    build_reviewer_briefing,
    build_reviewer_evidence_index,
    unresolved_evidence_refs,
)


def repo_root() -> Path:
    """Return the repository root from the installed source tree."""
    return Path(__file__).resolve().parents[3]


def reviewer_app_path() -> Path:
    """Return the Streamlit reviewer app entrypoint."""
    return repo_root() / "src" / "governance_platform" / "reviewer_app.py"


def required_generation_scripts() -> tuple[Path, ...]:
    """Return generation scripts required for the reviewer demo handoff."""
    root = repo_root()
    return (
        root / "scripts" / "generate_inventory.py",
        root / "scripts" / "generate_access.py",
        root / "scripts" / "generate_evidence.py",
        root / "scripts" / "generate_compliance.py",
        root / "scripts" / "generate_reporting.py",
        root / "scripts" / "generate_reviewer_bundle.py",
        root / "scripts" / "generate_policy_catalog.py",
        root / "scripts" / "generate_assurance_history.py",
        root / "scripts" / "generate_assurance_pack.py",
        root / "scripts" / "generate_review_readiness.py",
    )


def required_demo_docs() -> tuple[Path, ...]:
    """Return local demo documents required for reviewer handoff."""
    root = repo_root()
    return (
        root / "docs" / "demo" / "reviewer-demo-runbook.md",
        root / "docs" / "demo" / "reviewer-walkthrough-template.md",
    )


def streamlit_dependency_available() -> bool:
    """Return whether Streamlit is importable in the current environment."""
    return importlib.util.find_spec("streamlit") is not None


def required_outputs_check(
    outputs_root: str | Path | None = None, *, include_extended: bool = False
) -> tuple[Path, ...]:
    """Return missing generated-output paths for the reviewer handoff."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = missing_output_paths(root)
    if not include_extended:
        return missing
    return (
        *missing,
        *missing_policy_output_paths(root),
        *missing_assurance_output_paths(root),
        *missing_assurance_pack_output_paths(root),
        *missing_readiness_output_paths(root),
    )


def run_core_smoke_checks(
    outputs_root: str | Path | None = None, *, include_extended: bool = False
) -> dict[str, Any]:
    """Run non-server reviewer smoke checks and return deterministic metadata."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = required_outputs_check(root, include_extended=include_extended)
    if missing:
        raise MissingGeneratedOutputError(missing)

    state = load_reviewer_state(root)
    briefing = build_reviewer_briefing(state)
    evidence_index = build_reviewer_evidence_index(state)
    unresolved = unresolved_evidence_refs(state, evidence_index)
    if unresolved:
        raise ValueError(f"unresolved reviewer evidence refs: {', '.join(unresolved)}")

    project_drill = drillthrough_by_project(state, "RP-0001")
    request_drill = drillthrough_by_request(state, "AR-0001")
    grant_drill = drillthrough_by_grant(state, "AG-0001")
    filtered_views = build_filtered_reviewer_views(state)
    evidence_refs = evidence_reference_rows(state)

    if not project_drill["audit_events"]:
        raise ValueError("project drill-through returned no audit events for RP-0001")
    if not request_drill["decision"]:
        raise ValueError("request drill-through returned no decision for AR-0001")
    if not grant_drill["control_results"]:
        raise ValueError("grant drill-through returned no control results for AG-0001")
    if not filtered_views:
        raise ValueError("filtered reviewer views were not built")
    if not evidence_refs:
        raise ValueError("reviewer evidence references were not built")
    if not streamlit_dependency_available():
        raise ImportError("Streamlit is not available; install project dependencies first")
    if not reviewer_app_path().is_file():
        raise FileNotFoundError(f"Reviewer app entrypoint not found: {reviewer_app_path()}")

    result = {
        "snapshot_id": state.reporting_snapshot.snapshot_id,
        "briefing_id": briefing.briefing_id,
        "evidence_ref_count": len(evidence_index),
        "filtered_view_count": len(filtered_views),
        "app_entrypoint": str(reviewer_app_path()),
    }
    if not include_extended:
        return result

    policy_state = load_reviewer_policy_state(root)
    assurance_state = load_reviewer_assurance_state(root)
    assurance_pack_state = load_reviewer_assurance_pack_state(root)
    readiness_state = load_reviewer_readiness_state(root)
    if not policy_state.traceability_rows:
        raise ValueError("policy traceability rows were not loaded")
    if not assurance_state.control_drift_rows:
        raise ValueError("assurance control drift rows were not loaded")
    if not assurance_pack_state.evidence_map_rows:
        raise ValueError("assurance pack evidence map rows were not loaded")
    if readiness_state.checklist.readiness_status.value == "not_ready":
        raise ValueError("review-readiness checklist is not ready for review")
    if not all(path.is_file() for path in required_generation_scripts()):
        raise FileNotFoundError("one or more required generation scripts are missing")
    if not all(path.is_file() for path in required_demo_docs()):
        raise FileNotFoundError("one or more required demo documents are missing")
    from governance_platform.reviewer.readiness import (
        build_review_readiness_bundle,
        export_review_readiness_bundle,
    )

    readiness_bundle = build_review_readiness_bundle(root)
    with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
        first = Path(first_dir)
        second = Path(second_dir)
        export_review_readiness_bundle(readiness_bundle, first)
        export_review_readiness_bundle(readiness_bundle, second)
        for path in sorted(first.iterdir()):
            if path.read_bytes() != (second / path.name).read_bytes():
                raise ValueError(f"readiness export is not deterministic for {path.name}")
    result.update(
        {
            "policy_traceability_rows": len(policy_state.traceability_rows),
            "control_drift_rows": len(assurance_state.control_drift_rows),
            "assurance_evidence_map_rows": len(assurance_pack_state.evidence_map_rows),
            "readiness_status": readiness_state.checklist.readiness_status.value,
        }
    )
    return result


def check_streamlit_headless_start(port: int = 8510, timeout_seconds: float = 8.0) -> str:
    """Start the Streamlit app briefly in headless mode, then stop it.

    Some restricted execution sandboxes disallow binding even to 127.0.0.1.
    In that case, the smoke check falls back to dependency and entrypoint
    validation instead of failing the local handoff script.
    """
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(reviewer_app_path()),
        "--server.headless",
        "true",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
    ]
    process = subprocess.Popen(
        command,
        cwd=repo_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines: list[str] = []
    try:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            line = process.stdout.readline() if process.stdout is not None else ""
            if line:
                output_lines.append(line.rstrip())
                if (
                    "You can now view your Streamlit app" in line
                    or "server started" in line.lower()
                ):
                    return "passed"
            if process.poll() is not None:
                if process.stdout is not None:
                    output_lines.extend(line.rstrip() for line in process.stdout.readlines())
                break
            time.sleep(0.1)
        output = "\n".join(output_lines)
        if "PermissionError" in output and "Operation not permitted" in output:
            return "entrypoint_validated_startup_blocked_by_environment"
        raise RuntimeError("Streamlit reviewer app did not start cleanly. Output:\n" + output)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def run_smoke_checks(
    outputs_root: str | Path | None = None,
    *,
    start_streamlit: bool = True,
    include_extended: bool = False,
) -> dict[str, Any]:
    """Run reviewer demo smoke checks."""
    result = run_core_smoke_checks(outputs_root, include_extended=include_extended)
    if start_streamlit:
        result["streamlit_headless_start"] = check_streamlit_headless_start()
    else:
        result["streamlit_headless_start"] = "skipped"
    return result
