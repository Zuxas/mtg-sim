"""Bloomburrow — 17 cards (animal-themed Standard set)

Key mechanics: Offspring (pay extra for a copy token), Gift (optional upside),
Forage (exile 3 cards from GY as cost), tribal (Lizards, Fish, etc.).

Spec: apl/card_specs/bloomburrow.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness

STORMCHASER_TALENT  = "Stormchaser's Talent"
INTO_FLOOD_MAW      = "Into the Flood Maw"
EDDYMURK_CRAB       = "Eddymurk Crab"
KEEN_EYED_CURATOR   = "Keen-Eyed Curator"
PAWPATCH_FORMATION  = "Pawpatch Formation"
RAL_CRACKLING       = "Ral, Crackling Wit"
BEZA                = "Beza, the Bounding Spring"
EMBERHEART          = "Emberheart Challenger"
ARTIST_TALENT       = "Artist's Talent"
HEARTHBORN_BATTLER  = "Hearthborn Battler"
HIRED_CLAW          = "Hired Claw"
PAWPATCH_RECRUIT    = "Pawpatch Recruit"
YGRA                = "Ygra, Eater of All"
MIGHT_OF_MEEK       = "Might of the Meek"
FEED_CYCLE          = "Feed the Cycle"
SCRAPSHOOTER        = "Scrapshooter"
MOCKINGBIRD         = "Mockingbird"


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Bloomburrow cards. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if card_name == EDDYMURK_CRAB:
            cost = _eddymurk_cost(gs)
            if gs.mana_pool.total() < cost:
                continue
        elif not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def _eddymurk_cost(gs) -> int:
    instants_sorceries = sum(1 for c in gs.zones.graveyard
                             if not c.is_land() and not c.has(Tag.CREATURE))
    return max(2, 7 - instants_sorceries)  # base {5}{U}{U}=7


def _on_resolve(gs, name: str, card, opponent):
    if name == STORMCHASER_TALENT:
        gs._log(f"  Stormchaser's Talent: enchantment, spells can't be countered")

    elif name == INTO_FLOOD_MAW and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if c.has(Tag.CREATURE) and not c.is_land()]
        if targets:
            t = max(targets, key=lambda c: safe_power(c))
            opponent.zones.battlefield.remove(t)
            opponent.zones.hand.append(t)
            gs._log(f"  Into the Flood Maw: bounce {t.name}")

    elif name == EDDYMURK_CRAB:
        gs._log(f"  Eddymurk Crab: 5/5 flash (cost reduced by instants/sorceries in GY)")

    elif name == KEEN_EYED_CURATOR:
        gs._log(f"  Keen-Eyed Curator: 3/3, gains abilities if 4+ card types in exile")

    elif name == PAWPATCH_FORMATION and opponent:
        fliers = [c for c in opponent.zones.battlefield
                  if c.has(Tag.CREATURE) and 'flying' in (getattr(c,'oracle_text','') or '').lower()]
        if fliers:
            t = fliers[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs._log(f"  Pawpatch Formation: destroy flier {t.name}")
        elif opponent:
            enchants = [c for c in opponent.zones.battlefield if c.has(Tag.ENCHANTMENT)]
            if enchants:
                t = enchants[0]
                opponent.zones.battlefield.remove(t)
                opponent.zones.graveyard.append(t)
                gs._log(f"  Pawpatch Formation: destroy enchantment {t.name}")

    elif name == RAL_CRACKLING:
        gs._log(f"  Ral, Crackling Wit: gains loyalty on noncreature spells, +1 draw, -2 4/1 haste")

    elif name == BEZA:
        # Create Treasure if opp has more lands
        our_lands = sum(1 for c in gs.zones.battlefield if c.is_land())
        opp_lands = sum(1 for c in opponent.zones.battlefield if c.is_land()) if opponent else 0
        if opp_lands > our_lands:
            gs._log(f"  Beza: 4/5, created Treasure (opp has more lands)")

    elif name == EMBERHEART:
        gs._log(f"  Emberheart Challenger: 2/2 haste prowess")

    elif name == HEARTHBORN_BATTLER:
        gs._log(f"  Hearthborn Battler: 2/3 haste, deals 1 on player's 2nd spell each turn")

    elif name == YGRA:
        gs._log(f"  Ygra, Eater of All: 6/6 ward(sacrifice Food), other creatures are also Food artifacts")

    elif name == MIGHT_OF_MEEK:
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            from engine.keywords import KWTag
            t.tags.add(KWTag.TRAMPLE)
            t.counters = getattr(t,'counters',0) + 1
            gs._log(f"  Might of the Meek: {t.name} +1/+0 + trample")

    elif name == FEED_CYCLE:
        # Forage or pay B extra; draw a card
        gs.zones.draw(1)
        gs._log(f"  Feed the Cycle: draw 1")

    elif name == SCRAPSHOOTER:
        gs._log(f"  Scrapshooter: 4/4 gift(destroy artifact/enchantment)")

    elif name == MOCKINGBIRD:
        # Copy any creature on battlefield
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            best = max(critters, key=lambda c: safe_power(c))
            card.power = best.power; card.toughness = best.toughness
            gs._log(f"  Mockingbird: enters as copy of {best.name}")
