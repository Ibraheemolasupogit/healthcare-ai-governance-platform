"""Deterministic offline assurance archive manifests and verification.

Milestone 13 inventories selected repository artifacts and records exact-byte
SHA-256 checksums. It does not copy governance data, sign artifacts, or imply
authenticity, approval, certification, or production deployment.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

ARCHIVE_MANIFEST_FILENAME = "archive_manifest.json"
ARCHIVE_MANIFEST_CSV_FILENAME = "archive_manifest.csv"
ARCHIVE_VALIDATION_FILENAME = "archive_validation.json"
ARCHIVE_CHECKSUMS_FILENAME = "archive_file_checksums.sha256"
OFFLINE_HANDOFF_GUIDE_FILENAME = "offline_handoff_guide.md"
ARCHIVE_OUTPUT_FILENAMES: tuple[str, ...] = (
    ARCHIVE_MANIFEST_FILENAME,
    ARCHIVE_MANIFEST_CSV_FILENAME,
    ARCHIVE_VALIDATION_FILENAME,
    ARCHIVE_CHECKSUMS_FILENAME,
    OFFLINE_HANDOFF_GUIDE_FILENAME,
)

_GENERATED_AT = datetime(2025, 3, 24, 0, 0, 0)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ArchiveValidationStatus(str, Enum):
    """Validation status for an offline manifest."""

    PASSED = "passed"
    FAILED = "failed"


class ArchiveArtifact(BaseModel):
    """One repository-relative artifact in the offline manifest."""

    model_config = {"frozen": True, "extra": "forbid"}

    artifact_id: str = Field(pattern=r"^ARC-\d{4}$")
    relative_path: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    source_plane: str = Field(min_length=1)
    milestone: str = Field(min_length=1)
    description: str = Field(min_length=1)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    size_bytes: int = Field(ge=0)
    required: bool
    generation_command: str = Field(min_length=1)
    reviewer_role: str = Field(min_length=1)

    @field_validator("relative_path")
    @classmethod
    def _relative_safe_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
            raise ValueError("archive artifact path must be a safe repository-relative path")
        return value


class ArchiveManifest(BaseModel):
    """Canonical deterministic inventory of reviewer-facing artifacts."""

    model_config = {"frozen": True, "extra": "forbid"}

    manifest_id: str = Field(pattern=r"^AM-\d{4}$")
    generated_at: datetime
    repository_name: str = Field(min_length=1)
    package_scope: str = Field(min_length=1)
    artifacts: tuple[ArchiveArtifact, ...]
    artifact_count: int = Field(ge=0)
    required_artifact_count: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)
    verification_algorithm: str = "sha256"
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]

    @model_validator(mode="after")
    def _counts_match(self) -> ArchiveManifest:
        if self.artifact_count != len(self.artifacts):
            raise ValueError("artifact_count does not match artifacts")
        if self.required_artifact_count != sum(artifact.required for artifact in self.artifacts):
            raise ValueError("required_artifact_count does not match artifacts")
        if self.total_size_bytes != sum(artifact.size_bytes for artifact in self.artifacts):
            raise ValueError("total_size_bytes does not match artifacts")
        if self.verification_algorithm != "sha256":
            raise ValueError("only sha256 verification is supported")
        if not self.source_refs or not self.limitations:
            raise ValueError("manifest source_refs and limitations must not be empty")
        return self


class ArchiveValidationResult(BaseModel):
    """Filesystem validation result for an archive manifest."""

    model_config = {"frozen": True, "extra": "forbid"}

    validation_id: str = Field(pattern=r"^AVR-\d{4}$")
    evaluated_at: datetime
    manifest_valid: bool
    required_artifacts_present: bool
    checksum_validation_passed: bool
    duplicate_paths_absent: bool
    duplicate_artifact_ids_absent: bool
    status: ArchiveValidationStatus
    issues: tuple[str, ...]
    limitations: tuple[str, ...]


_LIMITATIONS: tuple[str, ...] = (
    "The manifest covers this local repository and selected generated synthetic outputs only.",
    "A matching checksum proves byte equality with the referenced file, not "
    "authenticity or correctness.",
    "No digital signature, external attestation, human approval, or production "
    "acceptance is provided.",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_spec(
    path: str,
    artifact_type: str,
    plane: str,
    milestone: str,
    description: str,
    command: str,
    role: str,
) -> tuple[str, str, str, str, str, str, str, str]:
    return path, artifact_type, plane, milestone, description, command, role, "required"


_ARTIFACT_SPECS: tuple[tuple[str, str, str, str, str, str, str, str], ...] = (
    _artifact_spec(
        "outputs/inventory/inventory_portfolio.json",
        "json",
        "inventory",
        "2",
        "Canonical synthetic inventory portfolio.",
        "python3 scripts/generate_inventory.py",
        "inventory reviewer",
    ),
    _artifact_spec(
        "outputs/inventory/inventory_summary.json",
        "json",
        "inventory",
        "2",
        "Inventory aggregate metrics.",
        "python3 scripts/generate_inventory.py",
        "inventory reviewer",
    ),
    _artifact_spec(
        "outputs/access/access_control_state.json",
        "json",
        "access",
        "3",
        "Canonical request, decision, and grant state.",
        "python3 scripts/generate_access.py",
        "access reviewer",
    ),
    _artifact_spec(
        "outputs/access/access_review_summary.json",
        "json",
        "access",
        "3",
        "Access governance summary.",
        "python3 scripts/generate_access.py",
        "access reviewer",
    ),
    _artifact_spec(
        "outputs/evidence/audit_events.json",
        "json",
        "audit_evidence",
        "4",
        "Append-only synthetic audit events.",
        "python3 scripts/generate_evidence.py",
        "audit reviewer",
    ),
    _artifact_spec(
        "outputs/evidence/audit_summary.json",
        "json",
        "audit_evidence",
        "4",
        "Audit summary and correlation metrics.",
        "python3 scripts/generate_evidence.py",
        "audit reviewer",
    ),
    _artifact_spec(
        "outputs/evidence/evidence_pack.json",
        "json",
        "audit_evidence",
        "4",
        "Canonical evidence pack.",
        "python3 scripts/generate_evidence.py",
        "evidence reviewer",
    ),
    _artifact_spec(
        "outputs/evidence/evidence_pack.md",
        "markdown",
        "audit_evidence",
        "4",
        "Reviewer-readable evidence pack.",
        "python3 scripts/generate_evidence.py",
        "evidence reviewer",
    ),
    _artifact_spec(
        "outputs/compliance/compliance_summary.json",
        "json",
        "compliance_risk",
        "5",
        "Control assessment, bounded risk, and posture.",
        "python3 scripts/generate_compliance.py",
        "compliance reviewer",
    ),
    _artifact_spec(
        "outputs/compliance/risk_indicators.json",
        "json",
        "compliance_risk",
        "5",
        "Evidence-backed risk indicators.",
        "python3 scripts/generate_compliance.py",
        "risk reviewer",
    ),
    _artifact_spec(
        "outputs/compliance/governance_posture.md",
        "markdown",
        "compliance_risk",
        "5",
        "Reviewer-readable governance posture.",
        "python3 scripts/generate_compliance.py",
        "compliance reviewer",
    ),
    _artifact_spec(
        "outputs/reporting/reporting_snapshot.json",
        "json",
        "reporting",
        "6",
        "Canonical governance reporting snapshot.",
        "python3 scripts/generate_reporting.py",
        "executive reviewer",
    ),
    _artifact_spec(
        "outputs/reporting/governance_kpis.csv",
        "csv",
        "reporting",
        "6",
        "Deterministic governance KPI rows.",
        "python3 scripts/generate_reporting.py",
        "executive reviewer",
    ),
    _artifact_spec(
        "outputs/reporting/executive_summary.md",
        "markdown",
        "reporting",
        "6",
        "Executive governance summary.",
        "python3 scripts/generate_reporting.py",
        "executive reviewer",
    ),
    _artifact_spec(
        "outputs/reviewer/reviewer_briefing.json",
        "json",
        "reviewer_handoff",
        "8",
        "Canonical reviewer briefing.",
        "python3 scripts/generate_reviewer_bundle.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/reviewer/reviewer_briefing.md",
        "markdown",
        "reviewer_handoff",
        "8",
        "Reviewer-readable briefing.",
        "python3 scripts/generate_reviewer_bundle.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/reviewer/reviewer_evidence_index.csv",
        "csv",
        "reviewer_handoff",
        "8",
        "Reviewer evidence reference index.",
        "python3 scripts/generate_reviewer_bundle.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/reviewer/reviewer_findings.csv",
        "csv",
        "reviewer_handoff",
        "8",
        "Deterministic reviewer findings export.",
        "python3 scripts/generate_reviewer_bundle.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/policy/policy_catalog.json",
        "json",
        "policy_control",
        "9",
        "Local governance policy metadata.",
        "python3 scripts/generate_policy_catalog.py",
        "control reviewer",
    ),
    _artifact_spec(
        "outputs/policy/control_catalog.json",
        "json",
        "policy_control",
        "9",
        "Catalog of implemented controls.",
        "python3 scripts/generate_policy_catalog.py",
        "control reviewer",
    ),
    _artifact_spec(
        "outputs/policy/control_evidence_traceability.csv",
        "csv",
        "policy_control",
        "9",
        "Control-to-evidence traceability matrix.",
        "python3 scripts/generate_policy_catalog.py",
        "control reviewer",
    ),
    _artifact_spec(
        "outputs/policy/policy_assurance_summary.json",
        "json",
        "policy_control",
        "9",
        "Policy assurance coverage summary.",
        "python3 scripts/generate_policy_catalog.py",
        "control reviewer",
    ),
    _artifact_spec(
        "outputs/assurance/assurance_snapshots.json",
        "json",
        "assurance_history",
        "10",
        "Explicit deterministic assurance snapshots.",
        "python3 scripts/generate_assurance_history.py",
        "assurance reviewer",
    ),
    _artifact_spec(
        "outputs/assurance/assurance_comparison.json",
        "json",
        "assurance_history",
        "10",
        "Snapshot comparison and posture transition.",
        "python3 scripts/generate_assurance_history.py",
        "assurance reviewer",
    ),
    _artifact_spec(
        "outputs/assurance/control_drift.csv",
        "csv",
        "assurance_history",
        "10",
        "Control drift rows.",
        "python3 scripts/generate_assurance_history.py",
        "assurance reviewer",
    ),
    _artifact_spec(
        "outputs/assurance/risk_drift.csv",
        "csv",
        "assurance_history",
        "10",
        "Risk drift rows.",
        "python3 scripts/generate_assurance_history.py",
        "assurance reviewer",
    ),
    _artifact_spec(
        "outputs/assurance/assurance_drift_report.md",
        "markdown",
        "assurance_history",
        "10",
        "Reviewer-readable assurance change report.",
        "python3 scripts/generate_assurance_history.py",
        "assurance reviewer",
    ),
    _artifact_spec(
        "outputs/assurance_pack/assurance_review_pack.json",
        "json",
        "assurance_pack",
        "11",
        "Integrated assurance review pack.",
        "python3 scripts/generate_assurance_pack.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/assurance_pack/priority_findings.csv",
        "csv",
        "assurance_pack",
        "11",
        "Prioritized cross-linked findings.",
        "python3 scripts/generate_assurance_pack.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/assurance_pack/assurance_evidence_map.csv",
        "csv",
        "assurance_pack",
        "11",
        "Finding, control, policy, evidence, and drift map.",
        "python3 scripts/generate_assurance_pack.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/assurance_pack/assurance_review_pack.md",
        "markdown",
        "assurance_pack",
        "11",
        "Reviewer-readable integrated pack.",
        "python3 scripts/generate_assurance_pack.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/readiness/acceptance_checklist.json",
        "json",
        "review_readiness",
        "12",
        "Deterministic review acceptance checklist.",
        "python3 scripts/generate_review_readiness.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/readiness/acceptance_checklist.csv",
        "csv",
        "review_readiness",
        "12",
        "Acceptance checklist table.",
        "python3 scripts/generate_review_readiness.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/readiness/artifact_completeness.json",
        "json",
        "review_readiness",
        "12",
        "Semantic artifact completeness evidence.",
        "python3 scripts/generate_review_readiness.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/readiness/demo_readiness.json",
        "json",
        "review_readiness",
        "12",
        "Local demo-readiness validation.",
        "python3 scripts/generate_review_readiness.py",
        "external reviewer",
    ),
    _artifact_spec(
        "outputs/readiness/review_readiness_report.md",
        "markdown",
        "review_readiness",
        "12",
        "Reviewer-readable readiness report.",
        "python3 scripts/generate_review_readiness.py",
        "external reviewer",
    ),
    _artifact_spec(
        "README.md",
        "markdown",
        "documentation",
        "1-12",
        "Repository scope, implementation status, and claim boundaries.",
        "repository source; regenerate upstream outputs as documented",
        "external reviewer",
    ),
    _artifact_spec(
        "reports/architecture.md",
        "markdown",
        "documentation",
        "1-12",
        "Architecture and implemented/planned boundary.",
        "repository source; regenerate upstream outputs as documented",
        "architecture reviewer",
    ),
    _artifact_spec(
        "outputs/README.md",
        "markdown",
        "documentation",
        "1-13",
        "Generated-output conventions and claim boundaries.",
        "repository source; regenerate upstream outputs as documented",
        "external reviewer",
    ),
    _artifact_spec(
        "governance/README.md",
        "markdown",
        "documentation",
        "1-13",
        "Governance operating-model index and implementation boundaries.",
        "repository source; regenerate upstream outputs as documented",
        "governance reviewer",
    ),
    _artifact_spec(
        "governance/compliance_monitoring.md",
        "markdown",
        "documentation",
        "5",
        "Compliance and risk governance reference.",
        "repository source; regenerate upstream outputs as documented",
        "compliance reviewer",
    ),
    _artifact_spec(
        "docs/architecture/decisions/README.md",
        "markdown",
        "documentation",
        "1",
        "Architecture decision index.",
        "repository source; regenerate upstream outputs as documented",
        "architecture reviewer",
    ),
    _artifact_spec(
        "governance/controls/README.md",
        "markdown",
        "documentation",
        "9",
        "Control catalog and lifecycle documentation.",
        "repository source; regenerate upstream outputs as documented",
        "control reviewer",
    ),
    _artifact_spec(
        "docs/demo/reviewer-demo-runbook.md",
        "markdown",
        "documentation",
        "12",
        "Local reviewer demo runbook.",
        "repository source; regenerate upstream outputs as documented",
        "external reviewer",
    ),
    _artifact_spec(
        "docs/demo/reviewer-walkthrough-template.md",
        "markdown",
        "documentation",
        "12",
        "Blank reviewer walkthrough notes template.",
        "repository source; use only for an actual future review",
        "external reviewer",
    ),
)


def archive_artifact_specs() -> tuple[tuple[str, str, str, str, str, str, str, str], ...]:
    """Return the stable reviewer-oriented archive selection."""
    return _ARTIFACT_SPECS


def build_archive_manifest(
    repo_root: str | Path | None = None,
    artifact_specs: tuple[tuple[str, str, str, str, str, str, str, str], ...] | None = None,
) -> ArchiveManifest:
    """Build a manifest from exact bytes of the selected repository artifacts."""
    root = (Path(repo_root) if repo_root is not None else _repo_root()).resolve()
    missing: list[str] = []
    artifacts: list[ArchiveArtifact] = []
    specs = _ARTIFACT_SPECS if artifact_specs is None else artifact_specs
    for index, (
        relative,
        artifact_type,
        plane,
        milestone,
        description,
        command,
        role,
        required,
    ) in enumerate(specs, start=1):
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        artifacts.append(
            ArchiveArtifact(
                artifact_id=f"ARC-{index:04d}",
                relative_path=relative,
                artifact_type=artifact_type,
                source_plane=plane,
                milestone=milestone,
                description=description,
                sha256=_sha256(path),
                size_bytes=path.stat().st_size,
                required=required == "required",
                generation_command=command,
                reviewer_role=role,
            )
        )
    if missing:
        raise FileNotFoundError("required archive artifacts are missing: " + ", ".join(missing))
    artifacts_tuple = tuple(sorted(artifacts, key=lambda item: item.relative_path))
    return ArchiveManifest(
        manifest_id="AM-0001",
        generated_at=_GENERATED_AT,
        repository_name="healthcare-ai-governance-platform",
        package_scope=(
            "Selected local synthetic governance outputs and reviewer documentation "
            "for offline review handoff."
        ),
        artifacts=artifacts_tuple,
        artifact_count=len(artifacts_tuple),
        required_artifact_count=sum(artifact.required for artifact in artifacts_tuple),
        total_size_bytes=sum(artifact.size_bytes for artifact in artifacts_tuple),
        source_refs=(
            "outputs/README.md",
            "reports/architecture.md",
            "docs/demo/reviewer-demo-runbook.md",
        ),
        limitations=_LIMITATIONS,
    )


def validate_archive_manifest(
    manifest: ArchiveManifest, repo_root: str | Path | None = None
) -> ArchiveValidationResult:
    """Validate paths, required files, duplicates, and exact-byte checksums."""
    root = (Path(repo_root) if repo_root is not None else _repo_root()).resolve()
    issues: list[str] = []
    paths = [artifact.relative_path for artifact in manifest.artifacts]
    ids = [artifact.artifact_id for artifact in manifest.artifacts]
    duplicate_paths = len(paths) != len(set(paths))
    duplicate_ids = len(ids) != len(set(ids))
    if duplicate_paths:
        issues.append("duplicate artifact paths are present")
    if duplicate_ids:
        issues.append("duplicate artifact IDs are present")
    required_present = True
    checksums_passed = True
    manifest_valid = True
    for artifact in manifest.artifacts:
        candidate = root / artifact.relative_path
        try:
            candidate.resolve().relative_to(root)
        except ValueError:
            issues.append(f"unsafe artifact path: {artifact.relative_path}")
            manifest_valid = False
            continue
        if not candidate.is_file():
            if artifact.required:
                required_present = False
            issues.append(f"missing artifact: {artifact.relative_path}")
            continue
        if _sha256(candidate) != artifact.sha256:
            checksums_passed = False
            issues.append(f"checksum mismatch: {artifact.relative_path}")
    status = (
        ArchiveValidationStatus.PASSED
        if manifest_valid
        and required_present
        and checksums_passed
        and not duplicate_paths
        and not duplicate_ids
        else ArchiveValidationStatus.FAILED
    )
    return ArchiveValidationResult(
        validation_id="AVR-0001",
        evaluated_at=_GENERATED_AT,
        manifest_valid=manifest_valid,
        required_artifacts_present=required_present,
        checksum_validation_passed=checksums_passed,
        duplicate_paths_absent=not duplicate_paths,
        duplicate_artifact_ids_absent=not duplicate_ids,
        status=status,
        issues=tuple(issues),
        limitations=_LIMITATIONS,
    )


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _csv_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def render_offline_handoff_guide(manifest: ArchiveManifest) -> str:
    """Render a concise, deterministic independent verification guide."""
    return f"""# Offline Assurance Verification

