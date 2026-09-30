"""
engine/strict.py -- strict simulation mode switch (spec harness/specs/2026-09-30-strict-mode.md).

With MTG_SIM_STRICT=1, code paths that used to swallow an error and keep going (a
card handler that raised, a failed sideboard, an APL exception, an unknown effect
primitive) raise StrictModeError instead, so a published number is either a raw
simulation or an explicit error. Default OFF: behaviour unchanged.

The flag is read at call time, so a launcher can set it for its subprocesses and
tests can toggle it in-process.
"""
from __future__ import annotations

import os


class StrictModeError(RuntimeError):
    """A result would have been silently altered; strict mode refuses."""


def is_strict() -> bool:
    return os.environ.get("MTG_SIM_STRICT") == "1"


def reraise_if_strict(exc: BaseException, where: str) -> None:
    """Call inside an `except` that would otherwise swallow `exc`."""
    if is_strict():
        raise StrictModeError(f"{where}: {type(exc).__name__}: {exc}") from exc
