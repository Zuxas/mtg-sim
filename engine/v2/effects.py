"""Resolution effects for the milestone card set. An effect receives an EffectContext
(read-only: controller, the resolving entry, its targets AFTER the CR 608.2b re-check, and
frozen facts about those targets) and returns ops. Effects never see GameState and have
no choice hook in milestone one (spec section 5), so a resolution is always atomic."""
from __future__ import annotations

from dataclasses import dataclass

from engine.v2.ops import op


@dataclass(frozen=True)
class EffectContext:
    controller: int
    source_oid: int
    legal_targets: tuple            # (("obj", oid) | ("player", p) | ("stack", sid, oid), ...)
    mode: object = None             # chosen mode (CR 700.2a)
    slots: tuple = ()               # per target slot: the target, or None if it became illegal (CR 608.2b)
    facts: tuple = ()               # read-only facts fixed at resolution (see FACTS)


def _damage(ctx, t, n):
    """n damage from the resolving spell to one legal target (CR 120.3)."""
    if t[0] == "obj":
        return op("damage_creature", ctx.source_oid, t[1], n)
    return op("damage_player", ctx.source_oid, t[1], n)


def lightning_bolt(ctx):
    return [_damage(ctx, t, 3) for t in ctx.legal_targets]


def lava_spike(ctx):
    # "target player or planeswalker": no planeswalker is supported, so targets are players
    return [_damage(ctx, t, 3) for t in ctx.legal_targets if t[0] == "player"]


def skullcrack(ctx):
    # "Players can't gain life this turn. Damage can't be prevented this turn. Skullcrack deals 3
    # damage to target player or planeswalker." (no planeswalkers are supported)
    out = [op("add_turn_effect", "no_lifegain", 0), op("add_turn_effect", "no_lifegain", 1),
           op("add_turn_effect", "no_prevention", None)]
    return out + [_damage(ctx, t, 3) for t in ctx.legal_targets if t[0] == "player"]


def boros_charm(ctx):
    if ctx.mode == 0:
        return [_damage(ctx, t, 4) for t in ctx.legal_targets if t[0] == "player"]
    if ctx.mode == 1:                     # the set of permanents is fixed now (CR 611.2c)
        return [op("add_turn_effect", "indestructible", oid) for oid in ctx.facts[0]]
    return [op("add_turn_effect", "double_strike", t[1]) for t in ctx.legal_targets if t[0] == "obj"]


def searing_blaze(ctx):
    n = 3 if ctx.facts[0] else 1          # landfall: a land entered under its controller's control this turn
    return [_damage(ctx, t, n) for t in ctx.slots if t is not None]


def rift_bolt(ctx):
    return [_damage(ctx, t, 3) for t in ctx.legal_targets]


def skewer_the_critics(ctx):
    return [_damage(ctx, t, 3) for t in ctx.legal_targets]


def lightning_helix(ctx):
    # Reached only with a legal target: with none the spell doesn't resolve (CR 608.2b), so no life
    return [_damage(ctx, t, 3) for t in ctx.legal_targets] + [op("gain_life", ctx.controller, 3)]


def giant_growth(ctx):
    return [op("eot_mod", t[1], 3, 3) for t in ctx.legal_targets if t[0] == "obj"]


def counterspell(ctx):
    out = []
    for t in ctx.legal_targets:
        if t[0] == "stack":                              # CR 701.6a
            out += [op("remove_entry", t[1]), op("move", t[2], "graveyard", "end"),
                    op("note", "SpellCountered", t[1])]
    return out


def divination(ctx):
    return [op("draw", ctx.controller), op("draw", ctx.controller)]


def mutagenic_growth(ctx):
    # "Target creature gets +2/+2 until end of turn." ({G/P}: paid as announced, CR 107.4f)
    return [op("eot_mod", t[1], 2, 2) for t in ctx.legal_targets if t[0] == "obj"]


def violent_urge(ctx):
    # "Target creature gets +1/+0 and gains first strike until end of turn. Delirium -- If there are four or
    # more card types among cards in your graveyard, that creature gains double strike until end of turn."
    # The delirium condition is read as the spell resolves (facts), while Violent Urge is still on the stack.
    out = []
    for t in ctx.legal_targets:
        if t[0] == "obj":
            out += [op("eot_mod", t[1], 1, 0), op("add_turn_effect", "first_strike", t[1])]
            if ctx.facts[0]:
                out.append(op("add_turn_effect", "double_strike", t[1]))
    return out


def lava_dart(ctx):
    return [_damage(ctx, t, 1) for t in ctx.legal_targets]              # "1 damage to any target"


EFFECTS = {
    "lightning_bolt": lightning_bolt,
    "giant_growth": giant_growth,
    "counterspell": counterspell,
    "divination": divination,
    "lava_spike": lava_spike,
    "lightning_helix": lightning_helix,
    "skullcrack": skullcrack,
    "boros_charm": boros_charm,
    "searing_blaze": searing_blaze,
    "rift_bolt": rift_bolt,
    "skewer_the_critics": skewer_the_critics,
    "mutagenic_growth": mutagenic_growth,
    "violent_urge": violent_urge,
    "lava_dart": lava_dart,
}


def facts(state, key, entry) -> tuple:
    """Read-only facts an effect needs, taken at resolution."""
    if key == "searing_blaze":
        return (state.lands_entered_turn[entry.controller] > 0,)
    if key == "violent_urge":
        from engine.v2.rules.statics import delirium
        return (delirium(state, entry.controller),)
    if key == "boros_charm" and entry.mode == 1:
        return (tuple(sorted(o for o in state.zones[("bf",)] if state.objects[o].controller == entry.controller)),)
    return ()


def check_registry():
    """Every SUPPORTED non-permanent card has an effect implementation (import-time)."""
    from engine.v2.cards import PERMANENT_KEYS, SUPPORTED
    from engine.v2.rules.library import LIBRARY            # spells whose resolution pauses for a library choice
    missing = [n for n, (k, _v) in SUPPORTED.items() if k not in EFFECTS and k not in PERMANENT_KEYS
               and k not in LIBRARY]
    if missing:
        raise RuntimeError(f"SUPPORTED cards without an effect implementation: {missing}")


check_registry()