## Purpose

Manifest `{manifest.manifest_id}` inventories {manifest.artifact_count} selected
reviewer-facing artifacts from the local healthcare AI governance platform. It is
an offline handoff index over synthetic governance outputs and documentation; it
is not a copied dataset or a deployment package.

## Verify Checksums

From the repository root, run:

```bash
python3 scripts/verify_offline_archive.py
```

The verifier loads `outputs/archive/archive_manifest.json`, checks required files,
and recalculates SHA-256 over exact file bytes. A successful result means the
listed files currently match the manifest.

## Reproduce The Evidence Chain

Run the documented generators in order, then rebuild the manifest:

```bash
python3 scripts/generate_inventory.py
python3 scripts/generate_access.py
python3 scripts/generate_evidence.py
python3 scripts/generate_compliance.py
python3 scripts/generate_reporting.py
python3 scripts/generate_reviewer_bundle.py
python3 scripts/generate_policy_catalog.py
python3 scripts/generate_assurance_history.py
python3 scripts/generate_assurance_pack.py
python3 scripts/generate_review_readiness.py
python3 scripts/generate_offline_archive.py
```

Compare the regenerated manifest and checksum files with the handoff copy.
Deterministic source code and fixed synthetic inputs should produce byte-identical
outputs.

## Interpretation And Boundaries

