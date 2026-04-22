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


def _silvergill_mentor_etb(gs, card):
    """Silvergill Mentor ETB: create a 1/1 W/U Merfolk token."""
    token = gs._make_token("Merfolk Token", "1", "1",
                            "Token Creature — Merfolk")
    gs._log("  Silvergill Mentor: +1/1 Merfolk token")


ETB_EFFECTS = {
    "Gran-Gran": _gran_gran_etb,
    "Courier's Briefcase": _couriers_briefcase_etb,
    "Invasion of Zendikar": _invasion_of_zendikar_etb,
    "Silvergill Mentor": _silvergill_mentor_etb,
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


def _lightning_helix(gs, card):
    """Lightning Helix — 3 damage + 3 life. Goldfish: face damage +
    defensive life (matters in match mode, not goldfish WR)."""
    gs.damage_dealt += 3
    gs.life += 3
    gs._log(f"  Lightning Helix: 3 dmg + 3 life "
            f"({gs.damage_dealt} dmg, {gs.life} life)")


def _consult_star_charts(gs, card):
    """Consult the Star Charts — 'Look at top X cards of your library,
    where X is the number of lands you control. Put one into your
    hand. Kicker {1}{U}: put all X into your hand instead.'

    Goldfish shortcut: kick whenever we had spare mana at cast time
    (mana_pool.total() >= 4 pre-pay). We can't know the pool state
    here (already paid), so infer from lands_in_play:
      - 4+ lands and the card wasn't literally the only spell we
        could cast this turn → we probably had the kicker mana →
        draw min(X, 4) cards
      - Otherwise draw 1.
    """
    lands_in_play = sum(1 for c in gs.zones.battlefield if c.is_land())
    # Simple heuristic: assume kicked when we have 5+ lands (base
    # cost {1}{U} = 2, kicker adds {1}{U} = 4 total, so we need at
    # least 4 mana capacity; 5 lands gives headroom for other plays).
    if lands_in_play >= 5:
        draw_count = min(lands_in_play, len(gs.zones.library))
        gs.zones.draw(draw_count)
        gs._log(f"  Consult the Star Charts (kicked): draw {draw_count}")
    else:
        gs.zones.draw(1)
        gs._log("  Consult the Star Charts: draw 1")


def _jeskai_revelation(gs, card):
    """Jeskai Revelation — big kitchen-sink 7-cmc. 4 damage face
    (from the 'any target'), draw 2, gain 4, make two 1/1 Monk
    tokens with prowess. Bounce mode skipped (no target in goldfish)."""
    gs.damage_dealt += 4
    gs.zones.draw(2)
    gs.life += 4
    # Tokens: use make_token
    from engine.keywords import KWTag
    for _ in range(2):
        tok = gs._make_token("Monk Token", "1", "1",
                              "Token Creature — Monk")
        tok.tags.add(KWTag.PROWESS)
    gs._log(f"  Jeskai Revelation: 4 dmg, 2 draw, 4 life, +2 Monks "
            f"({gs.damage_dealt} dmg)")


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
    "Lightning Helix":      _lightning_helix,
    "Consult the Star Charts": _consult_star_charts,
    "Jeskai Revelation":    _jeskai_revelation,
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
