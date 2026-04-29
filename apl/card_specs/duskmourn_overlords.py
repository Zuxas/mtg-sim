"""Duskmourn Overlords — Impending Cycle (5 cards)

All five share the Impending mechanic:
  Cast for reduced cost, enters with N time counters, NOT a creature.
  At start of your upkeep, remove a counter. When last removed, becomes creature.
  Can also be hard-cast at full cost as a creature immediately.

Cards:
- Overlord of the Hauntwoods  {3}{G}{G} 6/5  Impending 4 {1}{G}{G}
  When becomes creature: create 4/4 green Forest Dryad token for each time counter removed.
  Reach. Creatures entering tokens have trample.

- Overlord of the Boilerbilges {4}{R}{R} 5/5  Impending 4 {2}{R}{R}
  When becomes creature: deals damage = time counters removed to each opponent.
  Haste. All creatures ETB this turn have haste.

- Overlord of the Balemurk   {3}{B}{B} 5/5  Impending 5 {1}{B}
  When becomes creature: each opp mills 5, you draw 5.
  Flying. Each creature ETB this turn has flying.

- Overlord of the Mistmoors  {5}{W}{W} 6/6  Impending 4 {2}{W}{W}
  When becomes creature: create 2/2 Spirit token for each time counter.
  Flying. Spirits ETB this turn have flying.

- Overlord of the Floodpits  {3}{U}{U} 5/3  Impending 4 {1}{U}{U}
  When becomes creature: counter up to N target spells (N = time counters).
  Flying. Spells opponents cast cost more.

Decks: Duskmourn-based control, ramp, midrange.

Spec: apl/card_specs/duskmourn_overlords.py
"""
from __future__ import annotations
from data.card import Card, Tag

# Names
HAUNTWOODS  = "Overlord of the Hauntwoods"
BOILERBILGES= "Overlord of the Boilerbilges"
BALEMURK    = "Overlord of the Balemurk"
MISTMOORS   = "Overlord of the Mistmoors"
FLOODPITS   = "Overlord of the Floodpits"

ALL_OVERLORDS = {HAUNTWOODS, BOILERBILGES, BALEMURK, MISTMOORS, FLOODPITS}

# (name, full_cmc, impending_cmc, impending_counters, power, toughness)
OVERLORD_DATA = {
    HAUNTWOODS:   (5, 3, 4, 6, 5),
    BOILERBILGES: (6, 4, 4, 5, 5),
    BALEMURK:     (5, 2, 5, 5, 5),
    MISTMOORS:    (7, 4, 4, 6, 6),
    FLOODPITS:    (5, 3, 4, 5, 3),
}


def cast_impending(gs, overlord_name: str, opponent=None) -> bool:
    """Cast an Overlord via its Impending cost (enters with time counters).

    More mana-efficient. Creature ability fires when all counters removed.
    Returns True if cast.
    """
    if overlord_name not in OVERLORD_DATA:
        return False
    full_cmc, imp_cmc, imp_counters, power, toughness = OVERLORD_DATA[overlord_name]

    for c in list(gs.zones.hand):
        if c.name == overlord_name and gs.mana_pool.total() >= imp_cmc:
            try:
                gs.mana_pool.pay("{" + str(imp_cmc) + "}", imp_cmc)
            except Exception:
                continue
            gs.zones.hand.remove(c)
            # Not a creature yet — enchantment/artifact with time counters
            c.counters = imp_counters
            c._impending = True
            gs.zones.battlefield.append(c)
            gs._log(f"  {overlord_name}: Impending {imp_counters} (cost {imp_cmc}), "
                    f"becomes {power}/{toughness} creature in {imp_counters} turns")
            return True
    return False


def cast_hardcast(gs, overlord_name: str, opponent=None) -> bool:
    """Hard-cast an Overlord at full cost — enters as a creature immediately.

    Returns True if cast.
    """
    if overlord_name not in OVERLORD_DATA:
        return False
    full_cmc, imp_cmc, imp_counters, power, toughness = OVERLORD_DATA[overlord_name]

    for c in list(gs.zones.hand):
        if c.name == overlord_name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            c._impending = False
            gs._log(f"  {overlord_name}: hardcast {power}/{toughness} "
                    f"(full cost {full_cmc})")
            return True
    return False


def tick_impending(gs, overlord_name: str, opponent=None) -> bool:
    """At upkeep: remove one time counter. If last, fire ability and become creature.

    Returns True if the Overlord became a creature this turn.
    """
    for c in gs.zones.battlefield:
        if c.name == overlord_name and getattr(c, '_impending', False):
            c.counters = max(0, c.counters - 1)
            if c.counters == 0:
                c._impending = False
                _, _, imp_counters, power, toughness = OVERLORD_DATA[overlord_name]
                c.power = str(power)
                c.toughness = str(toughness)
                c.turn_entered = gs.turn
                c.summoning_sickness = True
                _fire_overlord_ability(gs, overlord_name, imp_counters, opponent)
                gs._log(f"  {overlord_name}: all counters removed, "
                        f"becomes {power}/{toughness} creature!")
                return True
            gs._log(f"  {overlord_name}: {c.counters} time counters remaining")
    return False


def _fire_overlord_ability(gs, name: str, counters: int, opponent):
    """Fire the Overlord's ETB ability when it becomes a creature."""
    if name == HAUNTWOODS:
        # Create 4/4 Dryad tokens (simplified: 1 token per 2 counters)
        for _ in range(max(1, counters // 2)):
            tok = Card("Forest Dryad", "{0}", 4, "Token Creature — Dryad")
            tok.power = "4"; tok.toughness = "4"
            tok.turn_entered = gs.turn; tok.summoning_sickness = True
            gs.zones.battlefield.append(tok)
        gs._log(f"  Hauntwoods: {max(1, counters//2)} Dryad tokens")

    elif name == BOILERBILGES:
        dmg = counters
        gs.damage_dealt += dmg
        gs._log(f"  Boilerbilges: {dmg} damage to each opponent")

    elif name == BALEMURK:
        gs.zones.draw(counters)
        gs._log(f"  Balemurk: draw {counters}, opp mills {counters}")

    elif name == MISTMOORS:
        for _ in range(counters):
            tok = Card("Spirit Token", "{0}", 2, "Token Creature — Spirit")
            tok.power = "2"; tok.toughness = "2"
            tok.turn_entered = gs.turn; tok.summoning_sickness = True
            gs.zones.battlefield.append(tok)
        gs._log(f"  Mistmoors: {counters} Spirit tokens")

    elif name == FLOODPITS:
        gs._log(f"  Floodpits: may counter up to {counters} target spells")
