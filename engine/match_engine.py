"""
engine/match_engine.py — Phase 3A match engine

Runs two MatchAPLs against each other using the MatchGameState.
This is the core game loop for real matchup simulation.

Usage:
    from engine.match_engine import run_match, run_match_set
    from apl.match_apl import GoldfishAdapter
    
    apl_a = GoldfishAdapter(boros_energy_apl)
    apl_b = GoldfishAdapter(izzet_prowess_apl)
    result = run_match(apl_a, deck_a, apl_b, deck_b)
    results = run_match_set(apl_a, deck_a, apl_b, deck_b, n=1000)
"""

from __future__ import annotations
import copy as _copy
import random
from typing import Optional

from engine.match_state import (
    MatchGameState, MatchResult, MatchSetResults,
    resolve_combat, safe_power, safe_toughness, has_keyword,
)
from engine.game_state import GameState, Phase
from engine.stack import (
    Stack, InteractionType, classify_card, get_burn_damage,
    resolve_interaction,
)
from apl.match_apl import MatchAPL, GoldfishAdapter, is_instant_speed
from apl.mulligan import take_opening_hand
from data.card import Card, Tag


def _do_mulligan(apl: MatchAPL, gs: GameState, rng: random.Random) -> int:
    """London mulligan for one player (#14). Returns number of mulligans.

    Draw 7 every time; on keep, bottom one card per mulligan taken. After 3
    mulligans the 4-card hand is kept. Shared with the goldfish path and
    match_runner via apl.mulligan.take_opening_hand.
    """
    hand, library, mulligans = take_opening_hand(
        gs.zones.library, apl.keep, apl.bottom, on_play=gs.on_play,
        max_mulligans=3, rng=rng, shuffle_first=False)
    gs.zones.hand[:] = hand
    gs.zones.library[:] = library
    return mulligans


def _tap_for_response(gs: GameState):
    """
    Allow a player to tap their untapped lands for mana before acting at
    instant speed (pre_combat, declare_blockers, end-step, reactive windows).
    In real MTG, players can tap lands whenever they could cast an instant.
    """
    for land in gs.zones.lands_on_battlefield():
        if not land.tapped:
            land.tapped = True
            gs.mana_pool.add_land(land.type_line, land.name, land.oracle_text or "")


