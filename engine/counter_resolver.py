"""Counterspell resolution.

Wires Spell Snare, Phantom Interference, Negate, Spell Pierce, Annul,
Disdainful Stroke, Essence Scatter, Spider-Sense, Disrupting Shoal, etc.
into the active-cast window. Without this module those handlers were
no-ops and tempo-style decks (Dimir Midrange, Esper Pixie, Jeskai)
were systematically underrated by the sim.

Design:
- `try_counter_spell(opp_apl, opp_gs, my_gs, spell)` is called from
  `GameState.cast_spell` after mana is paid, before the spell resolves.
- We auto-tap opp's lands for response mana (matches the "mana
  accumulation" approximation used elsewhere in the engine -- both
  players tap freely for instant-speed interaction).
- The counterspell must (a) be in opp's hand, (b) be castable with
  opp's available mana, (c) match the validity gate for the spell
  being cast, and (d) be value-positive per a simple heuristic.
- If multiple counters are valid we pick the cheapest legal one
  (preserve flexible counters for harder targets later).
"""
from __future__ import annotations
from data.card import Tag


# ─── Counter validity per card ──────────────────────────────────────
# Each predicate takes the spell being cast and returns True iff this
# counter can legally target it.

def _is_creature(spell):
    return spell.has(Tag.CREATURE)


def _is_noncreature(spell):
    return not spell.has(Tag.CREATURE)


def _is_artifact_or_enchantment(spell):
    return spell.has(Tag.ARTIFACT) or spell.has(Tag.ENCHANTMENT)


# (validity_predicate, base_cost_cmc, name_for_log)
COUNTER_VALIDITY = {
    "Spell Snare":          (lambda s: getattr(s, 'cmc', 0) == 2,         1),
    "Spell Pierce":         (_is_noncreature,                              1),
    "Negate":               (_is_noncreature,                              2),
    "Phantom Interference": (_is_noncreature,                              2),  # counter mode is {1}{U}
    "Disdainful Stroke":    (lambda s: getattr(s, 'cmc', 0) >= 4,          2),
    "Essence Scatter":      (_is_creature,                                 2),
    "Annul":                (_is_artifact_or_enchantment,                  1),
    "Spider-Sense":         (_is_noncreature,                              2),  # counters instant/sorcery/triggered
    "Disrupting Shoal":     (lambda s: True,                               0),  # any spell, alt-cost
    "Counterspell":         (lambda s: True,                               2),
    "Mystical Dispute":     (_is_noncreature,                              2),
    "Daze":                 (lambda s: True,                               1),
    "Force of Will":        (lambda s: True,                               5),
    "Force of Negation":    (_is_noncreature,                              5),
    "Subtlety":             (lambda s: True,                               4),
    "Consign to Memory":    (_is_noncreature,                              2),
    # Get Out modes: 1) counter creature/enchantment spell  2) bounce 1-2 owned (handled in APL)
    # Effective cmc=3 in the value gate -- it's {U}{U} actual cost but bouncing own
    # for tempo is usually higher value than countering a cheap creature. Forces it
    # to fire only on priority targets (Sapling Nursery, Earthbender Ascension, etc.)
    # or CMC>=3 spells.
    "Get Out":              (lambda s: s.has(Tag.CREATURE) or s.has(Tag.ENCHANTMENT), 3),
}

# Spells worth countering (high-impact engines / removal / finishers).
# When the spell being cast is in this set, we counter eagerly. When
# it's NOT in this set, we only counter if the value calculation says
# so (tempo trade -- counter cost < spell cost).
_PRIORITY_COUNTER_TARGETS = {
    # Engines / payoffs
    "Monument to Endurance", "Stormchaser's Talent", "Artist's Talent",
    "Sapling Nursery", "Earthbender Ascension", "Resonating Lute",
    "Overlord of the Mistmoors", "Aetherspouts", "High Noon",
    "Voice of Victory", "Sunfall", "Aang, Avatar of the Air",
    "Stock Up", "Enduring Curiosity", "Wan Shi Tong, Librarian",
    "Bringer of the Last Gift", "Doomsday Excruciator",
    "Pixie Guide", "Nowhere to Run", "Sheoldred, the Apocalypse",
    "Phlage, Titan of Fire's Fury", "Ral, Crackling Wit",
    "Pawpatch Recruit", "Lumbering Worldwagon",
    "Kaito, Bane of Nightmares",
    # Wipes
    "Day of Black Sun", "Day of Judgment", "Wrath of God",
    # Hard removal at 4+ CMC
    "Vanish into Eternity",
    # Threat creatures (when cast as the spell)
    "Slickshot Show-Off",  # 2-mana but high-impact
}


