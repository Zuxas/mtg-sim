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


def _novice_inspector_etb(gs, card):
    """Novice Inspector ETB: investigate (create a Clue artifact
    token — sacrifice {2}, T: draw a card). Goldfish shortcut: draw
    1 (the clue will inevitably be cracked on a later turn for its
    effective card-equivalent value)."""
    if gs.zones.library:
        gs.zones.draw(1)
    gs._log("  Novice Inspector ETB: investigate (+1 Clue → +1 card)")


def _starfield_shepherd_etb(gs, card):
    """Starfield Shepherd — {3}{W}{W} 3/2 flying, Warp {1}{W}.
    'When this creature enters, search your library for a basic
    Plains card or a creature card with mana value 1 or less,
    reveal it, put it into your hand, then shuffle.'

    Goldfish shortcut: draw 1 (a tutored card is functionally
    card advantage, though the real effect is selective — basic
    Plains for mana-fix or a 1-cmc creature for deploy)."""
    if gs.zones.library:
        gs.zones.draw(1)
    gs._log("  Starfield Shepherd ETB: tutor Plains or 1-cmc "
            "creature (+1 card)")


def _harvester_of_misery_etb(gs, card):
    """Harvester of Misery — {3}{B}{B} 5/4 menace. 'When this
    creature enters, other creatures get -2/-2 until end of turn.'

    Until-end-of-turn debuff. Only creatures whose effective
    toughness ≤ 2 at ETB time actually die — the shrink reverts
    otherwise. We model by killing eligible creatures and leaving
    survivors untouched."""
    from data.card import Tag

    def _wipe_small(g):
        deaths = []
        for c in list(g.zones.battlefield):
            if c is card or c.is_land() or not c.has(Tag.CREATURE):
                continue
            if c.effective_toughness() <= 2:
                deaths.append(c)
        for c in deaths:
            g.zones.battlefield.remove(c)
            g.zones.graveyard.append(c)
        return len(deaths)

    my_kills = _wipe_small(gs)
    opp = getattr(gs, "_match_opp", None)
    if opp is not None:
        opp_kills = _wipe_small(opp)
        gs._log(f"  Harvester: -2/-2 until EOT — {my_kills} mine "
                f"/ {opp_kills} opp die (big creatures survive)")
    else:
        gs._log(f"  Harvester: -2/-2 until EOT — {my_kills} die")


def _doomsday_excruciator_etb(gs, card):
    """Doomsday Excruciator — {6}{B}{B} 6/6 flying. 'When this
    creature enters, if it was cast, each player exiles all but the
    bottom six cards of their library face down.'

    A graveyard-and-hand-wrecker. Each player's library is trimmed to
    6 cards, everything else face-down exile. In match mode we hit
    both libraries. Goldfish: only our own library.

    The 'if it was cast' clause IS satisfied for Spider-Man casts
    even when Spider-Man enters as a copy of Excruciator — the copy
    object just took on the ETB, which checks whether the spell
    was cast (yes, Spider-Man's cast resolves)."""

    def _trim_library(g):
        # Keep only bottom 6 cards; exile the rest
        lib = g.zones.library
        if len(lib) <= 6:
            return 0
        exile_count = len(lib) - 6
        # bottom 6 are the LAST 6 in the list (assuming draw pops front)
        exiled = lib[:exile_count]
        g.zones.library = lib[exile_count:]
        g.zones.exile.extend(exiled)
        return exile_count

    my_exiled = _trim_library(gs)
    opp = getattr(gs, "_match_opp", None)
    if opp is not None:
        opp_exiled = _trim_library(opp)
        gs._log(f"  Excruciator ETB: me exile {my_exiled}, "
                f"opp exile {opp_exiled} (libraries trimmed to 6)")
    else:
        gs._log(f"  Excruciator ETB: exile {my_exiled} (library to 6)")


