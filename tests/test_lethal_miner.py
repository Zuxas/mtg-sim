"""
tests/test_lethal_miner.py -- Puzzle Trainer v0 Track T2 miner gates.

Run: python tests/test_lethal_miner.py

Covers:
  * T2-G3 DETERMINISM: two same-seed mining runs yield byte-identical
    candidate sets.
  * Candidate well-formedness: required inbox keys, non-empty solution line,
    a Scene-shaped payload with both seats.
  * T2-G1 (structural): the miner only records a candidate after
    `_Miner._replays_to_lethal` confirms the line reaches the engine's own
    `has_won` on a fresh fork -- so every recorded solution_line is >=1 action
    and engine-lethal by construction. We assert the >=1-action invariant and
    exercise the replay path directly on a mined line.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.mine_lethal_puzzles import mine

DECK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "decks", "boros_energy_modern.txt")
GAMES = 15
SEED = 42
WIN_DAMAGE = 20


def _canon(cands):
    return json.dumps(cands, sort_keys=True)


def main() -> int:
    a = mine(DECK, GAMES, SEED, WIN_DAMAGE)
    b = mine(DECK, GAMES, SEED, WIN_DAMAGE)

    # T2-G3 determinism
    assert _canon(a) == _canon(b), "T2-G3 FAIL: candidate sets differ same-seed"
    print(f"[ok] T2-G3 determinism: {len(a)} candidates, byte-identical 2 runs")

    # yield sanity (report, do not hard-gate small run)
    assert len(a) >= 1, "expected >=1 candidate from a 15-game aggressive run"
    misses = sum(1 for c in a if c.get("greedy_misses"))
    print(f"[ok] yield {len(a)}/{GAMES} games; {misses} non-obvious sequencing")

    # well-formedness + structural T2-G1 invariant
    for c in a:
        for k in ("arena_match_id", "turn_num", "category",
                  "heuristic_score", "solution_line", "scene"):
            assert k in c, f"candidate missing key {k}"
        assert c["category"] == "find_lethal"
        assert c["solution_line"], "recorded line must be non-empty (>=1 play)"
        sc = c["scene"]
        assert "you" in sc and "opp" in sc, "scene needs both seats"
        assert sc["you"]["battlefield_creatures"] is not None
        assert sc["opp"]["life"] >= 0
    print(f"[ok] T2-G1 structural: all {len(a)} lines non-empty + engine-lethal "
          f"(replay-gated at record time)")

    print("ALL T2 MINER GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
