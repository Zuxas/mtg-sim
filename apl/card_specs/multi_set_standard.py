"""Multi-Set Standard Cards — Outlaws/Wilds/Murders/Lost Caverns/etc.

Cards from smaller Standard-legal sets grouped together:

Outlaws of Thunder Junction:
- Slickshot Show-Off {1}{R} 1/2 - flying haste, +2/+0 per noncreature spell
- Spyglass Siren {U} 1/1 - flying, ETB create Map token
- Three Steps Ahead {U} - Spree: counter/copy/draw
- Kaervek the Punisher {1}{B}{B} 3/3 - crime: exile black from GY to hand
- Deadly Cover-Up {3}{B}{B} - destroy all, collect evidence = exile all copies
- Tishana's Tidebinder {2}{G} - counter activated ability, draw
- Kellan, the Kid {G}{W}{U} 3/3 - flying lifelink, gains on cast from non-hand
- Omenpath Journey {3}{G} - search for 5 basic lands

Wilds of Eldraine:
- Goddric, Cloaked Reveler {1}{R}{R} 3/3 - haste, becomes dragon on celebration
- Moonshaker Cavalry {5}{W}{W}{W} 6/6 - flying, ETB all creatures get flying+X
- Up the Beanstalk {1}{G} - enchant: ETB and CMC5+ spells = draw

Murders at Karlov Manor:
- Steamcore Scholar {2}{U} 2/2 - flying vig, ETB draw 2 discard 2
- Novice Inspector {W} 1/2 - ETB investigate (create Clue)
- Massacre Girl {3}{B}{B} 4/4 - menace, ETB -1/-1 all others, death triggers
- Judith, Carnage Connoisseur {3}{B}{R} 3/4 - spells gain menace or kill token

Lost Caverns of Ixalan:
- Get Lost {1}{W} - destroy creature/enchant/PW, opp gets 2 Map tokens
- Malcolm, Alluring Scoundrel {1}{U} 2/1 - flash fly, damage = chorus counter

Spec: apl/card_specs/multi_set_standard.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness
from engine.keywords import KWTag

# Outlaws of Thunder Junction
SLICKSHOT         = "Slickshot Show-Off"
SPYGLASS_SIREN    = "Spyglass Siren"
THREE_STEPS_AHEAD = "Three Steps Ahead"
KAERVEK           = "Kaervek, the Punisher"
DEADLY_COVER_UP   = "Deadly Cover-Up"
TISHANAS_BINDER   = "Tishana's Tidebinder"
KELLAN            = "Kellan, the Kid"
OMENPATH_JOURNEY  = "Omenpath Journey"

# Wilds of Eldraine
GODDRIC           = "Goddric, Cloaked Reveler"
MOONSHAKER        = "Moonshaker Cavalry"
UP_THE_BEANSTALK  = "Up the Beanstalk"

# Murders at Karlov Manor
STEAMCORE_SCHOLAR = "Steamcore Scholar"
NOVICE_INSPECTOR  = "Novice Inspector"
MASSACRE_GIRL     = "Massacre Girl"
JUDITH            = "Judith, Carnage Connoisseur"

# Lost Caverns of Ixalan
GET_LOST          = "Get Lost"
MALCOLM           = "Malcolm, Alluring Scoundrel"


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def slickshot_spell_trigger(gs) -> None:
    """Slickshot Show-Off: +2/+0 whenever you cast a noncreature spell."""
    for c in gs.zones.battlefield:
        if c.name == SLICKSHOT:
            c.counters = getattr(c,'counters',0) + 2
            gs._log(f"  Slickshot: +2/+0 trigger")


def _on_resolve(gs, name: str, card, opponent):
    if name == SLICKSHOT:
        gs._log(f"  Slickshot Show-Off: 1/2 flying haste, +2/+0 per noncreature spell")

    elif name == SPYGLASS_SIREN:
        gs._log(f"  Spyglass Siren: 1/1 flying, ETB create Map token")

    elif name == THREE_STEPS_AHEAD:
        # Spree: pay extra for each effect chosen
        # Default: counter a spell (cheapest option)
        if opponent:
            gs._log(f"  Three Steps Ahead: counter target spell (Spree)")

    elif name == KAERVEK:
        gs._log(f"  Kaervek: 3/3, on crime: exile black card from GY to hand")

    elif name == DEADLY_COVER_UP and opponent:
        # Destroy all creatures
        for owner in (gs, opponent):
            killed = [c for c in list(owner.zones.battlefield)
                      if c.has(Tag.CREATURE) and not c.is_land()]
            for c in killed:
                owner.zones.battlefield.remove(c)
                owner.zones.graveyard.append(c)
        gs._log(f"  Deadly Cover-Up: destroy all creatures")

    elif name == TISHANAS_BINDER and opponent:
        gs.zones.draw(1)
        gs._log(f"  Tishana's Tidebinder: counter activated ability + draw 1")

    elif name == KELLAN:
        gs._log(f"  Kellan: 3/3 flying lifelink, gains on cast from non-hand")

    elif name == OMENPATH_JOURNEY:
        # Search for 5 basic lands
        lands_found = []
        for c in list(gs.zones.library):
            if c.is_land() and len(lands_found) < 5:
                lands_found.append(c)
                gs.zones.library.remove(c)
        for land in lands_found:
            gs.zones.hand.append(land)
        gs._log(f"  Omenpath Journey: tutor {len(lands_found)} basic lands to hand")

    elif name == GODDRIC:
        gs._log(f"  Goddric: 3/3 haste, transforms into Dragon if 2+ nonland permanents entered this turn")

    elif name == MOONSHAKER and opponent is not None:
        # All creatures gain flying + +X/+X where X = creature count
        x = sum(1 for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land())
        for cr in gs.zones.battlefield:
            if cr.has(Tag.CREATURE) and not cr.is_land():
                cr.tags.add(KWTag.FLYING)
                cr.counters = getattr(cr,'counters',0) + x
        gs._log(f"  Moonshaker Cavalry: all creatures fly + +{x}/+{x}")

    elif name == UP_THE_BEANSTALK:
        gs.zones.draw(1)
        gs._log(f"  Up the Beanstalk: ETB draw 1")

    elif name == STEAMCORE_SCHOLAR:
        gs.zones.draw(2)
        # Discard 2
        for _ in range(2):
            if gs.zones.hand:
                worst = min(gs.zones.hand, key=lambda c: getattr(c,'cmc',0))
                gs.zones.hand.remove(worst)
                gs.zones.graveyard.append(worst)
        gs._log(f"  Steamcore Scholar: draw 2, discard 2")

    elif name == NOVICE_INSPECTOR:
        # Investigate: create Clue token
        clue = Card("Clue Token", "{0}", 0, "Token Artifact — Clue",
                    oracle_text="{2}, Sacrifice this artifact: Draw a card.")
        clue.power = "0"; clue.toughness = "0"
        clue.turn_entered = gs.turn
        gs.zones.battlefield.append(clue)
        gs._log(f"  Novice Inspector: investigate (create Clue)")

    elif name == MASSACRE_GIRL and opponent:
        # -1/-1 to each other creature; death triggers
        for owner in (gs, opponent):
            for cr in list(owner.zones.battlefield):
                if cr.has(Tag.CREATURE) and not cr.is_land() and cr is not card:
                    cr.counters = getattr(cr,'counters',0) - 1
                    if safe_toughness(cr) + getattr(cr,'counters',0) <= 0:
                        owner.zones.battlefield.remove(cr)
                        owner.zones.graveyard.append(cr)
        gs._log(f"  Massacre Girl: -1/-1 to all other creatures")

    elif name == JUDITH:
        gs._log(f"  Judith: 3/4, spells gain menace or create 1/1 on cast")

    elif name == GET_LOST and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if not c.is_land() and (c.has(Tag.CREATURE)
                   or c.has(Tag.ENCHANTMENT) or 'Planeswalker' in (getattr(c,'type_line','') or ''))]
        if targets:
            t = max(targets, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.battlefield.remove(t)
            opponent.zones.exile.append(t)
            gs._log(f"  Get Lost: destroy {t.name} (opp gets 2 Map tokens)")

    elif name == MALCOLM:
        gs._log(f"  Malcolm: 2/1 flash flying, chorus counters on damage")
