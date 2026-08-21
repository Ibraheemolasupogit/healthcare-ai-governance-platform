import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_repository import validate  # noqa: E402


def _tracked_files(repo_root: Path) -> list[Path]:
    """Files git actually tracks/would track — excludes .venv, caches, etc.
    without needing to hardcode ignore rules that duplicate .gitignore."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [repo_root / line for line in result.stdout.splitlines() if line]


def test_repository_structure_is_valid() -> None:
    problems = validate()
    assert problems == [], "\n".join(problems)


def test_no_placeholder_pbix_or_credential_files(repo_root: Path) -> None:
    forbidden_suffixes = {".pbix", ".pem", ".key"}
    offenders = [
        str(path.relative_to(repo_root))
        for path in _tracked_files(repo_root)
        if path.suffix in forbidden_suffixes
    ]
    assert offenders == [], f"unexpected artifacts found: {offenders}"


def test_no_snowflake_account_identifiers_committed(repo_root: Path) -> None:
    # Guards against accidentally introducing a real-looking Snowflake account
    # locator (e.g. "xy12345.us-east-1.snowflakecomputing.com") anywhere in
    # tracked markdown/config.
    account_locator_pattern = re.compile(r"\b[a-z]{2}\d{5}\.[a-z0-9-]+\.snowflakecomputing\.com\b")
    text_files = [
        path for path in _tracked_files(repo_root) if path.suffix in {".md", ".yaml", ".yml"}
    ]

    offenders = [
        str(path.relative_to(repo_root))
        for path in text_files
        if path.is_file() and account_locator_pattern.search(path.read_text(errors="ignore"))
    ]

    assert offenders == [], f"possible Snowflake account identifier found in: {offenders}"
