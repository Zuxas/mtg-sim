"""Casting legality (CR 601.2, 307.1, 115.5) and targets (CR 601.2c, 608.2b). Pure."""
from __future__ import annotations

from engine.v2.rules.mana import payable_with_sources

MAIN_STEPS = ("main1", "main2")
TARGET_SPEC = {                     # effect_key -> what it may target
    "lightning_bolt": ("creature", "player"),
    "giant_growth": ("creature",),
    "counterspell": ("spell",),
    "lava_spike": ("player",),
    "lightning_helix": ("creature", "player"),
    "skullcrack": ("player",),
}
MODAL = {"boros_charm": 3}                                  # effect_key -> number of modes (choose one)
MODE_TARGETS = {                                            # (key, mode) -> target slots (kinds per slot)
    ("boros_charm", 0): (("player",),),                     # 4 damage to target player (no planeswalkers)
    ("boros_charm", 1): (),                                 # permanents you control gain indestructible
    ("boros_charm", 2): (("creature",),),                   # target creature gains double strike
}
# Searing Blaze: "target player or planeswalker and target creature that player ... controls"
DEPENDENT = {"searing_blaze"}


def target_slots(key, mode=None) -> tuple:
    if (key, mode) in MODE_TARGETS:
        return MODE_TARGETS[(key, mode)]
    if key in DEPENDENT:
        return (("player",), ("creature",))
    spec = TARGET_SPEC.get(key)
    return (spec,) if spec else ()


def target_choices(state, key, mode=None, exclude_sid=None) -> list:
    """Every complete legal target assignment (CR 601.2c, 115.1); [()] when untargeted."""
    slots = target_slots(key, mode)
    if not slots:
        return [()]
    if key in DEPENDENT:
        return [(("player", p), ("obj", c)) for p in (0, 1) if state.lost[p] is None
                for c in creatures_on_battlefield(state) if state.objects[c].controller == p]
    return [(t,) for t in options_for_kinds(state, slots[0], exclude_sid)]


def castable_modes(state, key, exclude_sid=None) -> list:
    """CR 700.2a: a mode that would be illegal (no legal targets) can't be chosen."""
    return [m for m in range(MODAL[key]) if target_choices(state, key, m, exclude_sid)]


def slot_still_legal(state, key, i, target, targets) -> bool:
    """CR 608.2b per target; Searing Blaze's creature must still be controlled by the targeted player."""
    if not target_still_legal(state, target, key):
        return False
    if key in DEPENDENT and i == 1:
        return state.objects[target[1]].controller == targets[0][1]
    return True


def creatures_on_battlefield(state) -> list:
    return [oid for oid in state.battlefield() if state.definition(oid).is_creature]


def target_options(state, effect_key, exclude_sid=None) -> list:
    """Legal target choices for a spell with `effect_key` (single-target spells only)."""
    return options_for_kinds(state, TARGET_SPEC.get(effect_key), exclude_sid)


def options_for_kinds(state, spec, exclude_sid=None) -> list:
    """Legal single targets of the given kinds (creature / player / spell)."""
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


def target_still_legal_kinds(state, target, kinds) -> bool:
    """CR 608.2b for an ability whose targets are of the given kinds."""
    if target[0] == "obj" and "creature" not in kinds:
        return False
    if target[0] == "player" and "player" not in kinds:
        return False
    return target_still_legal(state, target, None)


def sorcery_timing_ok(state, player) -> bool:
    """CR 307.1 / 305.2 timing: own main phase, empty stack, has priority."""
    return player == state.active and state.step in MAIN_STEPS and not state.stack


def can_propose_cast(state, player, oid, avail=None, timing=None, targets_ok=None) -> bool:
    """ProposeCast is legal only when a legal completion exists (spec 7.4)."""
    o = state.objects.get(oid)
    if o is None or o.zone != "hand" or o.owner != player:
        return False
    d = state.definition(oid)
    if d.is_land:
        return False
    if not d.is_instant and not (sorcery_timing_ok(state, player) if timing is None else timing):
        return False
    key = d.effect_key
    if key in TARGET_SPEC or key in MODAL or key in DEPENDENT:
        if targets_ok is None:
            targets_ok = {}
        if key not in targets_ok:                           # per-decision cache (same answer per key)
            targets_ok[key] = bool(castable_modes(state, key)) if key in MODAL else \
                target_choices(state, key) != []
        if not targets_ok[key]:
            return False
    return payable_with_sources(state, player, d.cost_symbols, avail)


def can_play_land(state, player, oid) -> bool:
    o = state.objects.get(oid)
    return (o is not None and o.zone == "hand" and o.owner == player and state.definition(oid).is_land
            and sorcery_timing_ok(state, player) and state.land_played[player] == 0)
