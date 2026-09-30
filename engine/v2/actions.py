"""Typed player actions (frozen). Every action names its player. legal_actions() returns
the complete legal set; Game.apply refuses anything else.

Implementation note (spec section 6): attacker and blocker declarations are staged as one
decision per creature (ChooseAttack / ChooseBlock) and committed atomically when the last
creature is decided -- every legal declaration is reachable, and the full cartesian set
never has to be enumerated. Blocks in the milestone card set have no cross-creature
requirements, so per-creature staging is exact."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class DeclareKeep:
    player: int


@dataclass(frozen=True)
class DeclareMulligan:
    player: int


@dataclass(frozen=True)
class BottomCards:
    player: int
    cards: tuple                    # ordered: cards[0] goes to the bottom first, cards[-1] ends lowest


@dataclass(frozen=True)
class PassPriority:
    player: int


@dataclass(frozen=True)
class PlayLand:
    player: int
    oid: int


@dataclass(frozen=True)
class ActivateManaAbility:
    player: int
    oid: int


@dataclass(frozen=True)
class ProposeCast:
    player: int
    oid: int


@dataclass(frozen=True)
class ChooseTargets:
    player: int
    targets: tuple


@dataclass(frozen=True)
class PayCost:
    player: int
    assignment: tuple               # ((colour, amount), ...) sorted


@dataclass(frozen=True)
class ChooseAttack:
    player: int
    oid: int
    attacks: bool


@dataclass(frozen=True)
class ChooseBlock:
    player: int
    blocker: int
    attacker: object                # attacker oid or None


@dataclass(frozen=True)
class AssignCombatDamage:
    player: int
    attacker: int
    division: tuple                 # ((blocker, amount), ...) in blocker-oid order


@dataclass(frozen=True)
class DiscardToHandSize:
    player: int
    cards: tuple


@dataclass(frozen=True)
class Concede:
    player: int


ACTION_TYPES = {c.__name__: c for c in (DeclareKeep, DeclareMulligan, BottomCards, PassPriority, PlayLand,
                                        ActivateManaAbility, ProposeCast, ChooseTargets, PayCost, ChooseAttack,
                                        ChooseBlock, AssignCombatDamage, DiscardToHandSize, Concede)}


def to_record(a) -> list:
    return [type(a).__name__] + [_plain(getattr(a, f.name)) for f in fields(a)]


def from_record(rec) -> object:
    cls = ACTION_TYPES[rec[0]]
    vals = [_tuplify(v) for v in rec[1:]]
    return cls(*vals)


def _plain(v):
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    return v


def _tuplify(v):
    if isinstance(v, list):
        return tuple(_tuplify(x) for x in v)
    return v
