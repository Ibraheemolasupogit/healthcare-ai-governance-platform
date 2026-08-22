from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from governance_platform.reviewer.archive import (
    ArchiveArtifact,
    ArchiveManifest,
    ArchiveValidationStatus,
    archive_artifact_specs,
    build_archive_manifest,
    export_archive_bundle,
    load_archive_manifest,
    load_archive_validation,
    validate_archive_manifest,
    verify_archive,
)


def _fixture_repo(tmp_path: Path) -> Path:
    for relative, *_ in archive_artifact_specs():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"synthetic fixture: {relative}\n", encoding="utf-8")
    return tmp_path


def test_archive_manifest_rejects_unsafe_paths() -> None:
    with pytest.raises(ValidationError):
        ArchiveArtifact(
            artifact_id="ARC-0001",
            relative_path="../outside.txt",
            artifact_type="text",
            source_plane="test",
            milestone="13",
            description="unsafe",
            sha256="0" * 64,
            size_bytes=0,
            required=True,
            generation_command="test",
            reviewer_role="reviewer",
        )


def test_manifest_generation_is_ordered_and_deterministic(tmp_path: Path) -> None:
    root = _fixture_repo(tmp_path)
    first = build_archive_manifest(root)
    second = build_archive_manifest(root)

    assert [item.relative_path for item in first.artifacts] == sorted(
        item.relative_path for item in first.artifacts
    )
    assert first == second
    assert first.total_size_bytes == sum(item.size_bytes for item in first.artifacts)


def test_checksum_validation_detects_change_and_missing_required_file(tmp_path: Path) -> None:
    root = _fixture_repo(tmp_path)
    manifest = build_archive_manifest(root)
    target = root / manifest.artifacts[0].relative_path
    target.write_text("changed\n", encoding="utf-8")
    changed = validate_archive_manifest(manifest, root)

    assert changed.status == ArchiveValidationStatus.FAILED
    assert any("checksum mismatch" in issue for issue in changed.issues)

    target.unlink()
    missing = validate_archive_manifest(manifest, root)
    assert missing.required_artifacts_present is False
    assert missing.status == ArchiveValidationStatus.FAILED


def test_duplicate_paths_and_ids_are_reported(tmp_path: Path) -> None:
    path = tmp_path / "artifact.txt"
    path.write_text("x", encoding="utf-8")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    artifact = ArchiveArtifact(
        artifact_id="ARC-0001",
        relative_path="artifact.txt",
        artifact_type="text",
        source_plane="test",
        milestone="13",
        description="fixture",
        sha256=checksum,
        size_bytes=1,
        required=True,
        generation_command="test",
        reviewer_role="reviewer",
    )
    manifest = ArchiveManifest(
        manifest_id="AM-0001",
        generated_at="2025-03-24T00:00:00",
        repository_name="fixture",
        package_scope="fixture",
        artifacts=(artifact, artifact),
        artifact_count=2,
        required_artifact_count=2,
        total_size_bytes=2,
        source_refs=("fixture",),
        limitations=("fixture",),
    )

    result = validate_archive_manifest(manifest, tmp_path)
    assert result.duplicate_paths_absent is False
    assert result.duplicate_artifact_ids_absent is False
    assert result.status == ArchiveValidationStatus.FAILED


def test_export_reload_and_read_only_verification(tmp_path: Path) -> None:
    root = _fixture_repo(tmp_path / "repo")
    output = tmp_path / "archive"
    manifest = build_archive_manifest(root)
    export_archive_bundle(manifest, output, root)

    assert load_archive_manifest(output) == manifest
    assert load_archive_validation(output).status == ArchiveValidationStatus.PASSED
    assert verify_archive(output, root).status == ArchiveValidationStatus.PASSED
    assert (output / "archive_file_checksums.sha256").read_text().count(
        "\n"
    ) == manifest.artifact_count
