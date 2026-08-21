from pathlib import Path

import pytest
from pydantic import ValidationError

from governance_platform.config import Settings, load_settings


def test_load_settings_reads_example_file(repo_root: Path) -> None:
    settings = load_settings(repo_root / "config" / "settings.example.yaml")

    assert settings.platform_name == "healthcare-ai-governance-platform"
    assert settings.environment == "dev"
    assert settings.log_level == "INFO"


def test_load_settings_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "does-not-exist.yaml")


def test_load_settings_rejects_invalid_environment(tmp_path: Path) -> None:
    bad_settings = tmp_path / "bad.yaml"
    bad_settings.write_text("environment: production\n")

    with pytest.raises(ValidationError):
        load_settings(bad_settings)


def test_settings_defaults_without_a_file() -> None:
    defaults = Settings()

    assert defaults.environment == "dev"
    assert defaults.log_level == "INFO"