def _malboro_etb(gs, card):
    """Malboro — {4}{B}{B} 4/4. 'Bad Breath — When this creature
    enters, each opponent discards a card, loses 2 life, and exiles
    the top three cards of their library.'"""
    opp = getattr(gs, "_match_opp", None)
    if opp is None:
        gs._log("  Malboro: no opp (goldfish)")
        return
    # Discard — exile a random card from opp's hand
    if opp.zones.hand:
        # Pick opp's highest-cmc card to "discard"
        victim = max(opp.zones.hand, key=lambda c: getattr(c, 'cmc', 0))
        opp.zones.hand.remove(victim)
        opp.zones.graveyard.append(victim)
    # 2 life loss
    opp.life -= 2
    # Mill top 3 of opp library
    for _ in range(3):
        if opp.zones.library:
            milled = opp.zones.library.pop(0)
            opp.zones.exile.append(milled)
    gs._log(f"  Malboro Bad Breath: opp -2 life, discard, exile 3")


def _badgermole_cub_etb(gs, card):
    """Badgermole Cub — {1}{G} 2/2. 'When this creature enters,
    earthbend 1. (Target land you control becomes a 0/0 creature
    with haste that's still a land. Put a +1/+1 counter on it...).'
    Static: 'Whenever you tap a creature for mana, add an additional
    {G}.'

    Goldfish: earthbend animates a land as a 1/1 haste creature
    (0/0 base + +1/+1 counter). We model this as +1 flex mana on
    next tap (the +G static) and a one-time +1 counter-equivalent
    bump to damage as a proxy for the new attacker."""
    # Approximate the animated-land attacker — add +1 damage per
    # Badgermole ETB as a placeholder for its earthbent 1/1 body.
    gs.damage_dealt += 1
    gs._log(f"  Badgermole Cub: earthbend 1 (+1 dmg proxy for "
            f"animated land, total {gs.damage_dealt})")


def _cosmogrand_zenith_etb(gs, card):
    """Cosmogrand Zenith — {2}{W} 2/4. Body only on ETB. The trigger
    ('when you cast your second spell each turn') is fired from
    game_state.cast_spell → on_cosmogrand_second_spell."""
    gs._log("  Cosmogrand Zenith: ETB (2/4)")


def on_cosmogrand_second_spell(gs):
    """Fires when `gs.spells_cast_this_turn == 2`. For each
    Cosmogrand Zenith we control, choose the better of:
      • Create two 1/1 white Human Soldier creature tokens.
      • Put a +1/+1 counter on each creature you control.

    Heuristic: if we already have 3+ creatures, counter-everyone is
    better; else tokens add bodies for swinging. Goldfish pick the
    one that maximizes face damage on next attack."""
    from data.card import Tag
    zeniths = [c for c in gs.zones.battlefield
               if c.name == "Cosmogrand Zenith"]
    if not zeniths:
        return
    my_creatures = [c for c in gs.zones.battlefield
                    if not c.is_land() and c.has(Tag.CREATURE)]
    # Pick mode: 2 tokens (adds 2 bodies) or counters (adds N counters)
    for zenith in zeniths:
        if len(my_creatures) >= 3:
            for c in my_creatures:
                c.counters = (c.counters or 0) + 1
            gs._log(f"  Cosmogrand (2nd spell): +1/+1 on "
                    f"{len(my_creatures)} creatures")
        else:
            for _ in range(2):
                tok = gs._make_token("Human Soldier", "1", "1",
                                      "Token Creature — Human Soldier")
            gs._log("  Cosmogrand (2nd spell): +2 Human Soldier tokens")


