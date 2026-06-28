#!/usr/bin/env python3
"""R6 hidden-information (card-advantage / inevitability) -- Increment 1 proof.

Phase 1 = the gated TIMEOUT inevitability tiebreaker. Proves the zero-RNG inevitability
score makes a card-advantage seat that is BEHIND on life WIN the timeout (vs the legacy
life-only verdict that would lose it), that the recurring-engine term is load-bearing (not
raw hand size), and that the gate is OFF (legacy path) for non-opted-in seats.

OUT OF SCOPE here (Phase 2, deferred): the mid-game inevitability concession and the
Izzet-Lessons-vs-Selesnya de-inversion. Increment 1 is scaffold + Phase 1 only. ASCII-only.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.match_runner as mr
from data.card import Card


def _bolt():
    return Card("Lightning Bolt", mana_cost="{R}", cmc=1, type_line="Instant")


def _engine():
    return Card("Monument to Endurance", mana_cost=None, cmc=3, type_line="Enchantment")


def test1_inevitability_tiebreaker():
    # Seat A: BEHIND on life (8 < 12) but ahead on hand (7 vs 2) + a recurring engine.
    sa = mr._inevitability_score(8,  [_bolt() for _ in range(7)], [_engine()], [])
    sb = mr._inevitability_score(12, [_bolt() for _ in range(2)], [], [])
    # GREEN (gated): the card-advantage seat A wins the timeout.
    assert sa > sb, "FAIL: card-advantage seat should outscore (%.1f !> %.1f)" % (sa, sb)
    # RED (legacy life-only, result.won = life_b < life_a): A would LOSE (8 < 12 is False).
    legacy_a_wins = (8 > 12)      # legacy gives A the win only if A's life is higher
    gated_a_wins = (sa > sb)
    assert legacy_a_wins is False, "setup: legacy must pick B"
    assert gated_a_wins != legacy_a_wins, "FAIL: gated verdict must DIFFER from legacy"
    print("R6_TEST1 PASS: gated tiebreaker flips A (card-rich, life 8) to WIN; "
          "legacy life-only loses it. sa=%.1f sb=%.1f" % (sa, sb))


def test2_gate_off_is_legacy():
    class _D:
        pass
    g = _D(); g.apl_a = _D(); g.apl_b = _D()   # neither sets WANTS_HIDDEN_INFO
    assert mr._hidden_info_match_gate(g) is False, "FAIL: gate must be OFF for non-opt-in"
    # zero-RNG, pure-count sanity: empty board/hand -> score == life.
    assert mr._inevitability_score(20, [], [], []) == 20.0
    print("R6_TEST2 PASS: gate OFF for non-opted-in seats -> legacy timeout path (byte-identical).")


def test3_recurring_engine_load_bearing():
    # A recurring engine must outweigh a couple extra DEAD cards (engine w=5 > hand w=2).
    flood  = mr._inevitability_score(10, [_bolt() for _ in range(4)], [], [])              # 10 + 8
    engine = mr._inevitability_score(10, [_bolt() for _ in range(2)], [_engine()], [])     # 10 + 4 + 5
    assert engine > flood, "FAIL: recurring engine should outweigh 2 extra dead cards (%.1f !> %.1f)" % (engine, flood)
    print("R6_TEST3 PASS: recurring-engine count is load-bearing (engine %.1f > flood %.1f)." % (engine, flood))


if __name__ == "__main__":
    test1_inevitability_tiebreaker()
    test2_gate_off_is_legacy()
    test3_recurring_engine_load_bearing()
    print("ALL R6 PROOF TESTS PASS")
    sys.exit(0)
