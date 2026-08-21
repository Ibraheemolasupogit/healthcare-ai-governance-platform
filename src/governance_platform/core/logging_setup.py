"""Structured-ish logging setup shared by future governance plane modules.

Foundation utility only: configures the standard library logger with a
consistent format. No governance events are logged yet — there is nothing
to log until the governance planes are implemented.
"""

from __future__ import annotations

import logging

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """(Re)configure root logging for the given level.

    Safe to call more than once (e.g. if settings are reloaded); each call
    replaces any handlers a previous call installed rather than being a
    silent no-op, which is what ``logging.basicConfig`` does by default
    once the root logger already has handlers.
    """
    logging.basicConfig(level=level, format=_DEFAULT_FORMAT, force=True)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, e.g. ``get_logger(__name__)``."""
    return logging.getLogger(name)
