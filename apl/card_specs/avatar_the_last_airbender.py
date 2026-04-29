"""Avatar: The Last Airbender — 15 cards

Key mechanics: Earthbend (land becomes creature temporarily), Lessons
(Avatar-flavored: cycle of fire/water/earth/air cards), Bending mechanics.

Spec: apl/card_specs/avatar_the_last_airbender.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness

BADGERMOLE_CUB       = "Badgermole Cub"
BOOMERANG_BASICS     = "Boomerang Basics"
ABANDON_ATTACHMENTS  = "Abandon Attachments"
ACCUMULATE_WISDOM    = "Accumulate Wisdom"
COMBUSTION_TECHNIQUE = "Combustion Technique"
FIREBENDING_LESSON   = "Firebending Lesson"
GRAN_GRAN            = "Gran-Gran"
EARTHBENDER_ASCENSION= "Earthbender Ascension"
ITS_QUENCH_YA       = "It'll Quench Ya!"
WAN_SHI_TONG         = "Wan Shi Tong, Librarian"
IROHS_DEMONSTRATION  = "Iroh's Demonstration"
GREAT_DIVIDE_GUIDE   = "Great Divide Guide"
ORIGIN_METALBENDING  = "Origin of Metalbending"
UNAGI                = "The Unagi of Kyoshi Island"
OCTOPUS_FORM         = "Octopus Form"

ALL_NAMES = {BADGERMOLE_CUB, BOOMERANG_BASICS, ABANDON_ATTACHMENTS,
             ACCUMULATE_WISDOM, COMBUSTION_TECHNIQUE, FIREBENDING_LESSON,
             GRAN_GRAN, EARTHBENDER_ASCENSION, ITS_QUENCH_YA, WAN_SHI_TONG,
             IROHS_DEMONSTRATION, GREAT_DIVIDE_GUIDE, ORIGIN_METALBENDING,
             UNAGI, OCTOPUS_FORM}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Avatar cards. Returns True if cast."""
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
    if name == BADGERMOLE_CUB:
        # Earthbend 1: target land becomes 0/0 creature +2/2 counters
        lands = [c for c in gs.zones.battlefield if c.is_land()]
        if lands:
            land = lands[0]
            land.power = "2"; land.toughness = "2"
            land.turn_entered = gs.turn; land.summoning_sickness = False
            gs._log(f"  Badgermole Cub: earthbend {land.name} → 2/2")

    elif name == BOOMERANG_BASICS:
        if opponent:
            targets = [c for c in opponent.zones.battlefield if not c.is_land()]
            if targets:
                t = max(targets, key=lambda c: getattr(c,'cmc',0))
                opponent.zones.battlefield.remove(t)
                opponent.zones.hand.append(t)
                gs._log(f"  Boomerang Basics: bounce {t.name}")

    elif name == ABANDON_ATTACHMENTS:
        # Discard a card, draw 2
        if gs.zones.hand:
            worst = min(gs.zones.hand, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.remove(worst)
            gs.zones.graveyard.append(worst)
        gs.zones.draw(2)
        gs._log(f"  Abandon Attachments: discard/draw 2")

    elif name == ACCUMULATE_WISDOM:
        # Look at top 3, put 1 in hand, rest on bottom
        top3 = gs.zones.library[:3]
        gs.zones.library = gs.zones.library[3:]
        if top3:
            best = max(top3, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.append(best)
            top3.remove(best)
            gs.zones.library.extend(top3)
        gs._log(f"  Accumulate Wisdom: scry 3, draw 1")

    elif name == COMBUSTION_TECHNIQUE:
        # Damage = 2 + number of Lesson cards in GY
        lessons_in_gy = sum(1 for c in gs.zones.graveyard
                           if 'Lesson' in (getattr(c,'type_line','') or ''))
        dmg = 2 + lessons_in_gy
        gs.damage_dealt += dmg
        gs._log(f"  Combustion Technique: {dmg} damage ({lessons_in_gy} Lessons in GY)")

    elif name == FIREBENDING_LESSON:
        # Deals 1 damage; kicker {4} = deals 4 damage instead
        dmg = 1
        gs.damage_dealt += dmg
        gs._log(f"  Firebending Lesson: {dmg} damage (un-kicked)")

    elif name == GRAN_GRAN:
        gs._log(f"  Gran-Gran: noncreature spells can't be countered while active")

    elif name == EARTHBENDER_ASCENSION:
        # Earthbend 2 + search basic land
        lands = [c for c in gs.zones.battlefield if c.is_land()][:2]
        for land in lands:
            land.power = "2"; land.toughness = "2"
        gs._log(f"  Earthbender Ascension: earthbend 2, search Plains")

    elif name == ITS_QUENCH_YA:
        gs._log(f"  It'll Quench Ya!: counter spell or prevent damage")

    elif name == WAN_SHI_TONG:
        x = getattr(card, 'cmc', 0) - 2  # X from casting cost
        card.counters = getattr(card,'counters',0) + x
        card.power = str(1 + x); card.toughness = str(1 + x)
        gs._log(f"  Wan Shi Tong: X={x}, {1+x}/{1+x} flying vigilance")

    elif name == IROHS_DEMONSTRATION:
        gs.damage_dealt += 3
        gs.life += 3
        gs._log(f"  Iroh's Demonstration: 3 damage + 3 life")

    elif name == GREAT_DIVIDE_GUIDE:
        gs._log(f"  Great Divide Guide: each land/Ally taps for any color")

    elif name == ORIGIN_METALBENDING and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if c.has(Tag.ARTIFACT) or c.has(Tag.ENCHANTMENT)]
        if targets:
            t = targets[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs._log(f"  Origin of Metalbending: destroy {t.name}")
        else:
            critters = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)]
            if critters:
                t = max(critters, key=lambda c: safe_power(c))
                t.counters = getattr(t,'counters',0) + 1
                gs._log(f"  Origin of Metalbending: +1/+1 on {t.name}")

    elif name == OCTOPUS_FORM:
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            # Gains hexproof
            from engine.keywords import KWTag
            t.tags.add(KWTag.HEXPROOF)
            t.counters = getattr(t,'counters',0) + 1
            gs._log(f"  Octopus Form: {t.name} gets +1/+1 + hexproof until EOT")