def _spell_value(spell) -> int:
    """Heuristic value of a spell. CMC + bonus for being a priority target."""
    base = int(getattr(spell, 'cmc', 0) or 0)
    if spell.name in _PRIORITY_COUNTER_TARGETS:
        base += 3
    return base


def _tap_lands_for_response(gs):
    """Make opp's lands' mana available for instant-speed counter.

    Match-runner approximation: lands never untap between turns (no
    untap step in the loop), so checking `not tapped` would leave opp
    with zero response mana every window. `_build_view` already adds
    mana from every land regardless of tap state -- mirror that here so
    opp's reactive pool matches their active pool. Without this, the
    resolver wires correctly but conversion is ~4% (counters in hand
    fail the affordability gate because opp has 0 untapped lands)."""
    # Skip if pool already represents this turn's lands (avoid double-fill
    # when the same window fires multiple times for chained casts).
    if getattr(gs, '_response_pool_filled_turn', None) == getattr(gs, 'turn', 0):
        return
    gs._response_pool_filled_turn = getattr(gs, 'turn', 0)
    for land in gs.zones.lands_on_battlefield():
        try:
            gs.mana_pool.add_land(land.type_line or "", land.name or "")
        except Exception:
            gs.mana_pool.add("C", 1)


def try_counter_spell(opp_apl, opp_gs, my_gs, spell) -> bool:
    """Return True if opp counters the spell.

    Checks opp's hand for valid counters, picks the cheapest legal one
    that's value-positive vs the spell, casts it (paying mana), and
    returns True. Returns False if no counter fired.
    """
    # Voice of Victory blocks opp from casting on our turn
    if any(c.name == "Voice of Victory" for c in my_gs.zones.battlefield):
        return False

    spell_val = _spell_value(spell)

    # Find valid counters in opp hand
    candidates = []
    for c in opp_gs.zones.hand:
        if c.name not in COUNTER_VALIDITY:
            continue
        validity_fn, base_cmc = COUNTER_VALIDITY[c.name]
        if not validity_fn(spell):
            continue
        candidates.append((c, base_cmc))

    if not candidates:
        return False

    # Tap lands so we have response mana
    _tap_lands_for_response(opp_gs)

    # Try cheapest counter first (preserves flex for bigger targets later)
    candidates.sort(key=lambda x: x[1])

    for counter, counter_cmc in candidates:
        # Affordability check
        if not opp_gs.mana_pool.can_cast(counter.mana_cost, counter.cmc):
            # Try Phantom Interference's counter mode {1}{U} if it's
            # the {U} Spree base (handled by cmc==2 in card_db)
            continue

        # Value check: counter should be at most as expensive as the
        # spell value (otherwise tempo-negative). Always counter
        # priority targets regardless of cost.
        if (spell.name not in _PRIORITY_COUNTER_TARGETS
                and counter_cmc > spell_val):
            continue

        # Cast the counter (no recursion -- _in_counter_window is set
        # on my_gs but cast_spell uses my_gs._in_counter_window to skip
        # the window, so the counter spell itself won't trigger one)
        opp_gs._in_counter_window = True
        try:
            opp_gs.mana_pool.pay(counter.mana_cost, counter.cmc)
            opp_gs.zones.hand.remove(counter)
            opp_gs.zones.graveyard.append(counter)
            opp_gs.spells_cast_this_turn += 1
            opp_gs.noncreature_spells_this_turn += 1
            opp_gs._log(f"  [reactive] cast {counter.name} -> counter {spell.name}")
        finally:
            opp_gs._in_counter_window = False
        return True

    return False
