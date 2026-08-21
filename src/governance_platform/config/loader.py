"""Load non-secret platform settings from a YAML file.

This is a foundation utility for Milestone 1 — it loads and validates the
generic settings shape shown in ``config/settings.example.yaml``. It has no
awareness of any governance domain (datasets, access, audit, risk); those
will define their own settings once implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Validated platform settings.

    Field defaults intentionally match ``config/settings.example.yaml`` so
    the platform has a sane configuration even if no settings file is
    provided.
    """

    platform_name: str = Field(default="healthcare-ai-governance-platform")
    environment: Literal["dev", "sandbox", "staging"] = Field(default="dev")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")


def load_settings(path: str | Path) -> Settings:
    """Load and validate settings from a YAML file at ``path``.

    Raises ``FileNotFoundError`` if ``path`` does not exist and
    ``pydantic.ValidationError`` if its contents don't match ``Settings``.
    """
    settings_path = Path(path)
    if not settings_path.is_file():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")

    raw = yaml.safe_load(settings_path.read_text()) or {}
    return Settings.model_validate(raw)
