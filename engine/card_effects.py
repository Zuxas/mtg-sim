"""engine/card_effects.py -- Per-card effect dispatch for unique cards.

Catch-all registry for card effects that don't fit the generic
Saga / Class / keyword pipelines. Each handler is keyed by card name
and called at the appropriate hook point:

  on_etb(gs, card)       — fired from _apply_entering_etb
  on_spell_cast(gs, card_cast)
                          — fired from cast_spell. card_cast is the
                            spell that resolved; handlers iterate
                            battlefield and react.
  on_discard_event(gs, discarded_card)
                          — fired when a card is discarded (by any
                            source).

Keep each handler narrow and specific to one card — this is the
'wide surface, shallow logic' alternative to embedding every card
rule inside GameState.
"""


# ── ETB effects ─────────────────────────────────────────────────────

def _gran_gran_etb(gs, card):
    """Gran-Gran is a 2/2 creature with draw/discard on tap. ETB is
    vanilla; the synergy lives in its triggered ability and static."""
    pass  # no ETB


def _couriers_briefcase_etb(gs, card):
    """Courier's Briefcase (Standard / Streets of New Capenna) creates
    a Treasure token when it enters. Its +1 ability to gather info is
    a repeatable activation we simplify to 'free draw every turn'
    handled via the upkeep path (not modeled here — just the ETB)."""
    gs.make_treasure_token()


def _invasion_of_zendikar_etb(gs, card):
    """Invasion of Zendikar is a Battle; in Standard Domain Ramp it
    triggers 'search your library for up to 2 basic lands, put them
    tapped, shuffle'. Goldfish approx: +2 to flex and log the ramp."""
    gs.mana_pool.flex += 2
    gs._log("  Invasion of Zendikar: +2 mana (ramped 2 basics)")


ETB_EFFECTS = {
    "Gran-Gran": _gran_gran_etb,
    "Courier's Briefcase": _couriers_briefcase_etb,
    "Invasion of Zendikar": _invasion_of_zendikar_etb,
}


def on_etb(gs, card):
    """Called from GameState._apply_entering_etb."""
    fn = ETB_EFFECTS.get(card.name)
    if fn is None:
        return
    try:
        fn(gs, card)
    except Exception as e:
        gs._log(f"  ETB effect {card.name} error: {e}")


# ── Discard triggers (Monument to Endurance) ───────────────────────

def _monument_to_endurance_on_discard(gs, discarded, mon):
    """Monument to Endurance triggers when you discard a card.
    Rotates through three modes (draw / treasure / drain 3) — each
    chosen once per turn. Track on the monument's counters bitmask."""
    used_this_turn = getattr(mon, "_monument_used_modes", 0)
    # Prefer the drain mode (3 face damage) over draw / treasure in
    # goldfish since it's the only face damage path.
    if not (used_this_turn & 0b100):
        gs.damage_dealt += 3
        mon._monument_used_modes = used_this_turn | 0b100
        gs._log(f"  Monument to Endurance: drain 3 ({gs.damage_dealt} total)")
        return
    if not (used_this_turn & 0b001):
        gs.zones.draw(1)
        mon._monument_used_modes = used_this_turn | 0b001
        gs._log("  Monument to Endurance: draw 1")
        return
    if not (used_this_turn & 0b010):
        gs.make_treasure_token()
        mon._monument_used_modes = used_this_turn | 0b010


def on_discard_event(gs, discarded):
    """Called whenever a card is discarded. Fire every relevant
    trigger across the battlefield."""
    for perm in list(gs.zones.battlefield):
        if perm.name == "Monument to Endurance":
            try:
                _monument_to_endurance_on_discard(gs, discarded, perm)
            except Exception as e:
                gs._log(f"  Monument trigger error: {e}")


def reset_per_turn_effects(gs):
    """Reset per-turn flags on permanents (called from _upkeep)."""
    for perm in gs.zones.battlefield:
        if perm.name == "Monument to Endurance":
            perm._monument_used_modes = 0


