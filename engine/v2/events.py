"""Append-only event log. Events are grouped into atomic Transitions; each transition is
serialised canonically and chained into a running SHA-256 (spec section 8)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    kind: str
    data: tuple = ()                    # tuple of (key, value) pairs, canonical


@dataclass(frozen=True)
class Transition:
    index: int
    kind: str
    events: tuple
    hash: str


def _ser(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class EventLog:
    transitions: list = field(default_factory=list)
    head: str = "0" * 64

    def append(self, kind: str, events: list) -> Transition:
        body = _ser([len(self.transitions), kind, [[e.kind, list(e.data)] for e in events]])
        h = hashlib.sha256((self.head + body).encode("utf-8")).hexdigest()
        t = Transition(len(self.transitions), kind, tuple(events), h)
        self.transitions.append(t)
        self.head = h
        return t


def ev(kind: str, **data) -> Event:
    return Event(kind, tuple(sorted(data.items())))
