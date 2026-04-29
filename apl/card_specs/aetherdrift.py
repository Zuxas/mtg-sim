"""Aetherdrift — 15 cards (racing/vehicle themed Standard set)

Key mechanics: Exhaust (tap to activate once per turn), vehicle crew,
Speed counters on creatures.

Spec: apl/card_specs/aetherdrift.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power, safe_toughness

STOCK_UP          = "Stock Up"
MARAUDING_MAKO    = "Marauding Mako"
HUATLI            = "Huatli, Poet of Unity"
CREATIVE_OUTBURST = "Creative Outburst"
EXPLOSIVE_ENTRY   = "Explosive Entry"
FORSAKE_WORLDLY   = "Forsake the Worldly"

ALL_NAMES = {STOCK_UP, MARAUDING_MAKO, HUATLI,
             CREATIVE_OUTBURST, EXPLOSIVE_ENTRY, FORSAKE_WORLDLY}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Aetherdrift cards. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def _on_resolve(gs, name: str, card, opponent):
    if name == STOCK_UP:
        # Look at top 5, put 2 in hand
        top5 = gs.zones.library[:5]
        gs.zones.library = gs.zones.library[5:]
        top5.sort(key=lambda c: -getattr(c,'cmc',0))
        kept = top5[:2]
        rest = top5[2:]
        gs.zones.hand.extend(kept)
        gs.zones.library.extend(rest)
        gs._log(f"  Stock Up: draw 2 from top 5")

    elif name == MARAUDING_MAKO:
        gs._log(f"  Marauding Mako: 1/1, gains +1/+1 each time you discard")

    elif name == HUATLI:
        # ETB: search for basic land, put into hand
        lands = [c for c in gs.zones.library if c.is_land()]
        if lands:
            gs.zones.library.remove(lands[0])
            gs.zones.hand.append(lands[0])
            gs._log(f"  Huatli: ETB tutor basic land to hand")

    elif name == CREATIVE_OUTBURST:
        # 5 damage to any target + look at top 5
        gs.damage_dealt += 5
        top5 = gs.zones.library[:5]
        gs.zones.library = gs.zones.library[5:]
        if top5:
            best = max(top5, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.append(best)
            top5.remove(best)
            gs.zones.library.extend(top5)
        gs._log(f"  Creative Outburst: 5 damage + draw 1 from top 5")

    elif name == EXPLOSIVE_ENTRY and opponent:
        # Destroy artifact + put counter on creature
        artifacts = [c for c in opponent.zones.battlefield if c.has(Tag.ARTIFACT)]
        if artifacts:
            t = artifacts[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            critters = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)]
            if critters:
                target = max(critters, key=lambda c: safe_power(c))
                target.counters = getattr(target,'counters',0) + 1
            gs._log(f"  Explosive Entry: destroy {t.name} + +1/+1 counter")

    elif name == FORSAKE_WORLDLY and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if c.has(Tag.ARTIFACT) or c.has(Tag.ENCHANTMENT)]
        if targets:
            t = targets[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.exile.append(t)
            gs._log(f"  Forsake the Worldly: exile {t.name}")
        else:
            # Cycle for draw
            gs.zones.draw(1)
            gs._log(f"  Forsake the Worldly: cycle for draw")
