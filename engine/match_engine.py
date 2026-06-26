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
from apl.match_apl import MatchAPL, GoldfishAdapter
from apl.mulligan import take_opening_hand
from data.card import Card, Tag


def _do_mulligan(apl: MatchAPL, gs: GameState, rng: random.Random) -> int:
    """Run London mulligan for one player. Returns number of mulligans."""
    mulligans = 0
    hand_size = 7
    # Draw opening hand
    for _ in range(hand_size):
        if gs.zones.library:
            gs.zones.hand.append(gs.zones.library.pop(0))

    for attempt in range(3):
        if apl.keep(gs.zones.hand, mulligans, gs.on_play):
            # Bottom cards if mulliganed
            if mulligans > 0:
                to_bottom = apl.bottom(gs.zones.hand, mulligans)
                for card in to_bottom:
                    if card in gs.zones.hand:
                        gs.zones.hand.remove(card)
                        gs.zones.library.append(card)
            break
        else:
            # Shuffle hand back, draw fewer
            gs.zones.library.extend(gs.zones.hand)
            gs.zones.hand = []
            rng.shuffle(gs.zones.library)
            mulligans += 1
            for _ in range(7 - mulligans):
                if gs.zones.library:
                    gs.zones.hand.append(gs.zones.library.pop(0))

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
            gs.mana_pool.add_land(land.type_line, land.name)


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
        if itype != InteractionType.NONE and (c.has(Tag.INSTANT) or c.has(Tag.SORCERY)):
            # Check if we have mana to cast it
            if hasattr(c, 'cmc') and c.cmc <= reactive_gs.mana_pool.total():
                interaction_cards.append((c, itype))
    
    if not interaction_cards:
        return
    
    # Ask the APL which interaction to use
    response = reactive_apl.respond_to_spell(reactive_gs, active_gs, None)
    if response and response in reactive_gs.zones.hand:
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
        if reactive_gs.mana_pool.can_cast(response.mana_cost, response.cmc):
            reactive_gs.mana_pool.pay(response.mana_cost, response.cmc)
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


def run_match(apl_a: MatchAPL, deck_a: list,
              apl_b: MatchAPL, deck_b: list,
              on_play: bool = True,
              max_turns: int = 15,
              seed: int = None) -> MatchResult:
    """
    Run a single match between two MatchAPLs.
    Returns MatchResult with winner, kill turn, and game data.
    """
    # Shallow-copy each Card so per-game mutations (power changes, tapped,
    # summoning_sickness, counters) don't leak into subsequent games when
    # the same deck list is reused across run_match_set iterations.
    import copy as _copy
    deck_a = [_copy.copy(c) for c in deck_a]
    deck_b = [_copy.copy(c) for c in deck_b]

    mgs = MatchGameState(deck_a, deck_b, on_play=on_play, seed=seed)

    # Wire opponent archetype keys so each APL's threat model is accurate.
    try:
        from sim_bridge import _infer_archetype_key as _iak
        apl_a._opp_key = _iak(getattr(apl_b, 'name', '') or '')
        apl_b._opp_key = _iak(getattr(apl_a, 'name', '') or '')
    except Exception:
        pass

    # Clear per-match state so reused APL objects don't leak game state
    # across matches (stale _opp_gs, plotted cards, damage counters, etc.)
    for _apl in (apl_a, apl_b):
        _apl._opp_gs  = None
        _apl._my_gs   = None
        _apl._match_dmg = 0
        # Clear Plot exile zone if present
        _plotted_attr = getattr(_apl, 'PLOTTED_ZONE', None)
        if _plotted_attr and hasattr(_apl, _plotted_attr):
            setattr(_apl, _plotted_attr, [])

    # --- Mulligan phase ---
    mull_a = _do_mulligan(apl_a, mgs.gs_a, mgs.rng)
    mull_b = _do_mulligan(apl_b, mgs.gs_b, mgs.rng)

    # Snapshot kept opening hands (card names) for downstream aggregation.
    hand_a_names = [c.name for c in mgs.gs_a.zones.hand]
    hand_b_names = [c.name for c in mgs.gs_b.zones.hand]

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
            # NOTE: In real MTG, mana empties at the cleanup step. We intentionally
            # do NOT reset the mana pool here because tap_lands() auto-taps ALL
            # lands unconditionally — there's no concept of "hold up mana" for
            # instant-speed interaction. If we reset here, neither player has mana
            # in any response window, eliminating all interaction. The accumulation
            # serves as a rough proxy for held-up mana until per-land tap control
            # is implemented. Known limitation: players can interact across multiple
            # turns' worth of accumulated mana (slightly too much interaction).
            # TODO: implement selective land tapping per APL (COUNTER_COST reserve)
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
            if not skip_draw and gs.zones.library:
                gs.zones.hand.append(gs.zones.library.pop(0))

            # Let the APL declare how much mana to hold up before tapping.
            # AwareMatchAPL subclasses use this to leave interaction lands untapped.
            gs.mana_reserve = 0   # default: tap everything
            if hasattr(apl, 'reserve_mana'):
                apl.reserve_mana(gs, opp_gs)

            # Tap lands for mana (respects gs.mana_reserve)
            gs.tap_lands()

            # Check if Monument to Endurance drain during tap_lands() killed opponent
            if opp_gs.life <= 0 and not mgs.game_over:
                mgs.game_over = True
                mgs.winner    = active
                mgs.win_method = 'monument_drain'

            # --- MAIN PHASE 1 ---
            apl.main_phase_match(gs, opp_gs)

            # --- INTERACTION: Reactive player responds after main phase ---
            opp_player = 'b' if active == 'a' else 'a'
            spells_this_phase = max(1, gs.spells_cast_this_turn)
            _tap_for_response(opp_gs)   # opponent can tap lands to respond
            for _ in range(spells_this_phase):
                _try_reactive_interaction(opp_apl, opp_gs, gs, mgs, opp_player)
                if mgs.game_over:
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
                if mgs.game_over:
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
            if mgs.game_over:
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

            # Cleanup: remove temporary effects, discard to 7
            if len(gs.zones.hand) > 7:
                # Discard worst cards
                excess = len(gs.zones.hand) - 7
                discards = sorted(gs.zones.hand,
                                  key=lambda c: getattr(c, 'cmc', 0))[:excess]
                for d in discards:
                    gs.zones.hand.remove(d)
                    gs.zones.graveyard.append(d)

    # --- TIMEOUT ---
    mgs.winner = 'a' if mgs.gs_b.life < mgs.gs_a.life else 'b'
    mgs.win_method = 'timeout'
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
    print(f"  Avg game length: {results.avg_turns:.1f} turns")
    pd = results.play_draw_split()
    print(f"  On play: {pd['on_play']}% | On draw: {pd['on_draw']}%")
    print(f"\n  Kill turn distribution:")
    for turn, pct in sorted(results.kill_turn_distribution().items()):
        bar = '#' * int(pct / 2)
        print(f"    T{turn:2d}: {pct:5.1f}% {bar}")
    print()
