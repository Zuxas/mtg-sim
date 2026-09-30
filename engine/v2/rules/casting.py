"""Casting legality (CR 601.2, 307.1, 115.5) and targets (CR 601.2c, 608.2b). Pure."""
from __future__ import annotations

from engine.v2.rules.mana import payable_with_sources

MAIN_STEPS = ("main1", "main2")
TARGET_SPEC = {                     # effect_key -> what it may target
    "lightning_bolt": ("creature", "player"),
    "giant_growth": ("creature",),
    "counterspell": ("spell",),
}


def creatures_on_battlefield(state) -> list:
    return [oid for oid in state.battlefield() if state.definition(oid).is_creature]


def target_options(state, effect_key, exclude_sid=None) -> list:
    """Legal target choices for a spell with `effect_key` (single-target spells only)."""
    spec = TARGET_SPEC.get(effect_key)
    if not spec:
        return []
    out = []
    if "creature" in spec:
        out += [("obj", oid) for oid in creatures_on_battlefield(state)]
    if "player" in spec:
        out += [("player", 0), ("player", 1)]
    if "spell" in spec:                                   # CR 115.5: not itself
        out += [("stack", e.sid) for e in state.stack if e.state == "cast" and e.sid != exclude_sid]
    return out


def target_still_legal(state, target, effect_key) -> bool:
    """CR 608.2b: a target no longer in the zone it was in when targeted is illegal."""
    kind = target[0]
    if kind == "obj":
        o = state.objects.get(target[1])
        return o is not None and o.zone == "battlefield" and state.definition(o.oid).is_creature
    if kind == "player":
        return state.lost[target[1]] is None
    if kind == "stack":
        e = state.entry(target[1])
        return e is not None and e.state == "cast"
    return False


def sorcery_timing_ok(state, player) -> bool:
    """CR 307.1 / 305.2 timing: own main phase, empty stack, has priority."""
    return player == state.active and state.step in MAIN_STEPS and not state.stack


def can_propose_cast(state, player, oid) -> bool:
    """ProposeCast is legal only when a legal completion exists (spec 7.4)."""
    o = state.objects.get(oid)
    if o is None or o.zone != "hand" or o.owner != player:
        return False
    d = state.definition(oid)
    if d.is_land:
        return False
    if not d.is_instant and not sorcery_timing_ok(state, player):
        return False
    if d.effect_key in TARGET_SPEC and not target_options(state, d.effect_key):
        return False
    return payable_with_sources(state, player, d.cost_symbols)


def can_play_land(state, player, oid) -> bool:
    o = state.objects.get(oid)
    return (o is not None and o.zone == "hand" and o.owner == player and state.definition(oid).is_land
            and sorcery_timing_ok(state, player) and state.land_played[player] == 0)
