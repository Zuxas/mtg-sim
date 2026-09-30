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


def lightning_bolt(ctx):
    out = []
    for t in ctx.legal_targets:
        if t[0] == "obj":
            out.append(op("damage_creature", ctx.source_oid, t[1], 3))
        elif t[0] == "player":
            out.append(op("damage_player", ctx.source_oid, t[1], 3))
    return out


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
}


def check_registry():
    """Every SUPPORTED non-permanent card has an effect implementation (import-time)."""
    from engine.v2.cards import SUPPORTED
    missing = [n for n, (k, _v) in SUPPORTED.items()
               if k not in EFFECTS and k not in ("basic_land", "vanilla_creature")]
    if missing:
        raise RuntimeError(f"SUPPORTED cards without an effect implementation: {missing}")


check_registry()
