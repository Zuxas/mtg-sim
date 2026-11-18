"""test_view_sync_and_mana.py -- issues #23 and #24 (match_runner phase views).

#23: life and damage changed inside the main-1 and end-step views were thrown
     away (free shocklands, main-1 burn that never landed).
#24: every view rebuilt a full mana pool from all lands, so mana spent in
     main 1 was back for main 2 and for the opponent's end step.

Stub APLs and hand-built cards: no card data needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from apl.match_apl import MatchAPL
from engine.match_runner import (TwoPlayerGameState, _simple_play_turn,
                                 _run_post_combat_phase, _run_end_step)


def _mountain():
    return Card(name="Mountain", mana_cost="", cmc=0,
                type_line="Basic Land - Mountain", oracle_text="", colors=[])


class Probe(MatchAPL):
    """Runs a callback per phase and records the mana it saw."""
    name = "probe"

    def __init__(self, main1=None, main2=None, end=None):
        self.cb = {"main1": main1, "main2": main2, "end": end}
        self.seen = {}

    def _run(self, phase, gs, opp):
        self.seen[phase] = gs.mana_pool.total()
        if self.cb[phase]:
            self.cb[phase](gs, opp)

    def keep(self, hand, mulligans=0, on_play=True): return True
    def bottom(self, hand, n): return hand[:n]
    def main_phase(self, gs): pass
    def main_phase_match(self, gs, opp): self._run("main1", gs, opp)
    def main_phase2_match(self, gs, opp): self._run("main2", gs, opp)
    def end_step_actions(self, gs, opp): self._run("end", gs, opp)
    def declare_attackers(self, gs, opp): return []
    def declare_blockers(self, gs, opp, attackers): return {}


def _gs(apl_a, apl_b, lands_a=3, lands_b=3):
    gs = TwoPlayerGameState([], [], on_play=True, seed=1)
    gs.turn = 4
    gs.apl_a, gs.apl_b = apl_a, apl_b
    gs.bf_a = [_mountain() for _ in range(lands_a)]
    gs.bf_b = [_mountain() for _ in range(lands_b)]
    return gs


def _spend(n):
    return lambda gs, opp: gs.mana_pool.pay("", n)


# ---- #24 ----------------------------------------------------------------

def test_mana_spent_in_main1_is_gone_in_main2_and_at_opp_end_step():
    a, b = Probe(main1=_spend(3)), Probe()
    gs = _gs(a, b)
    _simple_play_turn(gs, "a", a)
    _run_post_combat_phase(gs, "a", a)
    assert a.seen == {"main1": 3, "main2": 0}, a.seen
    # B's turn; A is the reactive player at B's end step, still tapped out
    _simple_play_turn(gs, "b", b)
    _run_end_step(gs, "b", "a", a)
    assert a.seen["end"] == 0, a.seen


def test_held_up_lands_are_exactly_what_is_available():
    a, b = Probe(main1=_spend(1)), Probe()
    gs = _gs(a, b)
    _simple_play_turn(gs, "a", a)
    _run_post_combat_phase(gs, "a", a)
    _simple_play_turn(gs, "b", b)
    _run_end_step(gs, "b", "a", a)
    assert a.seen == {"main1": 3, "main2": 2, "end": 2}, a.seen


def test_lands_untap_on_own_next_turn():
    a, b = Probe(main1=_spend(3)), Probe()
    gs = _gs(a, b)
    _simple_play_turn(gs, "a", a)
    _simple_play_turn(gs, "b", b)
    _simple_play_turn(gs, "a", a)
    assert a.seen["main1"] == 3, a.seen


# ---- #23 ----------------------------------------------------------------

def test_main1_life_payment_and_burn_reach_match_state():
    def main1(gs, opp):
        gs.life -= 2            # shockland
        gs.damage_dealt += 3    # Bolt, damage_dealt-only channel
    a = Probe(main1=main1)
    gs = _gs(a, Probe())
    _simple_play_turn(gs, "a", a)
    assert (gs.life_a, gs.life_b, gs.damage_to_b) == (18, 17, 3), (gs.life_a, gs.life_b, gs.damage_to_b)


def test_burn_through_both_channels_counts_once():
    def main1(gs, opp):         # what the shared burn primitive does
        gs.damage_dealt += 3
        opp.life -= 3
    a = Probe(main1=main1)
    gs = _gs(a, Probe())
    _simple_play_turn(gs, "a", a)
    assert gs.life_b == 17, gs.life_b


def test_life_only_drain_in_main1_counts():
    a = Probe(main1=lambda gs, opp: setattr(opp, "life", opp.life - 2))
    gs = _gs(a, Probe())
    _simple_play_turn(gs, "a", a)
    assert gs.life_b == 18, gs.life_b


def test_end_step_drain_and_lifegain_persist():
    def end(gs, opp):
        gs.life += 1
        opp.life -= 1
    a = Probe(end=end)
    gs = _gs(a, Probe())
    _run_end_step(gs, "b", "a", a)
    assert (gs.life_a, gs.life_b) == (21, 19), (gs.life_a, gs.life_b)


def test_main2_still_syncs():
    def main2(gs, opp):
        gs.damage_dealt += 3
        gs.life -= 1
    a = Probe(main2=main2)
    gs = _gs(a, Probe())
    _run_post_combat_phase(gs, "a", a)
    assert (gs.life_a, gs.life_b, gs.damage_to_b) == (19, 17, 3)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_view_sync_and_mana: OK")
