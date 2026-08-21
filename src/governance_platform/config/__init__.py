"""Non-secret configuration loading for the governance platform.

Foundation utility only — no governance logic. See ``config/README.md`` at
the repository root for the intended shape of settings files.
"""

from governance_platform.config.loader import Settings, load_settings

__all__ = ["Settings", "load_settings"]
