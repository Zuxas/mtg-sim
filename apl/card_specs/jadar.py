"""Jadar, Ghoulcaller of Nephalia — {1}{B} 1/1 Legendary Creature — Human Wizard

Oracle:
  At the beginning of your end step, if you control no creatures with
  decayed, create a 2/2 black Zombie creature token with decayed.
  (A creature with decayed can't block. When it attacks, sacrifice it at
  end of combat.)

Decks: Dimir midrange, Sultai Reanimator, any black-based sacrifice.

Key decisions:
- Cast T2 (1B). 1/1 body, but generates a 2/2 token each end step.
- Decayed Zombie: can't block, sacrificed after attacking.
  Use for: attacking for 2, casualty fodder for Silverquill, sac for
  Witherbloom reanimation, death triggers.
- Each end step generates one if you have none. So: attack → sacrifice →
  end step → new one. Continuous engine.
- With Silverquill: each instant/sorcery can sac the decayed Zombie for
  casualty (gets a free copy of the spell).
- With Witherbloom: sac Zombie mid-cast to reanimate a better creature.
- Value scales with sac outlets; standalone it's 2 free damage per turn.

Spec: apl/card_specs/jadar.py
"""
from __future__ import annotations
from data.card import Card, Tag

NAME = "Jadar, Ghoulcaller of Nephalia"
CMC = 2  # {1}{B}
ZOMBIE_POWER = 2
ZOMBIE_TOUGHNESS = 2


def cast(gs, opponent=None) -> bool:
    """Cast Jadar T2. Starts zombie token engine.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Jadar: 1/1, end step creates 2/2 decayed Zombie if none present")
            return True
    return False


def is_active(gs) -> bool:
    """True if Jadar is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def has_decayed_zombie(gs) -> bool:
    """Check if we control any creature with decayed."""
    return any('decayed' in (getattr(c, 'oracle_text', '') or '').lower()
               for c in gs.zones.battlefield if c.has(Tag.CREATURE))


def fire_end_step(gs) -> bool:
    """At end step, create 2/2 decayed Zombie if we control none.

    Returns True if token was created.
    """
    if not is_active(gs):
        return False
    if has_decayed_zombie(gs):
        return False  # already have one

    token = Card("Decayed Zombie Token", "{0}", ZOMBIE_POWER,
                 "Token Creature — Zombie",
                 oracle_text="Decayed. (A creature with decayed can't block. "
                             "When it attacks, sacrifice it at end of combat.)")
    token.power = str(ZOMBIE_POWER)
    token.toughness = str(ZOMBIE_TOUGHNESS)
    token.turn_entered = gs.turn
    token.summoning_sickness = True
    gs.zones.battlefield.append(token)
    gs._log(f"  Jadar end step: create 2/2 decayed Zombie token")
    return True


def sacrifice_zombie_for_casualty(gs) -> bool:
    """Sacrifice the decayed Zombie as casualty fodder.

    Returns True if a zombie was sacrificed.
    """
    zombie = next((c for c in gs.zones.battlefield
                   if c.has(Tag.CREATURE)
                   and 'Zombie' in (getattr(c, 'type_line', '') or '')
                   and 'decayed' in (getattr(c, 'oracle_text', '') or '').lower()), None)
    if not zombie:
        return False
    gs.zones.battlefield.remove(zombie)
    gs.zones.graveyard.append(zombie)
    gs._log(f"  Sacrifice decayed Zombie for casualty")
    return True
