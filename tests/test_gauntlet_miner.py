"""
tests/test_gauntlet_miner.py -- gates for scripts/mine_gauntlet_puzzles.py
(spec harness/specs/2026-09-29-gauntlet-lethal-puzzles.md).

Run: python tests/test_gauntlet_miner.py

Covers:
  * printed_haste: printed Haste counts; engine-only haste (Ragavan's dash
    reminder, Bloodghast's condition) does not.
  * G4 NO PERTURBATION: the same games with and without the mining hook give
    identical MatchResults.
  * G5 DETERMINISM: two same-seed runs -> byte-identical candidates.
  * G1 REPLAY / G2 NON-TRIVIAL / G3 REAL BOARD on every mined candidate: the
    line re-runs from a fresh fork of the saved position to a win, the empty
    line does not win, and the opponent has a nonland permanent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine import match_runner as mr
import scripts.mine_gauntlet_puzzles as gm

OPPS = ["Death and Taxes", "Dimir Midrange"]
GAMES = 120
SEED = 42


def _card(name, oracle, type_line="Creature"):
    return Card(name=name, mana_cost="", cmc=1, type_line=type_line, oracle_text=oracle)


def test_printed_haste():
    assert gm.printed_haste(_card("Goblin Guide", "Haste\nWhenever this creature attacks, ..."))
    assert gm.printed_haste(_card("Slickshot Show-Off", "Flying, haste\nWhenever you cast ..."))
    assert not gm.printed_haste(_card(
        "Ragavan, Nimble Pilferer",
        "Whenever Ragavan deals combat damage to a player, create a Treasure token.\n"
        "Dash {1}{R} (You may cast this spell for its dash cost. If you do, it gains "
        "haste, and it's returned from the battlefield to its owner's hand at the "
        "beginning of the next end step.)"))
    assert not gm.printed_haste(_card(
        "Bloodghast", "This creature can't block.\nThis creature has haste as long "
        "as an opponent has 10 or less life."))
    print("[ok] printed_haste separates printed Haste from engine-only haste")


def _root_replay(cand):
    """Re-play the recorded game up to the candidate's turn and re-check the
    line on a fresh fork (independent of the miner's own search)."""
    from generate_matchup_data import load_deck_and_apl
    from apl import get_match_apl
    _, opp, seed = cand["arena_match_id"].split(":", 1)[1].split("|")
    seed = int(seed)
    ours, _, _ = load_deck_and_apl(cand["our_deck"], "modern")
    theirs, _, _ = load_deck_and_apl(opp, "modern")
    on_play = ((seed - SEED) % 2 == 0)
    seen = {}

    def hooked(gs, player, apl, skip_draw, result, turn_num):
        if player == "a" and turn_num == cand["turn_num"] and "done" not in seen:
            seen["done"] = True
            m = gm.GauntletMiner(cand["our_deck"])
            m.new_game(opp, "x", on_play)
            seen["empty"] = m._turn(gs, [], skip_draw, turn_num)[0]
            won, pilot = m._turn(gs, cand["solution_line"], skip_draw, turn_num)
            seen["line"] = won and pilot.ok and not pilot.haste_suspect
        return gm._ORIG_TURN(gs, player, apl, skip_draw, result, turn_num)

    mr._run_player_turn = hooked
    try:
        mr.run_match(get_match_apl(cand["our_deck"]), ours, get_match_apl(opp),
                     theirs, on_play=on_play, seed=seed)
    finally:
        mr._run_player_turn = gm._ORIG_TURN
    return seen


def main() -> int:
    test_printed_haste()

    a, res_hook, _ = gm.mine("Boros Energy", "modern", GAMES, SEED, OPPS)
    b, _, _ = gm.mine("Boros Energy", "modern", GAMES, SEED, OPPS)
    _, res_plain, _ = gm.mine("Boros Energy", "modern", GAMES, SEED, OPPS, hook=False)
    assert mr._run_player_turn is gm._ORIG_TURN, "hook not uninstalled"

    assert res_hook == res_plain, "G4 FAIL: mining changed real game results"
    print(f"[ok] G4 no perturbation: {len(res_hook)} games identical with/without hook")

    canon = lambda cs: json.dumps(cs, sort_keys=True)  # noqa: E731
    assert canon(a) == canon(b), "G5 FAIL: same-seed candidate sets differ"
    print(f"[ok] G5 determinism: {len(a)} candidates byte-identical across 2 runs")

    assert a, "expected >=1 candidate from this run"
    for c in a:
        assert c["solution_line"], "G2 FAIL: empty line"
        opp = c["scene"]["opp"]
        assert opp["battlefield_creatures"] or opp["battlefield_other"], \
            "G3 FAIL: opponent has no nonland permanent"
        seen = _root_replay(c)
        assert seen.get("line") is True, f"G1 FAIL: line does not replay {c['arena_match_id']}"
        assert seen.get("empty") is False, f"G2 FAIL: empty line kills {c['arena_match_id']}"
    print(f"[ok] G1/G2/G3: all {len(a)} lines replay to a win from a fresh "
          f"re-played game; empty line never kills; opponent board present")

    print("ALL GAUNTLET MINER GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