def _overlord_hauntwoods_etb(gs, card):
    """Overlord of the Hauntwoods: 'Whenever this permanent enters
    or attacks, create a tapped colorless land token named Everywhere
    that is every basic land type.'

    The Everywhere token is a LAND so it triggers landfall. Being
    every basic land type means it counts as Plains + Island + Swamp
    + Mountain + Forest simultaneously — huge for domain decks."""
    from data.card import Card, Tag
    token = Card(
        name="Everywhere",
        mana_cost="",
        cmc=0,
        type_line="Token Land — Plains Island Swamp Mountain Forest",
        oracle_text="",
        power="",
        toughness="",
        colors=[],
    )
    token.tapped = True  # enters tapped
    token.turn_entered = gs.turn
    gs.zones.battlefield.append(token)
    gs._log("  Hauntwoods ETB: create Everywhere land token (all 5 types)")
    # Land ETB triggers landfall for other permanents (Badgermole Cub)
    on_landfall(gs)


def _overlord_boilerbilges_etb(gs, card):
    """Overlord of the Boilerbilges: 'Whenever this permanent enters
    or attacks, it deals 4 damage to any target.' Goldfish: face."""
    gs.damage_dealt += 4
    gs._log(f"  Boilerbilges ETB: 4 dmg face ({gs.damage_dealt})")


def _overlord_balemurk_etb(gs, card):
    """Overlord of the Balemurk — {3}{B}{B} 5/5. 'Whenever this
    permanent enters or attacks, mill four cards, then you may
    return a non-Avatar creature card or a planeswalker card from
    your graveyard to your hand.'

    Returns to HAND, not battlefield (distinction matters for
    reanimator math). Goldfish: mill 4, then pick the best eligible
    card from GY and put it back in hand."""
    from data.card import Tag
    for _ in range(4):
        if gs.zones.library:
            milled = gs.zones.library.pop(0)
            gs.zones.graveyard.append(milled)
    # Return best eligible card from GY to hand (non-Avatar creature
    # or planeswalker). Avatar check is by subtype in type_line.
    eligible = [
        c for c in gs.zones.graveyard
        if (c.has(Tag.CREATURE) and "Avatar" not in (c.type_line or ""))
        or "Planeswalker" in (c.type_line or "")
    ]
    if eligible:
        best = max(eligible, key=lambda c: getattr(c, 'cmc', 0))
        gs.zones.graveyard.remove(best)
        gs.zones.hand.append(best)
        gs._log(f"  Balemurk ETB: mill 4, return {best.name} to hand")
    else:
        gs._log("  Balemurk ETB: mill 4 (no eligible GY target)")


def _bringer_last_gift_etb(gs, card):
    """Bringer of the Last Gift — {6}{B}{B} 6/6 flying. 'When this
    creature enters, if you cast it, each player sacrifices all
    other creatures they control. Then each player returns all
    creature cards from their graveyard that weren't put there
    this way to the battlefield.'

    A Living End-on-a-body. Huge tempo swing when our GY is loaded
    with milled creatures and the opp's side is smaller. The 'if
    you cast it' clause is satisfied — we only call this handler
    from the cast path.

    Both-player semantics: the card says 'each player sacrifices all
    other creatures they control. Then each player returns all
    creature cards from their graveyard that weren't put there this
    way to the battlefield.' In match mode we reach the opp via
    gs._match_opp (set by match_engine)."""
    from data.card import Tag

    def _sac_and_reanim(g):
        """Run the Living End effect on a single game state."""
        sacs = [c for c in g.zones.battlefield
                if c is not card
                and c.has(Tag.CREATURE) and not c.is_land()]
        for c in sacs:
            g.zones.battlefield.remove(c)
            g.zones.graveyard.append(c)
        sacrificed_ids = {id(c) for c in sacs}
        gy_creatures = [c for c in g.zones.graveyard
                        if c.has(Tag.CREATURE)
                        and id(c) not in sacrificed_ids]
        reanimated = []
        for c in gy_creatures:
            g.zones.graveyard.remove(c)
            g.zones.battlefield.append(c)
            c.turn_entered = g.turn
            c.summoning_sickness = True
            c.tapped = False
            reanimated.append(c)
        return len(sacs), reanimated

    my_sacs, my_reanim = _sac_and_reanim(gs)
    opp = getattr(gs, "_match_opp", None)
    if opp is not None:
        opp_sacs, opp_reanim = _sac_and_reanim(opp)
        gs._log(f"  Bringer ETB: me sac {my_sacs}/reanim {len(my_reanim)}, "
                f"opp sac {opp_sacs}/reanim {len(opp_reanim)}")
    else:
        gs._log(f"  Bringer ETB: sac {my_sacs}, reanim {len(my_reanim)} "
                f"(goldfish — own side only)")


