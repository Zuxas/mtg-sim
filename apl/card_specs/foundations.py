"""Foundations — Standard-legal reprints and staples

Cards (all reprints or near-reprints; simple effects):
Burst Lightning {R} - 2 damage; kicker {4} = 4 damage
Llanowar Elves {G} 1/1 - {T}: add {G}
Duress {B} - opponent reveals hand, exile a noncreature nonland card
Mossborn Hydra {2}{G} 0/0 - trample, enters with X +1/+1 counters
Opt {U} - scry 1, draw 1
Sleight of Hand {U} - look at top 2, put 1 in hand
Shock {R} - 2 damage to any target
Lightning Bolt {R} - 3 damage to any target
Counterspell {U}{U} - counter target spell
Rampant Growth {1}{G} - search for basic land, put into play tapped
Naturalize {1}{G} - destroy target artifact or enchantment
Murder {1}{B}{B} - destroy target creature
Giant Growth {G} - target creature +3/+3 until EOT

Spec: apl/card_specs/foundations.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power, safe_toughness

BURST_LIGHTNING = "Burst Lightning"
LLANOWAR_ELVES  = "Llanowar Elves"
DURESS          = "Duress"
MOSSBORN_HYDRA  = "Mossborn Hydra"
OPT             = "Opt"
SLEIGHT_OF_HAND = "Sleight of Hand"
SHOCK           = "Shock"
LIGHTNING_BOLT  = "Lightning Bolt"
COUNTERSPELL    = "Counterspell"
RAMPANT_GROWTH  = "Rampant Growth"
NATURALIZE      = "Naturalize"
MURDER          = "Murder"
GIANT_GROWTH    = "Giant Growth"

ALL_NAMES = {BURST_LIGHTNING, LLANOWAR_ELVES, DURESS, MOSSBORN_HYDRA,
             OPT, SLEIGHT_OF_HAND, SHOCK, LIGHTNING_BOLT, COUNTERSPELL,
             RAMPANT_GROWTH, NATURALIZE, MURDER, GIANT_GROWTH}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Foundations cards. Returns True if cast."""
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
    if name == BURST_LIGHTNING:
        gs.damage_dealt += 2
        gs._log(f"  Burst Lightning: 2 damage ({gs.damage_dealt} total)")

    elif name == LLANOWAR_ELVES:
        gs._log(f"  Llanowar Elves: 1/1, {T}: add {{G}}")

    elif name == DURESS and opponent:
        noncreatures = [c for c in opponent.zones.hand
                        if not c.is_land() and not c.has(Tag.CREATURE)]
        if noncreatures:
            t = max(noncreatures, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.hand.remove(t)
            opponent.zones.exile.append(t)
            gs._log(f"  Duress: exile {t.name} from opp hand")

    elif name == MOSSBORN_HYDRA:
        # X counters based on available mana
        x = max(0, gs.mana_pool.total() - 2)
        card.counters = getattr(card,'counters',0) + x
        card.power = str(x); card.toughness = str(x)
        gs._log(f"  Mossborn Hydra: enters as {x}/{x} trample")

    elif name == OPT:
        # Scry 1, draw 1
        if gs.zones.library:
            top = gs.zones.library[0]
            if top.is_land() or getattr(top,'cmc',0) <= 1:
                gs.zones.library.pop(0)
                gs.zones.library.append(top)  # put on bottom
        gs.zones.draw(1)
        gs._log(f"  Opt: scry 1, draw 1")

    elif name == SLEIGHT_OF_HAND:
        # Look at top 2, put 1 in hand
        if len(gs.zones.library) >= 2:
            top2 = gs.zones.library[:2]
            gs.zones.library = gs.zones.library[2:]
            best = max(top2, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.append(best)
            top2.remove(best)
            gs.zones.library = top2 + gs.zones.library
        gs._log(f"  Sleight of Hand: draw 1 from top 2")

    elif name == SHOCK:
        gs.damage_dealt += 2
        gs._log(f"  Shock: 2 damage ({gs.damage_dealt} total)")

    elif name == LIGHTNING_BOLT:
        gs.damage_dealt += 3
        gs._log(f"  Lightning Bolt: 3 damage ({gs.damage_dealt} total)")

    elif name == COUNTERSPELL and opponent:
        gs._log(f"  Counterspell: counter target spell")

    elif name == RAMPANT_GROWTH:
        plains = [c for c in gs.zones.library if c.is_land()]
        if plains:
            land = plains[0]
            gs.zones.library.remove(land)
            gs.zones.battlefield.append(land)
            land.tapped = True
            gs._log(f"  Rampant Growth: fetch {land.name} (tapped)")

    elif name == NATURALIZE and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if c.has(Tag.ARTIFACT) or c.has(Tag.ENCHANTMENT)]
        if targets:
            t = targets[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs._log(f"  Naturalize: destroy {t.name}")

    elif name == MURDER and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs._log(f"  Murder: destroy {t.name}")

    elif name == GIANT_GROWTH:
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            t.counters = getattr(t,'counters',0) + 3
            gs._log(f"  Giant Growth: {t.name} +3/+3")