def _try_reactive_interaction(reactive_apl: MatchAPL, reactive_gs: GameState,
                              active_gs: GameState, mgs: MatchGameState,
                              reactive_player: str):
    """
    Give the reactive player a chance to use instant-speed interaction.
    Checks hand for removal/burn/counter and uses the APL to decide.
    """
    # Voice of Victory spell lock: "Your opponents can't cast spells during your turn"
    if any(c.name == "Voice of Victory" for c in active_gs.zones.battlefield):
        return
    
    hand = reactive_gs.zones.hand
    
    # Find instants and flash creatures in hand
    interaction_cards = []
    for c in hand:
        itype = classify_card(c)
        if itype != InteractionType.NONE and is_instant_speed(c):
            # Check if we have mana to cast it
            if hasattr(c, 'cmc') and c.cmc <= reactive_gs.mana_pool.total():
                interaction_cards.append((c, itype))
    
    if not interaction_cards:
        return
    
    # Ask the APL which interaction to use
    response = reactive_apl.respond_to_spell(reactive_gs, active_gs, None)
    # is_instant_speed again: an APL that overrides respond_to_spell may hand
    # back a sorcery, and this is the one place every response goes through.
    if response and response in reactive_gs.zones.hand and is_instant_speed(response):
        itype = classify_card(response)
        
        # Pick target
        target = None
        if itype == InteractionType.REMOVAL:
            creatures = [c for c in active_gs.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
            if creatures:
                target = max(creatures, key=lambda c: safe_power(c))
        
        if itype == InteractionType.BURN:
            damage = get_burn_damage(response)
            creatures = [c for c in active_gs.zones.battlefield
                         if not c.is_land() and safe_toughness(c) <= damage]
            if creatures:
                target = max(creatures, key=lambda c: safe_power(c))
            # If no creature to kill, burn the player
        
        # Cast the spell
        if reactive_gs.can_pay_mana(response.mana_cost, response.cmc):
            reactive_gs.pay_mana(response.mana_cost, response.cmc)
            reactive_gs.zones.hand.remove(response)
            reactive_gs.zones.graveyard.append(response)
            reactive_gs.noncreature_spells_this_turn += 1
            
            # Apply effect
            from engine.stack import Resolution, StackItem
            item = StackItem(card=response, caster=reactive_player,
                             targets=[target] if target else [],
                             interaction_type=itype,
                             damage=get_burn_damage(response) if itype == InteractionType.BURN else 0)
            resolution = Resolution(item, 'resolved')
            resolve_interaction(resolution, reactive_gs, active_gs)
            
            # Check if opponent died from burn
            if active_gs.life <= 0:
                mgs.game_over = True
                mgs.winner = reactive_player
                mgs.win_method = 'combat'


# ---------------------------------------------------------------------------
# R2 instant-speed combat windows (design 1.3 / 1.4 / 1.7).
#
# Two gated priority windows reuse the SHARED R1 pass loop
# (engine.priority_stack.run_priority_pass) instead of mirroring it:
#   WINDOW 1 -- after attackers declared, before blockers (removal: kill the
#              sole blocker so damage connects; defender may remove an attacker).
#   WINDOW 2 -- after blockers declared, before combat damage (pump: a +X/+X
#              instant changes the strike-step math on a blocked attacker).
# Both are APNAP (active player gets priority first). The whole block is reached
# ONLY when _instant_combat_enabled is True, so the gate-OFF path is byte-
# identical to today's shallow-hook combat (design 1.3).
# ---------------------------------------------------------------------------

# Test-only instrumentation, mirrors R1 COUNTERS_CAST. Incremented only when a
# combat instant is actually placed on the stack inside a WINDOW pass. The
# gate-OFF path never reaches it, so any nonzero value is direct evidence R2
# fired in real play. Pure integer bookkeeping -> determinism preserved.
TRICKS_CAST = 0


def reset_trick_count():
    global TRICKS_CAST
    TRICKS_CAST = 0


# Pump instants castable for free via Phyrexian mana (pitched, no land tap).
# Their "cost" is the card moving hand -> graveyard (design 4.1 TEST 1(d)).
_FREE_PITCH_PUMP = {"Mutagenic Growth"}


def _instant_combat_enabled(gs, opp_gs) -> bool:
    """R2 gate: True iff EITHER seat's APL opts into instant-speed combat.

    Mirrors the R1 gate exactly (design 1.4). Reads the APL refs that
    run_match wires onto each GameState (_self_apl / _match_opp_apl). All
    getattr lookups default to None/False, so any path that has not wired the
    APL refs (or any non-tempo deck) returns False -> the gate-OFF combat path
    is untouched.
    """
    self_apl = getattr(gs, '_self_apl', None)
    opp_apl = getattr(gs, '_match_opp_apl', None) or getattr(opp_gs, '_self_apl', None)
    return bool(getattr(self_apl, 'WANTS_INSTANT_COMBAT', False)
                or getattr(opp_apl, 'WANTS_INSTANT_COMBAT', False))


def _pay_for_combat(gs, card) -> bool:
    """Pay a combat instant's cost from ACTUAL untapped mana (design 2).

    Free Phyrexian pump (Mutagenic Growth) is paid by pitch (no mana). Every
    other instant reuses R1's _pay_for_counter, which honors gs.mana_reserve
    and taps real untapped lands. A misjudged-affordability action that cannot
    pay returns False and is treated as a pass by the loop.
    """
    if card.name in _FREE_PITCH_PUMP:
        return True
    from engine.priority_stack import _pay_for_counter
    return _pay_for_counter(gs, card)


def _run_combat_window(active_gs, active_apl, opp_gs, opp_apl, window):
    """Run ONE gated combat priority window via the shared R1 pass loop.

    Seeds an EMPTY stack and offers priority APNAP (active/attacking player
    first). Each side's combat_priority_action returns (card, target) or None.
    A cast instant is enqueued as a StackItem with its interaction_type and
    resolved through engine.stack.resolve_interaction (the path R1 deferred):
      - PUMP  -> targets[0].counters += 2 (read by effective_power/_toughness
                 at damage time, so resolve_combat reflects it for free).
      - REMOVAL/BURN -> the target leaves the battlefield, so blocks/damage
                 recompute without it.
    Returns None (the loop closes when the stack drains to empty). ZERO
    random() -- determinism preserved (design 1.7 / abort G).
    """
    from engine.priority_stack import run_priority_pass

    sides = {
        "caster": (active_gs, active_apl),   # active/attacking player
        "opp":    (opp_gs, opp_apl),         # defending player
    }

    def _ask(apl, my_gs, their_gs, stack):
        if apl is None or my_gs is None:
            return None
        fn = getattr(apl, 'combat_priority_action', None)
        if fn is None:
            return None
        try:
            return fn(my_gs, their_gs, stack, window)
        except TypeError:
            return None

    def _apply(action, gs, priority, stack):
        card, target = action
        if card is None:
            return False
        if card not in gs.zones.hand:
            return False
        if not _pay_for_combat(gs, card):
            return False
        gs.zones.hand.remove(card)
        itype = classify_card(card)
        dmg = get_burn_damage(card) if itype == InteractionType.BURN else 0
        item = stack.cast(card, priority,
                          targets=[target] if target is not None else [],
                          interaction_type=itype, damage=dmg)
        global TRICKS_CAST
        TRICKS_CAST += 1
        log_fn = getattr(gs, '_log', None)
        if callable(log_fn):
            log_fn(f"  [combat W{window}] {priority} casts {card.name}")
        return True

    def _resolve_top(stack, sides, base, owner_gs):
        # stack.resolve_one() returns a Resolution (or None on empty stack).
        resolution = stack.resolve_one()
        if resolution is None:
            return None
        caster_gs = sides[resolution.item.caster][0]
        target_gs = sides[_combat_other(resolution.item.caster)][0]
        # Apply the spell's effect (REMOVAL/BURN move the TARGET; PUMP adds
        # counters). resolve_interaction does NOT move the spell card itself.
        resolve_interaction(resolution, caster_gs, target_gs)
        # The instant itself goes to its caster's graveyard (mirrors R1's
        # counter -> graveyard; satisfies the "cost actually paid" proof).
        if caster_gs is not None:
            caster_gs.zones.graveyard.append(resolution.item.card)
        return None   # never terminal: the window ends only on an empty stack

    stack = Stack()
    run_priority_pass(
        sides, stack,
        base=None, owner_gs=active_gs,
        first="caster",            # APNAP: active/attacking player first
        ask=_ask,
        apply_action=_apply,
        resolve_top=_resolve_top,
    )


def _combat_other(side: str) -> str:
    return "opp" if side == "caster" else "caster"


def _reset_apl(apl):
    """Put an APL back in the state it was in before its first game (#15).

    Callers reuse one APL object across G1-G3 and across whole gauntlets, and
    APLs keep per-game counters on self (Kappa counters, spells cast, flags).
    The first time an APL is seen its attributes are snapshotted; every game
    after that starts from a deep copy of the snapshot. The object identity is
    kept, so callers can still read an APL's state after a game.

    Anything set on the APL before its first game is part of the snapshot and
    survives. Anything set between games is discarded.

    Two escape hatches: an APL that defines reset_game_state() is reset by
    that method alone; an APL whose attributes cannot be deep-copied keeps
    the old named resets and prints one warning.
    """
    # An APL can own its reset: define reset_game_state() and it is used
    # instead of the snapshot.
    custom = getattr(apl, 'reset_game_state', None)
    d = apl.__dict__
    if not callable(custom):
        snap = d.get('_pristine_state')
        if snap is None:
            for k in ('_opp_gs', '_my_gs'):   # stale game states: never part of config
                d.pop(k, None)
            try:
                snap = _copy.deepcopy(d)
            except Exception as e:
                # Something on the APL cannot be copied (a lock, a file, a
                # client). Say so once and fall back to the old named resets.
                print(f"  [!APL RESET] {type(apl).__name__} cannot be snapshotted ({type(e).__name__}); "
                      f"per-game state may leak. Define reset_game_state() on it.")
                snap = False
        if snap:
            d.clear()
            d.update(_copy.deepcopy(snap))
        d['_pristine_state'] = snap
    else:
        custom()
    apl._opp_gs = None
    apl._my_gs = None
    apl._match_dmg = 0
    plotted = getattr(apl, 'PLOTTED_ZONE', None)
    if plotted and hasattr(apl, plotted) and not d.get('_pristine_state'):
        setattr(apl, plotted, [])


def run_match(apl_a: MatchAPL, deck_a: list,
              apl_b: MatchAPL, deck_b: list,
              on_play: bool = True,
              max_turns: int = 40,   # safety cap; see test_games_play_out
              seed: int = None) -> MatchResult:
    """
    Run a single match between two MatchAPLs.
    Returns MatchResult with winner, kill turn, and game data.

    With a seed, the same call replays the same game: engine code that uses
    the global `random` (zones.shuffle, card handlers) is seeded for the
    duration of the game and the caller's global state is restored after.
    """
    # ponytail: the global generator is per process, so seeded games are safe
    # in sequence and across worker processes but not in concurrent threads.
    # Pass a game-owned Random to every consumer if threads are ever needed.
    if seed is None:
        return _run_match(apl_a, deck_a, apl_b, deck_b, on_play, max_turns, seed)
    state = random.getstate()
    random.seed(seed)
    try:
        return _run_match(apl_a, deck_a, apl_b, deck_b, on_play, max_turns, seed)
    finally:
        random.setstate(state)


def _run_match(apl_a, deck_a, apl_b, deck_b, on_play, max_turns, seed) -> MatchResult:
    # Shallow-copy each Card so per-game mutations (power changes, tapped,
    # summoning_sickness, counters) don't leak into subsequent games when
    # the same deck list is reused across run_match_set iterations.
    import copy as _copy
    deck_a = [_copy.copy(c) for c in deck_a]
    deck_b = [_copy.copy(c) for c in deck_b]

    mgs = MatchGameState(deck_a, deck_b, on_play=on_play, seed=seed)

    # Reset per-game state so reused APL objects don't leak anything across
    # games (#15): counters, flags, stale _opp_gs, plotted cards, and so on.
    _reset_apl(apl_a)
    _reset_apl(apl_b)

    # Wire opponent archetype keys so each APL's threat model is accurate.
    try:
        from sim_bridge import _infer_archetype_key as _iak
        apl_a._opp_key = _iak(getattr(apl_b, 'name', '') or '')
        apl_b._opp_key = _iak(getattr(apl_a, 'name', '') or '')
    except Exception:
        pass


    # --- Mulligan phase ---
    mull_a = _do_mulligan(apl_a, mgs.gs_a, mgs.rng)
    mull_b = _do_mulligan(apl_b, mgs.gs_b, mgs.rng)

    # Snapshot kept opening hands (card names) for downstream aggregation.
    hand_a_names = [c.name for c in mgs.gs_a.zones.hand]
    hand_b_names = [c.name for c in mgs.gs_b.zones.hand]

    def _finish():
        result = mgs.to_match_result()
        result.mulligans_a = mull_a
        result.mulligans_b = mull_b
        result.hand_a = hand_a_names
        result.hand_b = hand_b_names
        result._on_play = on_play
        return result

    # --- Game loop ---
    for turn_num in range(1, max_turns + 1):
        mgs.turn = turn_num

        # Both players take a turn each round
        for active in (['a', 'b'] if on_play else ['b', 'a']):
            mgs.active_player = active
            gs = mgs.active_gs()
            opp_gs = mgs.reactive_gs()
            apl = apl_a if active == 'a' else apl_b
            opp_apl = apl_b if active == 'a' else apl_a

            # --- BEGINNING OF TURN ---
            gs.turn = turn_num
            gs.land_played = False
            gs.noncreature_spells_this_turn = 0
            gs.spells_cast_this_turn = 0
            gs.innocence_drew_this_turn = False
            gs._monument_choices_this_turn = set()   # Monument to Endurance choice reset
            # Mana does not carry from one of your turns to the next (CR 500.4).
            # The pool used to be left alone "as a rough proxy for held-up
            # mana", which let it pile up without limit: six lands gave 21
            # mana on turn 6, and every unspent point was banked forever.
            # ponytail: what you leave unspent on your own turn still floats
            # through the opponent's turn. That is the same mana you could
            # have held up by not tapping, so it keeps instant-speed plays
            # working for APLs with no reserve_mana(); empty at end of turn
            # once every APL holds lands back through reserve_mana().
            gs.mana_pool.empty()
            # Stash opp GS on active gs so ETB handlers (Bringer's
            # Living End mass-reanimate, etc.) can reach across.
            gs._match_opp = opp_gs
            opp_gs._match_opp = gs
            # Also wire APL refs so cast_spell can ask the opponent
            # whether to counter at the right window. Set both ways so
            # each player can counter the other's spells.
            gs._match_opp_apl = opp_apl
            opp_gs._match_opp_apl = apl
            # R1: also wire each gs to its OWN apl so cast_spell's gate can
            # check both directions (caster's APL OR opponent's APL may want
            # the priority stack -> enables counter-the-counter). Additive
            # attribute set; no RNG, no effect on the legacy path order.
            gs._self_apl = apl
            opp_gs._self_apl = opp_apl

            # Untap
            for card in gs.zones.battlefield:
                if hasattr(card, 'tapped'):
                    card.tapped = False

            # Remove summoning sickness from creatures that survived a full turn
            if turn_num > 1:
                for card in gs.zones.battlefield:
                    if hasattr(card, 'turn_entered') and card.turn_entered < turn_num:
                        card.summoning_sickness = False

            # Draw (skip for player on the play, turn 1)
            skip_draw = (turn_num == 1 and
                         ((active == 'a' and on_play) or
                          (active == 'b' and not on_play)))
            if not skip_draw and not gs.zones.library:
                # Rule 104.3c: drawing from an empty library loses the game.
                # ponytail: draw step only; the ~300 handler sites that pop
                # the library directly still treat an empty library as a
                # no-op. Route them through one draw() to cover spell draws.
                mgs.game_over = True
                mgs.winner = 'b' if active == 'a' else 'a'
                mgs.win_method = 'decked'
                result = mgs.to_match_result()
                result.mulligans_a = mull_a
                result.mulligans_b = mull_b
                result.hand_a = hand_a_names
                result.hand_b = hand_b_names
                result._on_play = on_play
                return result
            if not skip_draw:
                gs.zones.hand.append(gs.zones.library.pop(0))

            # Let the APL declare how much mana to hold up before tapping.
            # AwareMatchAPL subclasses use this to leave interaction lands untapped.
            gs.mana_reserve = 0   # default: tap everything
            if hasattr(apl, 'reserve_mana'):
                apl.reserve_mana(gs, opp_gs)

            # Tap lands for mana (respects gs.mana_reserve)
            gs.tap_lands()

            # Check if Monument to Endurance drain during tap_lands() killed opponent
            if mgs.check_life('monument_drain'):
                return _finish()

            # --- MAIN PHASE 1 ---
            apl.main_phase_match(gs, opp_gs)
            # SBA (#22): burn/drain/life payment in main phase ends the game now,
            # not after the dead player has taken another turn.
            if mgs.check_life('noncombat'):
                return _finish()

            # --- INTERACTION: Reactive player responds after main phase ---
            opp_player = 'b' if active == 'a' else 'a'
            spells_this_phase = max(1, gs.spells_cast_this_turn)
            _tap_for_response(opp_gs)   # opponent can tap lands to respond
            for _ in range(spells_this_phase):
                _try_reactive_interaction(opp_apl, opp_gs, gs, mgs, opp_player)
                if mgs.check_life('noncombat'):
                    break
            if mgs.game_over:
                result = mgs.to_match_result()
                result.mulligans_a = mull_a
                result.mulligans_b = mull_b
                result.hand_a = hand_a_names
                result.hand_b = hand_b_names
                result._on_play = on_play
                return result

            # --- BEGIN COMBAT ---
            # R2 gate (design 1.4): when ON, the two stepped windows below
            # SUPERSEDE the legacy shallow one-shot hooks so they cannot
            # double-fire. When OFF (every non-tempo deck), gate_on is False and
            # all the legacy hooks run EXACTLY as today (frozen baseline).
            gate_on = _instant_combat_enabled(gs, opp_gs)

            # --- defender pre-combat priority window (legacy shallow hook) ---
            # Tap defending player's untapped lands for mana (they can tap
            # at instant speed in real MTG), then let them act.
            if not gate_on and hasattr(opp_apl, 'pre_combat_instant'):
                _tap_for_response(opp_gs)
                opp_apl.pre_combat_instant(opp_gs, gs)
                if mgs.check_life('noncombat'):
                    result = mgs.to_match_result()
                    result.mulligans_a = mull_a
                    result.mulligans_b = mull_b
                    result.hand_a = hand_a_names
                    result.hand_b = hand_b_names
                    result._on_play = on_play
                    return result

            # --- COMBAT ---
            # Activate Restless lands before declaring attackers so
            # they become eligible (and their activation cost comes
            # out of the main-phase mana pool, not combat mana).
            gs.activate_restless_lands()
            attackers = apl.declare_attackers(gs, opp_gs)
            prowess_boosted = []
            if attackers:
                # Prowess: +1/+0 per noncreature spell cast this turn
                # (rule 702.109). Applied to attackers before blocks so
                # the reach threshold reflects the pumped power.
                from engine.keywords import KWTag
                n_spells = gs.noncreature_spells_this_turn
                if n_spells > 0:
                    for c in attackers:
                        # Standard PROWESS: +1/+0 per noncreature spell (rule 702.109)
                        if KWTag.PROWESS in c.tags:
                            bonus = n_spells
                            c.counters += bonus
                            prowess_boosted.append((c, bonus))

                        # Slickshot Show-Off: +2/+0 per noncreature spell cast this turn
                        # (own trigger, not prowess tag — must be handled explicitly)
                        elif c.name == "Slickshot Show-Off":
                            bonus = n_spells * 2
                            c.counters += bonus
                            prowess_boosted.append((c, bonus))

                        # Colorstorm Stallion (Opus): +1/+1 per instant/sorcery cast
                        # Treated same as prowess for pump purposes
                        elif c.name == "Colorstorm Stallion":
                            bonus = n_spells
                            c.counters += bonus
                            prowess_boosted.append((c, bonus))

                        # Elusive Otter (prowess creature from Stormchaser's Talent token)
                        elif c.name in {"Elusive Otter", "Otter Token"}:
                            bonus = n_spells
                            c.counters += bonus
                            prowess_boosted.append((c, bonus))

                # --- WINDOW 1: after attackers declared, before blockers ---
                if gate_on:
                    # R2 (design 1.3): APNAP priority pass. Active player may
                    # remove the sole blocker so an attacker connects; defender
                    # may remove an attacker before committing blocks. Both
                    # seats can tap real untapped lands first.
                    _tap_for_response(gs)
                    _tap_for_response(opp_gs)
                    _run_combat_window(gs, apl, opp_gs, opp_apl, window=1)
                    # Drop any attacker removed during the window.
                    attackers = [a for a in attackers
                                 if a in gs.zones.battlefield]
                elif hasattr(opp_apl, 'post_attackers_instant'):
                    # Legacy shallow hook (gate OFF, byte-identical baseline).
                    _tap_for_response(opp_gs)
                    opp_apl.post_attackers_instant(opp_gs, gs, attackers)
                    # Remove killed attackers from the list
                    attackers = [a for a in attackers
                                 if a in gs.zones.battlefield]

                # Defender declares blockers
                blocker_assignments = opp_apl.declare_blockers(
                    opp_gs, gs, attackers)

                # --- WINDOW 2: after blockers declared, before combat damage ---
                if gate_on:
                    # R2 (design 1.3): canonical combat-trick window. Active
                    # player gets priority first (pump a blocked attacker via
                    # the PUMP primitive -> counters, read by resolve_combat at
                    # damage time); defender may respond; LIFO resolve.
                    _tap_for_response(gs)
                    _tap_for_response(opp_gs)
                    _run_combat_window(gs, apl, opp_gs, opp_apl, window=2)
                    # A removal response could have killed an attacker mid-window.
                    attackers = [a for a in attackers
                                 if a in gs.zones.battlefield]
                elif hasattr(apl, 'combat_trick'):
                    # Legacy shallow hook (gate OFF, byte-identical baseline).
                    apl.combat_trick(gs, opp_gs, attackers, blocker_assignments)

                # Resolve combat with keywords
                combat_result = resolve_combat(
                    attackers, blocker_assignments, active, mgs)

                # Lifelink happens at the same time as the damage, so the
                # defender's gain goes in BEFORE deal_damage decides lethal.
                if combat_result.life_gained_defender > 0:
                    mgs.gain_life(opp_player, combat_result.life_gained_defender)

                # Apply damage to defending player
                mgs.deal_damage(active, combat_result.damage_to_defender)

                # Apply lifelink
                if combat_result.life_gained_attacker > 0:
                    mgs.gain_life(active, combat_result.life_gained_attacker)

                # Remove dead creatures
                for dead in combat_result.attacker_deaths:
                    if dead in gs.zones.battlefield:
                        gs.zones.battlefield.remove(dead)
                        gs.zones.graveyard.append(dead)
                for dead in combat_result.defender_deaths:
                    if dead in opp_gs.zones.battlefield:
                        opp_gs.zones.battlefield.remove(dead)
                        opp_gs.zones.graveyard.append(dead)

            # Prowess bonus is end-of-turn; strip before next phase so
            # the counter stacking stays consistent across turns.
            for card, bonus in prowess_boosted:
                card.counters -= bonus

            # --- CHECK WIN ---
            # deal_damage already labelled combat kills; check_life catches
            # combat-window burn and life lost to attack triggers.
            if mgs.check_life('noncombat'):
                result = mgs.to_match_result()
                result.mulligans_a = mull_a
                result.mulligans_b = mull_b
                result.hand_a = hand_a_names
                result.hand_b = hand_b_names
                result._on_play = on_play
                return result

            # --- END STEP ---
            _tap_for_response(opp_gs)   # opponent can tap for end-step instants/flash
            opp_apl.end_step_actions(opp_gs, gs)
            if mgs.check_life('noncombat'):
                return _finish()

            # Cleanup: remove temporary effects, discard to 7
            if len(gs.zones.hand) > 7:
                # Discard worst cards
                excess = len(gs.zones.hand) - 7
                discards = sorted(gs.zones.hand,
                                  key=lambda c: getattr(c, 'cmc', 0))[:excess]
                for d in discards:
                    gs.zones.hand.remove(d)
                    gs.zones.graveyard.append(d)

    # --- TIMEOUT --- (R6 gated: inevitability tiebreaker when a seat opts in; legacy on tie/off)
    if getattr(apl_a, "WANTS_HIDDEN_INFO", False) or getattr(apl_b, "WANTS_HIDDEN_INFO", False):
        from engine.match_runner import _inevitability_score as _inev
        _sa = _inev(mgs.gs_a.life, mgs.gs_a.zones.hand, mgs.gs_a.zones.battlefield, mgs.gs_b.zones.battlefield)
        _sb = _inev(mgs.gs_b.life, mgs.gs_b.zones.hand, mgs.gs_b.zones.battlefield, mgs.gs_a.zones.battlefield)
        if _sa != _sb:
            mgs.winner = 'a' if _sa > _sb else 'b'
    if mgs.winner is None and mgs.gs_a.life != mgs.gs_b.life:
        mgs.winner = 'a' if mgs.gs_b.life < mgs.gs_a.life else 'b'
    mgs.win_method = 'timeout'
    if mgs.winner is None:
        # Dead-even stall (#29). Used to go to B every time, which read as a
        # 0% mirror. Seeded coin flip keeps it unbiased and reproducible.
        # ponytail: coin flip, not a draw bucket; add winner='draw' handling
        # through the Bo3/gauntlet consumers if stalls need their own column.
        mgs.winner = mgs.rng.choice(['a', 'b'])
        mgs.win_method = 'timeout_tie'
    result = mgs.to_match_result()
    result.mulligans_a = mull_a
    result.mulligans_b = mull_b
    result.hand_a = hand_a_names
    result.hand_b = hand_b_names
    result._on_play = on_play
    return result


def run_match_set(apl_a: MatchAPL, deck_a: list,
                  apl_b: MatchAPL, deck_b: list,
                  n: int = 1000,
                  mix_play_draw: bool = True,
                  seed: int = 42) -> MatchSetResults:
    """
    Run N matches between two MatchAPLs. Returns aggregated results.
    mix_play_draw=True alternates who is on the play each game.
    """
    results = MatchSetResults(n_games=n)
    rng = random.Random(seed)

    for i in range(n):
        game_on_play = (i % 2 == 0) if mix_play_draw else True
        game_seed = rng.randint(0, 999_999)

        match = run_match(
            apl_a, deck_a, apl_b, deck_b,
            on_play=game_on_play, seed=game_seed
        )

        if match.winner == 'a':
            results.a_wins += 1
        else:
            results.b_wins += 1
        if match.win_method.endswith('_tie'):
            results.ties += 1
        results.kill_turns.append(match.kill_turn)
        results.results.append(match)

    total_turns = sum(results.kill_turns)
    results.avg_turns = total_turns / n if n else 0
    return results


def print_match_report(results: MatchSetResults,
                       name_a: str = "Deck A",
                       name_b: str = "Deck B"):
    """Print a formatted matchup report."""
    print(f"\n{'='*50}")
    print(f"  MATCHUP: {name_a} vs {name_b}")
    print(f"  {results.n_games} games")
    print(f"{'='*50}")
    print(f"  {name_a}: {results.win_pct_a()}% win rate "
          f"({results.a_wins}-{results.b_wins})")
    if results.ties:
        print(f"  Ties (coin flip): {results.ties}")
    print(f"  Avg game length: {results.avg_turns:.1f} turns")
    pd = results.play_draw_split()
    print(f"  On play: {pd['on_play']}% | On draw: {pd['on_draw']}%")
    print(f"\n  Kill turn distribution:")
    for turn, pct in sorted(results.kill_turn_distribution().items()):
        bar = '#' * int(pct / 2)
        print(f"    T{turn:2d}: {pct:5.1f}% {bar}")
    print()