A matching checksum proves byte equality with the referenced repository file. It
does not prove that the artifact is correct, authentic, complete beyond the
manifest selection, or produced by a real production system. The package is local,
read-only, synthetic-data-only, and non-production.

Checksum integrity does not imply regulatory approval, external certification,
authenticity of a real production system, human governance approval, or production
deployment. No digital signature, PKI, external attestation, or formal approval is
included.

The full manifest contains provenance, source-plane, milestone, reproduction-command,
reviewer-role, size, and SHA-256 metadata for every selected artifact.
"""


def export_archive_bundle(
    manifest: ArchiveManifest, output_dir: str | Path, repo_root: str | Path | None = None
) -> dict[str, int | str]:
    """Write manifest, CSV, checksum list, validation, and guide outputs."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(repo_root) if repo_root is not None else _repo_root()
    validation = validate_archive_manifest(manifest, root)
    _json(destination / ARCHIVE_MANIFEST_FILENAME, manifest.model_dump(mode="json"))
    columns = (
        "artifact_id",
        "relative_path",
        "artifact_type",
        "source_plane",
        "milestone",
        "sha256",
        "size_bytes",
        "required",
        "generation_command",
        "reviewer_role",
    )
    with (destination / ARCHIVE_MANIFEST_CSV_FILENAME).open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for artifact in manifest.artifacts:
            writer.writerow([_csv_value(getattr(artifact, column)) for column in columns])
    checksum_lines = [
        f"{artifact.sha256}  {artifact.relative_path}" for artifact in manifest.artifacts
    ]
    (destination / ARCHIVE_CHECKSUMS_FILENAME).write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    (destination / OFFLINE_HANDOFF_GUIDE_FILENAME).write_text(
        render_offline_handoff_guide(manifest), encoding="utf-8"
    )
    _json(destination / ARCHIVE_VALIDATION_FILENAME, validation.model_dump(mode="json"))
    return {
        "manifest_id": manifest.manifest_id,
        "artifact_count": manifest.artifact_count,
        "required_artifact_count": manifest.required_artifact_count,
    }