def _superior_spider_man_etb(gs, card):
    """Superior Spider-Man — {2}{U}{B} 4/4. 'Mind Swap: You may
    have Superior Spider-Man enter as a copy of any creature card
    in a graveyard, except his name is Superior Spider-Man and
    he's a 4/4 Spider Human Hero in addition to his other types.
    When you do, exile that card.'

    The combo cheat: pick Bringer of the Last Gift in GY, copy it,
    Bringer's ETB fires (because this IS a cast spell resolving),
    and Living End goes off for 4 mana instead of 8. We model this
    by: if the biggest creature in GY is Bringer, exile it and run
    Bringer's ETB here. Otherwise pick the strongest creature in GY
    and steal its ETB stats (approximated as: bump our damage by
    its effective_power as a proxy for the body swing).

    Matching real play — Doomsday / Sultai Reanimator decks run
    Spider-Man specifically to cheat Bringer into play earlier."""
    from data.card import Tag
    gy_creatures = [c for c in gs.zones.graveyard
                     if c.has(Tag.CREATURE)]
    if not gy_creatures:
        return
    # Priority: copy Bringer of the Last Gift if we've got one
    bringer_in_gy = next((c for c in gy_creatures
                           if c.name == "Bringer of the Last Gift"), None)
    if bringer_in_gy is not None:
        gs.zones.graveyard.remove(bringer_in_gy)
        gs.zones.exile.append(bringer_in_gy)
        gs._log("  Spider-Man: copy Bringer from GY (exile target)")
        # Spider-Man is now a 4/4 with Bringer's ETB firing
        _bringer_last_gift_etb(gs, card)
        return
    # No Bringer — copy the biggest creature from GY
    best = max(gy_creatures, key=lambda c: getattr(c, 'cmc', 0))
    gs.zones.graveyard.remove(best)
    gs.zones.exile.append(best)
    gs._log(f"  Spider-Man: copy {best.name} from GY (exile)")
    # Approximate the copy by boosting Spider-Man's power
    extra_power = max(0, int(getattr(best, 'power', 0) or 0) - 4)
    if extra_power:
        card.counters = (card.counters or 0) + extra_power
        gs._log(f"    copy pump: +{extra_power}/+{extra_power}")


def _deceit_etb(gs, card):
    """Deceit — {4}{U/B}{U/B} 5/5. Two ETB modes:
      - if {U}{U} spent: bounce target nonland permanent to hand
      - if {B}{B} spent: target opp discards a chosen nonland card
    Also has Evoke {U/B}{U/B} (sac on ETB — cheat it out for 2 mana).

    Goldfish shortcut: we assume the caster paid BOTH {U}{U} AND
    {B}{B} (common Sultai Reanimator play: cast for full 6 mana
    so both triggers fire). Bounce mode = log only (no target in
    goldfish). Discard mode = opponent-side trigger handled in
    match mode only. Here we log and approximate as +1 card (from
    the mill the discard'd opp would take). Evoke-mode cast sacs
    Deceit to GY — a free reanimator target for Bringer later."""
    gs._log("  Deceit ETB: dual-mode bounce + discard (goldfish log-only)")


def _overlord_balemurk_etb_v2(gs, card):
    """Placeholder to avoid name collision — reserved for future
    update if Balemurk's impending Saga chapters need modeling."""
    pass


