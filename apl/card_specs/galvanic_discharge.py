"""Galvanic Discharge — `{R}` instant: get {E}{E}{E}, then pay {E} for damage.

Oracle:
  You get {E}{E}{E} (three energy counters). Then you may pay any amount of
  {E}. Galvanic Discharge deals that much damage to any target.

Decks using this spec: Boros Energy (cast purely for the +3 net energy).

Reference impl: apl/boros_energy.py:GALVANIC (line 47) + the "7. Galvanic
                Discharge" block (~line 366) where every copy is cast for +3
                energy each, 0 damage to an own creature.

Two modes:
  - cast_for_energy: +3 net energy, 0 damage. Goldfish-SAFE (energy accrues
    regardless of opponent). This is the boros line's behavior.
  - cast_for_damage: spend energy to deal damage to an opponent target.
    Goldfish-DEAD: early-returns False when opponent is None.

Energy bookkeeping uses gs.energy (the exact field boros uses) so a later
Phase B swap into boros_energy.py is mechanical.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Galvanic Discharge"
CAST_CMC = 1   # {R}


def cast_for_energy(gs, opponent=None) -> bool:
    """Cast one Galvanic Discharge for +3 net energy, 0 damage.

    Requires a creature on the battlefield (the boros line targets an own
    creature for 0 damage). Mirrors boros_energy.py:366-373 exactly:
    +3 energy, then cast_spell. Goldfish-safe.

    Returns True if a copy was cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            creatures = gs.zones.creatures_on_battlefield()
            if creatures:
                gs.energy += 3
                gs.cast_spell(c)
                gs._log(f"  Galvanic: +3 energy ({gs.energy}), 0 dmg to own creature")
                return True
    return False


def cast_for_damage(gs, opponent=None, amount=None) -> bool:
    """Cast one Galvanic Discharge to deal `amount` damage to the opponent.

    Net energy = 3 - amount spent. `amount` defaults to 3 (all the energy this
    spell produces), clamped to [0, 3]. Damage goes to the opponent's face
    (simplest target; APLs may pre-pick a creature target before calling).

    Goldfish-DEAD: returns False when opponent is None (no legal target that
    matters for the goldfish clock).

    Returns True if a copy was cast.
    """
    if opponent is None:
        return False  # goldfish-skip
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.energy += 3
            dmg = 3 if amount is None else max(0, min(3, amount))
            gs.energy -= dmg
            gs.cast_spell(c)
            opponent.life -= dmg
            gs._log(f"  Galvanic: {dmg} dmg to opp (energy: {gs.energy})")
            return True
    return False
