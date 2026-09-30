"""Append-only event log. Events are grouped into atomic Transitions; each transition is
serialised canonically and chained into a running SHA-256 (spec section 8).

The chain is computed lazily and incrementally: appending is cheap, and the first time a
transition's hash or the log head is requested every earlier link is computed once, in
order. The values are exactly those of an eager chain (the log is append-only and
transitions are immutable), so records and replay compare identical hashes."""
from __future__ import annotations

import hashlib
from typing import NamedTuple

GENESIS = "0" * 64


class Event(NamedTuple):             # immutable; NamedTuple for speed (created ~2k times per game)
    kind: str
    data: tuple = ()                    # tuple of (key, value) pairs, canonical (sorted keys)


class Transition:
    """Immutable by convention (__slots__, no setters). `hash` is the chained SHA-256 up to
    and including this transition."""
    __slots__ = ("index", "kind", "events", "_log")

    def __init__(self, index: int, kind: str, events: tuple, log: "EventLog"):
        self.index, self.kind, self.events, self._log = index, kind, events, log

    @property
    def hash(self) -> str:
        return self._log.hash_at(self.index)

    def __repr__(self):
        return f"Transition({self.index}, {self.kind!r}, {len(self.events)} events)"


def _ser(obj) -> str:
    # Canonical: event payloads are sorted tuples of ints / strs / bools / None / tuples,
    # whose repr is deterministic across runs and platforms for a given Python version.
    return repr(obj)


class EventLog:
    def __init__(self):
        self.transitions: list = []
        self._hashes: list = []                 # chained hashes computed so far (prefix)

    def append(self, kind: str, events: list) -> Transition:
        t = Transition(len(self.transitions), kind, tuple(events), self)
        self.transitions.append(t)
        return t

    def hash_at(self, index: int) -> str:
        hs = self._hashes
        prev = hs[-1] if hs else GENESIS
        for t in self.transitions[len(hs):index + 1]:
            body = _ser((t.index, t.kind, tuple((e.kind, e.data) for e in t.events)))
            prev = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
            hs.append(prev)
        return hs[index]

    @property
    def head(self) -> str:
        return self.hash_at(len(self.transitions) - 1) if self.transitions else GENESIS


def ev(kind: str, **data) -> Event:
    return Event(kind, tuple(sorted(data.items())))
