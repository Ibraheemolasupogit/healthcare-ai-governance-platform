import re

import governance_platform
from governance_platform import access, audit, inventory, reporting, responsible_ai, risk


def test_package_version_is_semver() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", governance_platform.__version__)


def test_placeholder_plane_modules_import_cleanly() -> None:
    # audit/risk/responsible_ai/reporting remain Milestone 1 placeholders with
    # no governance logic; inventory is implemented as of Milestone 2 (see
    # tests/test_inventory_*.py) and access is implemented as of Milestone 3
    # (see tests/test_access_*.py). The meaningful assertion here is that the
    # package structure is importable and each plane module has a docstring
    # describing its (implemented or intended) scope.
    for module in (inventory, access, audit, risk, responsible_ai, reporting):
        assert module.__doc__ is not None
        assert module.__doc__.strip() != ""
