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


EFFECTS = {
    "lightning_bolt": lightning_bolt,
    "giant_growth": giant_growth,
    "counterspell": counterspell,
    "divination": divination,
    "lava_spike": lava_spike,
    "lightning_helix": lightning_helix,
}


def check_registry():
    """Every SUPPORTED non-permanent card has an effect implementation (import-time)."""
    from engine.v2.cards import PERMANENT_KEYS, SUPPORTED
    missing = [n for n, (k, _v) in SUPPORTED.items() if k not in EFFECTS and k not in PERMANENT_KEYS]
    if missing:
        raise RuntimeError(f"SUPPORTED cards without an effect implementation: {missing}")


check_registry()
