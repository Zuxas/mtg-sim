"""Per-seat immutable observation (spec section 4, I9). Hidden information respected:
own hand (incl. a provisional mulligan hand) is visible, the opponent's hand is a count,
libraries are counts, staged hidden choices (mulligan bottoms) are never shown."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermanentView:
    oid: int
    name: str
    owner: int
    controller: int
    tapped: bool
    damage: int
    power: object
    toughness: object
    can_attack: bool


@dataclass(frozen=True)
class StackView:
    sid: str
    name: str
    controller: int
    state: str
    targets: tuple


@dataclass(frozen=True)
class Observation:
    seat: int
    turn: int
    step: str
    active: int
    priority: object
    starting_player: int
    life: tuple
    my_pool: tuple
    opp_pool: tuple
    hand: tuple                     # ((oid, name), ...)
    opp_hand_count: int
    library_counts: tuple
    battlefield: tuple              # PermanentView...
    graveyards: tuple               # (tuple of names, tuple of names)
    stack: tuple                    # StackView...
    pending: tuple                  # (kind, player, info)
    mull_counts: tuple
    kept: tuple
    attackers: tuple
    blocks: tuple
    result: object


def observe(state, seat: int) -> Observation:
    name = lambda oid: state.instances[state.objects[oid].ciid].name        # noqa: E731
    bf = []
    for oid in state.battlefield():
        o = state.objects[oid]
        d = state.definition(oid)
        bf.append(PermanentView(oid, d.name, o.owner, o.controller, o.tapped, o.damage,
                                state.power(oid) if d.is_creature else None,
                                state.toughness(oid) if d.is_creature else None,
                                d.is_creature and (o.controlled_since < state.turn or d.has("Haste"))))
    stack = tuple(StackView(e.sid, state.instances[e.ciid].name, e.controller, e.state, tuple(e.targets))
                  for e in state.stack)
    opp = 1 - seat
    return Observation(
        seat=seat, turn=state.turn, step=state.step, active=state.active, priority=state.priority,
        starting_player=state.starting_player, life=tuple(state.life),
        my_pool=tuple(sorted(state.pools[seat].items())), opp_pool=tuple(sorted(state.pools[opp].items())),
        hand=tuple((oid, name(oid)) for oid in state.zones[(seat, "hand")]),
        opp_hand_count=len(state.zones[(opp, "hand")]),
        library_counts=(len(state.zones[(0, "library")]), len(state.zones[(1, "library")])),
        battlefield=tuple(bf),
        graveyards=tuple(tuple(name(o) for o in state.zones[(p, "graveyard")]) for p in (0, 1)),
        stack=stack,
        pending=state.pending.view() if state.pending else (),
        mull_counts=tuple(state.mull_count), kept=tuple(state.kept),
        attackers=tuple(state.attackers), blocks=tuple(sorted(state.blocks.items())),
        result=state.result)
