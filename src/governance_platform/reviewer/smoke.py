"""Smoke checks for the local reviewer demo handoff."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
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
    load_reviewer_state,
    missing_output_paths,
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


def streamlit_dependency_available() -> bool:
    """Return whether Streamlit is importable in the current environment."""
    return importlib.util.find_spec("streamlit") is not None


def required_outputs_check(outputs_root: str | Path | None = None) -> tuple[Path, ...]:
    """Return missing generated-output paths for the reviewer handoff."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    return missing_output_paths(root)


def run_core_smoke_checks(outputs_root: str | Path | None = None) -> dict[str, Any]:
    """Run non-server reviewer smoke checks and return deterministic metadata."""
    root = Path(outputs_root) if outputs_root is not None else default_outputs_root()
    missing = required_outputs_check(root)
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

    return {
        "snapshot_id": state.reporting_snapshot.snapshot_id,
        "briefing_id": briefing.briefing_id,
        "evidence_ref_count": len(evidence_index),
        "filtered_view_count": len(filtered_views),
        "app_entrypoint": str(reviewer_app_path()),
    }


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
    outputs_root: str | Path | None = None, *, start_streamlit: bool = True
) -> dict[str, Any]:
    """Run reviewer demo smoke checks."""
    result = run_core_smoke_checks(outputs_root)
    if start_streamlit:
        result["streamlit_headless_start"] = check_streamlit_headless_start()
    else:
        result["streamlit_headless_start"] = "skipped"
    return result
