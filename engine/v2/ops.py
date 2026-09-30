"""Engine operations: the ONLY way state changes. Rules and effects return lists of
ops; engine.v2.reducer validates and applies them inside an atomic transition."""
from __future__ import annotations

from typing import NamedTuple


class Op(NamedTuple):                # immutable; NamedTuple for speed
    name: str
    args: tuple = ()


def op(name: str, *args) -> Op:
    return Op(name, tuple(args))
