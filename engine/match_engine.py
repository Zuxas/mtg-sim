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
from apl.match_apl import MatchAPL, GoldfishAdapter
from apl.mulligan import take_opening_hand
from data.card import Card


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


def run_match(apl_a: MatchAPL, deck_a: list,
              apl_b: MatchAPL, deck_b: list,
              on_play: bool = True,
              max_turns: int = 15,
              seed: int = None) -> MatchResult:
    """
    Run a single match between two MatchAPLs.
    Returns MatchResult with winner, kill turn, and game data.
    """
    mgs = MatchGameState(deck_a, deck_b, on_play=on_play, seed=seed)

    # --- Mulligan phase ---
    mull_a = _do_mulligan(apl_a, mgs.gs_a, mgs.rng)
    mull_b = _do_mulligan(apl_b, mgs.gs_b, mgs.rng)

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

            # Tap lands for mana
            gs.tap_lands()

            # --- MAIN PHASE 1 ---
            apl.main_phase_match(gs, opp_gs)

            # --- COMBAT ---
            attackers = apl.declare_attackers(gs, opp_gs)
            if attackers:
                # Defender declares blockers
                blocker_assignments = opp_apl.declare_blockers(
                    opp_gs, gs, attackers)

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

            # --- CHECK WIN ---
            if mgs.game_over:
                result = mgs.to_match_result()
                result.mulligans_a = mull_a
                result.mulligans_b = mull_b
                result._on_play = on_play
                return result

            # --- END STEP ---
            # Opponent can act at end of active player's turn
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
