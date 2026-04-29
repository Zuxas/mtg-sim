"""Quandrix, the Proof — {4}{G}{U} 6/6 Legendary Creature — Elder Dragon

Oracle:
  Flying, trample
  Cascade (When you cast this spell, exile cards from the top of your
  library until you exile a nonland card that costs less. You may cast it
  without paying its mana cost. Put the exiled cards on the bottom in a
  random order.)
  Instant and sorcery spells you cast from your hand have cascade.

Decks: Standard Simic/cascade brews.

Key decisions:
- Cast T6 (4GU). 6/6 flying trample is a massive threat.
- Quandrix itself cascades into anything CMC < 6.
- After it resolves, EVERY instant/sorcery cast from hand cascades.
  e.g. Bolt (CMC 1) cascades into any CMC 0 spell (unlikely to hit).
  e.g. Counterspell (CMC 2) cascades into CMC < 2 = most cantrips.
  e.g. Lorehold miracle (higher CMC) cascades deep.
- Cascade hits lower CMV nonland card — can chain spells significantly.
- In Standard: free spell cascade from every Bolt/Opt/Counterspell.
- Combat: 6/6 flying trample wins in 3-4 turns against most decks.

Spec: apl/card_specs/quandrix.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Quandrix, the Proof"
CMC = 6  # {4}{G}{U}


def cast(gs, opponent=None) -> bool:
    """Cast Quandrix at T6+. Immediately grants cascade to all instants/sorceries.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Quandrix: 6/6 flying trample + cascade on all spells")
            return True
    return False


def is_active(gs) -> bool:
    """True if Quandrix is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield if not c.is_land())


def simulate_cascade(gs, spell_cmc: int, opponent=None) -> int:
    """Simulate cascade from casting a spell of given CMC.

    Finds the top library card with CMC < spell_cmc and casts it free.
    Returns the CMC of the cascaded spell (0 if nothing found).
    """
    if not is_active(gs):
        return 0

    # Look through library for first nonland card with CMC < spell_cmc
    cascade_target = None
    exile_pile = []
    for card in gs.zones.library[:]:
        if card.is_land():
            exile_pile.append(card)
            continue
        card_cmc = getattr(card, 'cmc', 0)
        if card_cmc < spell_cmc:
            cascade_target = card
            break
        exile_pile.append(card)

    if not cascade_target:
        # Put exile pile on bottom (simplified: just leave library as-is)
        return 0

    # Remove cascade target from library, cast it for free
    gs.zones.library.remove(cascade_target)
    # Put exiled cards on bottom
    for card in exile_pile:
        if card in gs.zones.library:
            gs.zones.library.remove(card)
    gs.zones.library.extend(exile_pile)

    # Cast the cascade target
    if cascade_target.has(Tag.CREATURE):
        gs.zones.battlefield.append(cascade_target)
        cascade_target.turn_entered = gs.turn
    else:
        gs.zones.graveyard.append(cascade_target)

    target_cmc = getattr(cascade_target, 'cmc', 0)
    gs._log(f"  Cascade ({spell_cmc} -> {cascade_target.name} CMC {target_cmc}): free cast")
    return target_cmc