def _enduring_innocence_etb(gs, card):
    """Enduring Innocence — {1}{W}{W} 2/1 Lifelink. 'Whenever one
    or more OTHER creatures you control with power 2 or less enter,
    draw a card. This ability triggers only once each turn.'

    The trigger fires on OTHER creatures entering, not on Innocence
    itself. We flag the battlefield with _enduring_innocence_active
    so the per-turn draw fires on the next small-creature ETB.
    Goldfish: skip draw on ETB (not valid) — draws come later."""
    gs._log("  Enduring Innocence: 2/1 lifelink on board "
            "(draws on other 2-power creatures ETB)")


ETB_EFFECTS = {
    "Gran-Gran": _gran_gran_etb,
    "Courier's Briefcase": _couriers_briefcase_etb,
    "Invasion of Zendikar": _invasion_of_zendikar_etb,
    "Silvergill Mentor": _silvergill_mentor_etb,
    "Novice Inspector": _novice_inspector_etb,
    "Starfield Shepherd": _starfield_shepherd_etb,
    "Cosmogrand Zenith": _cosmogrand_zenith_etb,
    "Enduring Innocence": _enduring_innocence_etb,
    "Overlord of the Hauntwoods": _overlord_hauntwoods_etb,
    "Overlord of the Boilerbilges": _overlord_boilerbilges_etb,
    "Overlord of the Balemurk": _overlord_balemurk_etb,
    "Bringer of the Last Gift": _bringer_last_gift_etb,
    "Superior Spider-Man": _superior_spider_man_etb,
    "Deceit": _deceit_etb,
    "Badgermole Cub": _badgermole_cub_etb,
    "Harvester of Misery": _harvester_of_misery_etb,
    "Doomsday Excruciator": _doomsday_excruciator_etb,
    "Malboro": _malboro_etb,
}


# ── Landfall — fires from play_land() on every land ETB ────────────

# Landfall registry (verified against Scryfall oracle text 2026-04-22).
# Each set lists cards whose landfall trigger does a specific thing.
#
# LANDFALL_GROW — Sazh's Chocobo: "Whenever a land you control enters,
# put a +1/+1 counter on this creature."
LANDFALL_GROW = {
    "Sazh's Chocobo",
}

# LANDFALL_MILL — Icetill Explorer: "Whenever a land you control
# enters, mill a card." Useful for Sultai Reanimator-style GY fills.
LANDFALL_MILL = {
    "Icetill Explorer",
}

# LANDFALL_DOUBLE — Mightform Harmonizer: "Whenever a land you
# control enters, double the power of target creature you control
# until end of turn." Huge swing at 4+ lands in play.
LANDFALL_DOUBLE = {
    "Mightform Harmonizer",
}

# LANDFALL_QUEST — Earthbender Ascension: "Whenever a land you
# control enters, put a quest counter on this enchantment. When you
# do, if it has four or more quest counters on it, put a +1/+1
# counter on target creature you control. It gains trample until
# end of turn." Needs 4 triggers before it actually pumps.
LANDFALL_QUEST = {
    "Earthbender Ascension",
}