def load_archive_manifest(path_or_dir: str | Path) -> ArchiveManifest:
    """Load a canonical archive manifest from a file or archive directory."""
    path = Path(path_or_dir)
    path = path / ARCHIVE_MANIFEST_FILENAME if path.is_dir() else path
    return ArchiveManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_archive_validation(path_or_dir: str | Path) -> ArchiveValidationResult:
    """Load a canonical archive validation result."""
    path = Path(path_or_dir)
    path = path / ARCHIVE_VALIDATION_FILENAME if path.is_dir() else path
    return ArchiveValidationResult.model_validate_json(path.read_text(encoding="utf-8"))


def verify_archive(
    path_or_dir: str | Path, repo_root: str | Path | None = None
) -> ArchiveValidationResult:
    """Load and verify a manifest without regenerating any governance state."""
    return validate_archive_manifest(load_archive_manifest(path_or_dir), repo_root)


__all__ = [
    "ARCHIVE_OUTPUT_FILENAMES",
    "ArchiveArtifact",
    "ArchiveManifest",
    "ArchiveValidationResult",
    "ArchiveValidationStatus",
    "archive_artifact_specs",
    "build_archive_manifest",
    "export_archive_bundle",
    "load_archive_manifest",
    "load_archive_validation",
    "render_offline_handoff_guide",
    "validate_archive_manifest",
    "verify_archive",
]
