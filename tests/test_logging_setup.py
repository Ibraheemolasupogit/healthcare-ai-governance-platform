import logging

from governance_platform.core.logging_setup import configure_logging, get_logger


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("governance_platform.test")
    assert logger.name == "governance_platform.test"


def test_configure_logging_sets_root_level() -> None:
    configure_logging(level="DEBUG")
    assert logging.getLogger().level == logging.DEBUG

    configure_logging(level="INFO")