def on_landfall(gs):
    """Called by play_land after a land resolves. Fires each
    registered landfall trigger. Verified effects only."""
    for c in list(gs.zones.battlefield):
        if c.is_land():
            continue
        if c.name in LANDFALL_GROW:
            c.counters = (c.counters or 0) + 1
            gs._log(f"  Landfall: {c.name} gets +1/+1 counter "
                    f"(total {c.counters})")
        elif c.name in LANDFALL_MILL:
            if gs.zones.library:
                milled = gs.zones.library.pop(0)
                gs.zones.graveyard.append(milled)
                gs._log(f"  Landfall ({c.name}): mill {milled.name}")
        elif c.name in LANDFALL_DOUBLE:
            # Double power of biggest friendly creature until EOT.
            # Goldfish approx: +effective_power counters (temp). To
            # keep combat math simple, we add counters permanently —
            # this overstates the effect but captures the pump swing.
            from data.card import Tag as _Tag
            friends = [x for x in gs.zones.battlefield
                       if not x.is_land() and x.has(_Tag.CREATURE)
                       and x is not c]
            if friends:
                target = max(friends, key=lambda x: x.effective_power())
                bump = max(1, target.effective_power())
                target.counters = (target.counters or 0) + bump
                gs._log(f"  Landfall ({c.name}): double "
                        f"{target.name} (+{bump} counters)")
        elif c.name in LANDFALL_QUEST:
            # Track quest counters via c.counters. At 4+, pump biggest
            # friendly creature once and reset.
            c.counters = (c.counters or 0) + 1
            if c.counters >= 4:
                from data.card import Tag as _Tag
                friends = [x for x in gs.zones.battlefield
                           if not x.is_land() and x.has(_Tag.CREATURE)
                           and x is not c]
                if friends:
                    target = max(friends,
                                  key=lambda x: x.effective_power())
                    target.counters = (target.counters or 0) + 1
                    gs._log(f"  Ascension (4 quests): +1/+1 to "
                            f"{target.name}")
                c.counters = 0  # reset to avoid repeat trigger
            else:
                gs._log(f"  Ascension: quest {c.counters}/4")
        elif c.name == "Mossborn Hydra":
            # "Landfall — Whenever a land you control enters, double the
            # number of +1/+1 counters on this creature."
            # Enters with 1 counter (handled in ETB). Doubling each land
            # models the exponential growth correctly.
            if (c.counters or 0) > 0:
                c.counters = c.counters * 2
                gs._log(f"  Mossborn Hydra: landfall double counters "
                        f"-> {c.counters} ({c.counters}/{c.counters})")
        elif c.name == "Tifa Lockhart":
            # "Landfall — Whenever a land you control enters, double
            # Tifa Lockhart's power until end of turn."
            # Goldfish: model as permanent doubling via power string
            # (acceptable approximation — resets next game).
            try:
                p = int(c.power)
                c.power = str(p * 2)
                gs._log(f"  Tifa Lockhart: landfall double power "
                        f"-> {c.power}/{c.toughness}")
            except (ValueError, TypeError):
                pass
        elif c.name == "Bristly Bill, Spine Sower":
            # "Landfall — Whenever a land you control enters, put a +1/+1
            # counter on target creature you control."
            # Target: biggest creature on board (best use of the trigger).
            from data.card import Tag as _Tag
            friends = [x for x in gs.zones.battlefield
                       if not x.is_land() and x.has(_Tag.CREATURE)]
            if friends:
                target = max(friends, key=lambda x: x.effective_power())
                target.counters = (target.counters or 0) + 1
                gs._log(f"  Bristly Bill: landfall +1/+1 on "
                        f"{target.name}")


# Back-compat alias — old code may import LANDFALL_TOKEN / ASCENSION.
LANDFALL_TOKEN = LANDFALL_GROW   # Chocobo was miscategorized before
LANDFALL_ASCENSION = LANDFALL_QUEST


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


# Load hand-verified handlers (overrides auto-parser output).
# Import at module end to avoid circular imports.
try:
    import engine.card_handlers_verified  # noqa: F401
except Exception as _e:
    print(f"[card_effects] verified handlers failed to load: {_e}")

# Auto-generated set handlers (setdefault — hand-written entries always win).
# sos_auto_handlers: SOS-specific, generated with explicit card list.
# standard_auto_handlers: all 17 Standard sets from oracle bulk.
# Both use setdefault so order doesn't matter; union covers more cards.
try:
    import engine.sos_auto_handlers       # noqa: F401
    import engine.standard_auto_handlers  # noqa: F401
except Exception as _e:
    print(f"[card_effects] auto handlers failed to load: {_e}")
