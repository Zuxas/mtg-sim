"""Per-seat immutable observation (spec section 4, I9). Hidden information respected:
own hand (incl. a provisional mulligan hand) is visible, the opponent's hand is a count,
libraries are counts, staged hidden choices (mulligan bottoms) are never shown. A seat sees its
OWN staged combat choices (attackers and damage division for the active player, blocks for the
defending player) but never the opponent's."""
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
    can_attack: bool                # CR 508.1a: eligible to be declared as an attacker right now


@dataclass(frozen=True)
class StackView:
    sid: str
    name: str
    controller: int
    state: str
    targets: tuple
    mode: object = None


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
    pending_triggers: tuple         # ((tid, controller, ability key, source card name), ...) -- public
    my_search: tuple                # ((oid, name), ...) matching cards -- ONLY while this seat searches
    turn_effects: tuple             # ((kind, a), ...) public duration effects
    exile: tuple                    # per player: ((oid, name, counters), ...) -- public zone
    my_attack_choices: tuple        # ((oid, attacks), ...) staged by this seat (active player only)
    my_block_choices: tuple         # ((blocker, attacker or None), ...) staged by this seat (defender only)
    my_divisions: tuple             # ((attacker, ((blocker, dmg), ...)), ...) staged by this seat (active only)
    result: object


def _search_view(state, seat) -> tuple:
    pd = state.pending
    if pd is None or pd.kind != "search_choice" or pd.player != seat:
        return ()
    from engine.v2.abilities import fetch_matches
    key = state.continuation.data[0]
    return tuple((oid, state.instances[state.objects[oid].ciid].name)
                 for oid in sorted(state.zones[(seat, "library")]) if fetch_matches(state, key, oid))


def observe(state, seat: int) -> Observation:
    from engine.v2.rules.combat import eligible_attackers
    name = lambda oid: state.instances[state.objects[oid].ciid].name        # noqa: E731
    can_attack = set(eligible_attackers(state))        # active player, controller, untapped, sickness/haste
    bf = []
    for oid in state.battlefield():
        o = state.objects[oid]
        d = state.definition(oid)
        bf.append(PermanentView(oid, d.name, o.owner, o.controller, o.tapped, o.damage,
                                state.power(oid) if d.is_creature else None,
                                state.toughness(oid) if d.is_creature else None,
                                oid in can_attack))
    from engine.v2.abilities import ABILITY_NAMES
    stack = tuple(StackView(e.sid, state.instances[e.ciid].name if e.state != "ability"
                            else f"{ABILITY_NAMES[e.ability]} ({state.instances[e.ciid].name})",
                            e.controller, e.state, tuple(e.targets), e.mode)
                  for e in state.stack)
    opp = 1 - seat
    attacking, defending = seat == state.active, seat != state.active
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
        pending_triggers=tuple((t.tid, t.controller, t.key, state.instances[t.ciid].name)
                               for t in state.pending_triggers),
        my_search=_search_view(state, seat),
        turn_effects=tuple(tuple(e) for e in state.turn_effects),
        exile=tuple(tuple((o, name(o), state.objects[o].counters) for o in state.zones[(p, "exile")]) for p in (0, 1)),
        my_attack_choices=tuple(sorted(state.attack_choices.items())) if attacking else (),
        my_block_choices=tuple(sorted(state.block_choices.items(), key=lambda kv: kv[0])) if defending else (),
        my_divisions=tuple(sorted(state.divisions.items())) if attacking else (),
        result=state.result)
