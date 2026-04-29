"""Witherbloom, the Balancer — {6}{B}{G} 5/5 Legendary Creature — Elder Dragon

Oracle:
  Affinity for creatures (This spell costs {1} less to cast for each
  creature you control.)
  Flying, deathtouch
  Instant and sorcery spells you cast have "When this spell resolves,
  you may sacrifice a creature. If you do, return target creature card
  from your graveyard to the battlefield."

Decks: Sultai Reanimator, Golgari midrange, any creature-heavy deck.

Key decisions:
- Base cost {6}{B}{G} = 8 mana, reduced by 1 per creature.
  With 4 creatures: costs {4}{B}{G} (4 mana cheaper).
  With 6 creatures: costs {2}{B}{G} or less.
- 5/5 flying deathtouch = excellent blocker AND attacker.
- Spell reanimation: every instant/sorcery has "sacrifice a creature to
  reanimate from GY." Chain with cheap spells to loop GY creatures.
- Best targets to reanimate: high-CMC creatures that died.
- Deathtouch + flying: trades with any creature, blocks all fliers.
- Affinity means in creature-heavy builds (tokens etc.) it approaches free.

Spec: apl/card_specs/witherbloom.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

NAME = "Witherbloom, the Balancer"
BASE_CMC = 8  # {6}{B}{G}


def effective_cmc(gs) -> int:
    """Compute actual cost: base 8 minus 1 per creature controlled."""
    creatures = sum(1 for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land())
    return max(2, BASE_CMC - creatures)  # floor at 2 ({B}{G})


def cast(gs, opponent=None) -> bool:
    """Cast Witherbloom when effective cost <= available mana.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME:
            cost = effective_cmc(gs)
            if gs.mana_pool.total() >= cost:
                try:
                    gs.mana_pool.pay("{" + str(cost) + "}", cost)
                except Exception:
                    continue
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                c.summoning_sickness = True
                discount = BASE_CMC - cost
                gs._log(f"  Witherbloom: 5/5 flying deathtouch, "
                        f"cost {cost} (affinity -{discount}), spells reanimate")
                return True
    return False


def is_active(gs) -> bool:
    """True if Witherbloom is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def apply_spell_reanimation(gs, opponent=None) -> bool:
    """When any instant/sorcery resolves with Witherbloom active,
    optionally sacrifice a creature to reanimate from GY.

    Returns True if reanimation happened.
    """
    if not is_active(gs):
        return False

    # Find best target in GY (highest CMC creature)
    gy_creatures = [c for c in gs.zones.graveyard if c.has(Tag.CREATURE)]
    if not gy_creatures:
        return False

    # Find a small creature to sacrifice (least valuable)
    sacrifice_pool = [c for c in gs.zones.battlefield
                      if c.has(Tag.CREATURE) and not c.is_land()
                      and c.name != NAME]
    if not sacrifice_pool:
        return False

    sac_target = min(sacrifice_pool, key=lambda c: safe_power(c))
    reanimate_target = max(gy_creatures, key=lambda c: getattr(c, 'cmc', 0))

    # Only reanimate if target is worth more than sacrificed creature
    if getattr(reanimate_target, 'cmc', 0) <= getattr(sac_target, 'cmc', 0):
        return False

    gs.zones.battlefield.remove(sac_target)
    gs.zones.graveyard.append(sac_target)
    gs.zones.graveyard.remove(reanimate_target)
    gs.zones.battlefield.append(reanimate_target)
    reanimate_target.turn_entered = gs.turn
    reanimate_target.summoning_sickness = True
    gs._log(f"  Witherbloom: sac {sac_target.name}, reanimate "
            f"{reanimate_target.name} from GY")
    return True
