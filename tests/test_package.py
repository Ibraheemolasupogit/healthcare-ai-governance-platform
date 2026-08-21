import re

import governance_platform
from governance_platform import access, audit, inventory, reporting, responsible_ai, risk


def test_package_version_is_semver() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", governance_platform.__version__)


def test_placeholder_plane_modules_import_cleanly() -> None:
    # Milestone 1 ships these as placeholders with no governance logic; the
    # meaningful assertion is that the package structure is importable and
    # each plane module has a docstring describing its intended scope.
    for module in (inventory, access, audit, risk, responsible_ai, reporting):
        assert module.__doc__ is not None
        assert module.__doc__.strip() != ""
