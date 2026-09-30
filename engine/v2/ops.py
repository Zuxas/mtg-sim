"""Engine operations: the ONLY way state changes. Rules and effects return lists of
ops; engine.v2.reducer validates and applies them inside an atomic transition."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Op:
    name: str
    args: tuple = ()

    def __getitem__(self, i):
        return self.args[i]


def op(name: str, *args) -> Op:
    return Op(name, tuple(args))
