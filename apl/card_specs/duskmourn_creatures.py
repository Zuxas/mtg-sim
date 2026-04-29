"""Duskmourn Creatures — 9 cards

Floodpits Drowner {1}{U} 2/1 Flash Vigilance
  When ETB: tap target creature opp controls, put a stun counter on it.

Fear of Missing Out {1}{R} 2/3
  ETB: discard a card, draw a card.
  Delirium: whenever attacks, target creature gets +1/+1 until EOT.

Enduring Curiosity {2}{U}{U} 4/3 Flash
  Whenever a creature you control deals combat damage to a player, draw a card.
  When EOT, if you drew 2+ this turn, return Enduring Curiosity to hand.

Enduring Innocence {1}{W}{W} 2/1 Lifelink
  Whenever other creatures with power 2 or less ETB under your control, draw.
  When EOT if you drew 2+, return Enduring Innocence to hand.

Razorkin Needlehead {R}{R} 2/2
  First strike during your turn.
  Whenever an opp draws a card, this creature deals 1 damage to them.

Kaito, Bane of Nightmares {2}{U}{B} Legendary Creature
  Ninjutsu {1}{U}{B}: Return unblocked attacker to hand, put Kaito in.
  When Kaito deals combat damage: draw a card, create 1/1 Ninja token.

Splitskin Doll {1}{W} 2/1
  ETB: draw a card. Then discard unless you control another creature with skin.

Abhorrent Oculus {2}{U} 5/5
  Additional cost: exile 6 cards from GY.
  Flying. Beginning of upkeep: draw 2, create 2/2 blue Beholder token.

Doomsday Excruciator {B}{B}{B}{B}{B}{B} 6/6
  Flying. When cast: each player exiles all but bottom 6 cards of library.
  Each turn, each player may cast a spell from exile.

Decks: Various Standard archetypes.
Spec: apl/card_specs/duskmourn_creatures.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness

FLOODPITS_DROWNER    = "Floodpits Drowner"
FEAR_MISSING_OUT     = "Fear of Missing Out"
ENDURING_CURIOSITY   = "Enduring Curiosity"
ENDURING_INNOCENCE   = "Enduring Innocence"
RAZORKIN_NEEDLEHEAD  = "Razorkin Needlehead"
KAITO_BANE           = "Kaito, Bane of Nightmares"
SPLITSKIN_DOLL       = "Splitskin Doll"
ABHORRENT_OCULUS     = "Abhorrent Oculus"
DOOMSDAY_EXCRUCIATOR = "Doomsday Excruciator"


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Duskmourn creature cards. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if card_name == ABHORRENT_OCULUS:
            if not _can_pay_oculus_cost(gs):
                continue
            _pay_oculus_cost(gs)
            gs.zones.hand.remove(c)
            gs.zones.battlefield.append(c)
            c.turn_entered = gs.turn; c.summoning_sickness = True
            gs._log(f"  Abhorrent Oculus: 5/5 flying (exiled 6 from GY)")
            return True
        if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            _on_etb(gs, card_name, c, opponent)
            return True
    return False


def _can_pay_oculus_cost(gs) -> bool:
    return (gs.mana_pool.total() >= 3 and
            len([x for x in gs.zones.graveyard if not x.is_land()]) >= 6)


def _pay_oculus_cost(gs):
    exiled = 0
    for card in list(gs.zones.graveyard):
        if not card.is_land() and exiled < 6:
            gs.zones.graveyard.remove(card)
            gs.zones.exile.append(card)
            exiled += 1
    try:
        gs.mana_pool.pay("{2}{U}", 3)
    except Exception:
        pass


def _on_etb(gs, name: str, card, opponent):
    """Fire ETB effects for Duskmourn creatures."""
    if name == FLOODPITS_DROWNER and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            t.tapped = True
            t.stun_counter = True
            gs._log(f"  Floodpits Drowner: tap+stun {t.name}")

    elif name == FEAR_MISSING_OUT:
        # Discard then draw
        if gs.zones.hand:
            worst = min(gs.zones.hand, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.remove(worst)
            gs.zones.graveyard.append(worst)
        gs.zones.draw(1)
        gs._log(f"  Fear of Missing Out: discard/draw")

    elif name == SPLITSKIN_DOLL:
        gs.zones.draw(1)
        # Check if we have another creature; if not, discard
        others = [c for c in gs.zones.battlefield
                  if c.has(Tag.CREATURE) and not c.is_land() and c is not card]
        if not others and gs.zones.hand:
            worst = min(gs.zones.hand, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.remove(worst)
            gs.zones.graveyard.append(worst)
        gs._log(f"  Splitskin Doll: draw 1")

    elif name == DOOMSDAY_EXCRUCIATOR and opponent:
        # Each player exiles all but bottom 6
        for player in (gs, opponent):
            keep = list(player.zones.library[-6:])
            exile = list(player.zones.library[:-6])
            player.zones.library = keep
            for card in exile:
                player.zones.exile.append(card)
        gs._log(f"  Doomsday Excruciator: both players exile down to 6 cards in library")


def abhorrent_oculus_upkeep(gs) -> None:
    """Beginning of upkeep: draw 2, create 2/2 Beholder if Oculus is active."""
    if not any(c.name == ABHORRENT_OCULUS for c in gs.zones.battlefield):
        return
    gs.zones.draw(2)
    tok = Card("Beholder Token", "{0}", 2, "Token Creature — Beholder",
               oracle_text="Flying.")
    tok.power = "2"; tok.toughness = "2"
    tok.turn_entered = gs.turn; tok.summoning_sickness = True
    gs.zones.battlefield.append(tok)
    gs._log(f"  Abhorrent Oculus upkeep: draw 2 + 2/2 Beholder")
