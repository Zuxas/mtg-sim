"""The Dawning Archaic — {10} 7/7 Legendary Creature — Avatar

Oracle:
  This spell costs {1} less to cast for each instant and sorcery card
  in your graveyard.
  Reach
  Whenever The Dawning Archaic attacks, you may cast target instant or
  sorcery card from your graveyard without paying its mana cost. If that
  spell would be put into your graveyard, exile it instead.

Decks: Standard spells/graveyard brews (Izzet Cauldron finisher).

Key decisions:
- Base cost {10}, reduced by 1 per instant/sorcery in GY.
  With 7 spells in GY: costs {3}. With 10: free.
  Standard goldfish: typically T5-6 with 4-6 spells in GY → costs 4-6.
- Reach: blocks flying threats while you build toward attack.
- Attack trigger: cast any instant/sorcery from GY for free.
  Priority for free cast: highest-value spell in GY (Magma Opus >> Bolt)
  After cast, goes to exile (can't be recurred again).
- Build-around: fill GY early with cantrips/removal to reduce cost fast.

Spec: apl/card_specs/the_dawning_archaic.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "The Dawning Archaic"
BASE_CMC = 10


def effective_cmc(gs) -> int:
    """Compute actual casting cost based on instants/sorceries in GY."""
    gy_spells = sum(1 for c in gs.zones.graveyard
                    if not c.is_land() and not c.has(Tag.CREATURE)
                    and not c.has(Tag.ENCHANTMENT) and not c.has(Tag.ARTIFACT))
    return max(0, BASE_CMC - gy_spells)


def cast(gs, opponent=None) -> bool:
    """Cast Dawning Archaic when effective cost <= available mana.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME:
            cost = effective_cmc(gs)
            if gs.mana_pool.total() >= cost:
                # Pay the reduced cost
                try:
                    gs.mana_pool.pay("{" + str(cost) + "}", cost)
                except Exception:
                    continue
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                gy_count = BASE_CMC - cost
                gs._log(f"  Dawning Archaic: 7/7 reach, cost {cost} "
                        f"(reduced {gy_count} by GY spells)")
                return True
    return False


def is_active(gs) -> bool:
    """True if The Dawning Archaic is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def fire_attack_trigger(gs, opponent=None) -> bool:
    """When Archaic attacks, cast the best instant/sorcery from GY for free.

    Returns True if a spell was cast.
    """
    if not is_active(gs):
        return False

    # Find best spell in GY (highest CMC = most value)
    gy_spells = [c for c in gs.zones.graveyard
                 if not c.is_land() and not c.has(Tag.CREATURE)]
    if not gy_spells:
        return False

    # Cast highest-CMC spell first (most value)
    target = max(gy_spells, key=lambda c: getattr(c, 'cmc', 0))
    gs.zones.graveyard.remove(target)

    # Cast for free — goes to exile after resolution
    gs.zones.exile.append(target)
    gs._log(f"  Dawning Archaic attack: free cast {target.name} from GY "
            f"(CMC {getattr(target, 'cmc', 0)}, exiled after)")

    # Apply spell effect (damage if burn)
    spell_cmc = getattr(target, 'cmc', 0)
    if spell_cmc >= 1 and opponent:
        gs.damage_dealt += spell_cmc  # rough approximation
    return True