# ── Spell effects (resolve-on-cast) ────────────────────────────────

def _abandon_attachments(gs, card):
    """Discard a card, draw 2. Pick a land or a dead-weight spell to
    discard, then draw. Trigger Monument via on_discard_event."""
    if not gs.zones.hand:
        return
    discards = [c for c in gs.zones.hand if c.is_land()]
    if not discards:
        discards = list(gs.zones.hand)
    victim = discards[-1]
    gs.zones.hand.remove(victim)
    gs.zones.graveyard.append(victim)
    gs._log(f"  Abandon Attachments: discard {victim.name}, draw 2")
    on_discard_event(gs, victim)
    gs.zones.draw(2)


def _accumulate_wisdom(gs, card):
    """Look at top 3, take 1 (or all 3 if 3+ Lessons in graveyard)."""
    lessons_in_gy = sum(
        1 for c in gs.zones.graveyard
        if "lesson" in (c.type_line or "").lower()
    )
    take = min(3, len(gs.zones.library)) if lessons_in_gy >= 3 else 1
    gs.zones.draw(take)   # simplification: just draws
    gs._log(f"  Accumulate Wisdom: draw {take} "
            f"({lessons_in_gy} Lessons in GY)")


def _iroh_demonstration(gs, card):
    """Choose one: 1 damage to each opp creature, OR 4 to a creature.
    Goldfish has no opp creatures — the spell resolves but does
    nothing face-relevant. Log for visibility."""
    gs._log("  Iroh's Demonstration: no creatures to target (goldfish)")


def _boomerang_basics(gs, card):
    """Bounce a nonland permanent. Goldfish: returns the oldest Lesson
    we've stuck so we can replay it for more Monument procs."""
    gs._log("  Boomerang Basics: (no target in goldfish)")


def _combustion_technique(gs, card):
    """2 + lessons-in-gy damage to a creature. Face-invalid in
    goldfish. Log only."""
    gs._log("  Combustion Technique: no creature target (goldfish)")


def _firebending_lesson(gs, card):
    """2 or 5 damage to a creature. No face target in goldfish."""
    gs._log("  Firebending Lesson: no creature target (goldfish)")


def _quench_ya(gs, card):
    """Counter a spell unless opp pays 2. No opp spells in goldfish."""
    gs._log("  It'll Quench Ya!: nothing to counter (goldfish)")


def _opt(gs, card):
    """Opt — scry 1, draw 1. Goldfish: just draw 1."""
    gs.zones.draw(1)


def _sleight_of_hand(gs, card):
    """Sleight of Hand — look at top 2, pick 1. Goldfish: draw 1."""
    gs.zones.draw(1)


def _stock_up(gs, card):
    """Stock Up — look at top 5, put 2 in hand. Goldfish: draw 2."""
    gs.zones.draw(2)


def _bounce_off(gs, card):
    """Bounce Off — return creature to hand. No target in goldfish;
    the cast still fires prowess and feeds the graveyard."""
    pass


SPELL_EFFECTS = {
    "Abandon Attachments":  _abandon_attachments,
    "Accumulate Wisdom":    _accumulate_wisdom,
    "Iroh's Demonstration": _iroh_demonstration,
    "Boomerang Basics":     _boomerang_basics,
    "Combustion Technique": _combustion_technique,
    "Firebending Lesson":   _firebending_lesson,
    "It'll Quench Ya!":     _quench_ya,
    "Opt":                  _opt,
    "Sleight of Hand":      _sleight_of_hand,
    "Stock Up":             _stock_up,
    "Bounce Off":           _bounce_off,
    # Burst Lightning face damage handled by AggroAPL's BURN_SPELLS —
    # registering here would double-count.
}


def on_spell_resolve(gs, card):
    """Called from cast_spell right after the spell moves to GY."""
    fn = SPELL_EFFECTS.get(card.name)
    if fn is None:
        return
    try:
        fn(gs, card)
    except Exception as e:
        gs._log(f"  Spell effect {card.name} error: {e}")
