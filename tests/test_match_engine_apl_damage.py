"""match_engine must apply noncombat damage however the APL or handler wrote it.

Three styles exist in the codebase:
  1. goldfish style:  gs.damage_dealt += n          (17 match APLs, 23 handlers)
  2. match style:     opponent.life -= n
  3. both at once:    the shared burn helpers, deal_damage()
match_engine only ever honoured 2 and 3, so style-1 damage vanished.

Run: python tests/test_match_engine_apl_damage.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from apl.match_apl import GenericMatchAPL
from engine import match_engine
from engine.match_state import MatchGameState


def _lands(n=60):
    out = []
    for _ in range(n):
        c = Card(name="Mountain", mana_cost="", cmc=0.0, type_line="Basic Land - Mountain")
        c.tags = {Tag.LAND}
        out.append(c)
    return out


class _Burn(GenericMatchAPL):
    """Deals 5 to the face every main phase, written in the given style."""
    style = "goldfish"

    def keep(self, hand, mulligans=0, on_play=True):
        return True

    def main_phase_match(self, gs, opponent):
        if self.style in ("goldfish", "both"):
            gs.damage_dealt += 5
        if self.style in ("match", "both"):
            opponent.life -= 5


def _kill_turn(style):
    apl = _Burn()
    apl.style = style
    r = match_engine.run_match(apl, _lands(), GenericMatchAPL(), _lands(), on_play=True, seed=1)
    return r.winner, r.kill_turn, r.final_life_b, r.win_method


def test_goldfish_style_damage_reaches_life():
    assert _kill_turn("goldfish") == ("a", 4, 0, "noncombat")


def test_match_style_damage_unchanged():
    assert _kill_turn("match") == ("a", 4, 0, "noncombat")


def test_damage_written_to_both_channels_counts_once():
    assert _kill_turn("both") == ("a", 4, 0, "noncombat")


def test_combat_damage_counts_once():
    mgs = MatchGameState(_lands(), _lands(), seed=1)
    mgs.deal_damage('a', 3)
    mgs.settle_damage()
    assert mgs.gs_b.life == 17 and mgs.gs_a.damage_dealt == 3


def test_mixed_events_in_one_window():
    mgs = MatchGameState(_lands(), _lands(), seed=1)
    a, b = mgs.gs_a, mgs.gs_b
    a.damage_dealt += 3                       # goldfish style: owed
    a.damage_dealt += 2; b.life -= 2          # both channels: already landed
    b.life -= 4                               # match style: already landed
    b.life += 3                               # opponent gains life: not ours
    mgs.settle_damage()
    assert b.life == 20 - 3 - 2 - 4 + 3
    mgs.settle_damage()                       # settling twice applies nothing new
    assert b.life == 14


def test_damage_then_equal_lifegain_nets_to_zero():
    mgs = MatchGameState(_lands(), _lands(), seed=1)
    a, b = mgs.gs_a, mgs.gs_b
    a.damage_dealt += 3
    b.life += 3
    mgs.settle_damage()
    assert b.life == 20 and a.damage_dealt == 3


def test_paired_then_unpaired_then_lifegain():
    mgs = MatchGameState(_lands(), _lands(), seed=1)
    a, b = mgs.gs_a, mgs.gs_b
    a.damage_dealt += 3; b.life -= 3          # Bolt through a dual-write helper
    a.damage_dealt += 3                       # Bombardment, goldfish style
    b.life += 3                               # opponent gains 3
    mgs.settle_damage()
    assert b.life == 20 - 3 - 3 + 3 and a.damage_dealt == 6


def test_opponents_own_life_payment_is_not_doubled():
    mgs = MatchGameState(_lands(), _lands(), seed=1)
    mgs.gs_b.life -= 2                        # shock land
    mgs.settle_damage()
    assert mgs.gs_b.life == 18


def test_known_ceiling_equal_unrelated_events_are_read_as_one():
    """Documents the bridge's limit rather than a wanted behaviour: a
    goldfish-style bump of 2 right before the opponent's own 2-life payment
    is indistinguishable from one dual-channel write, so the bump is dropped.
    This test should start failing, and be deleted, when damage goes through
    one deal_damage() call."""
    mgs = MatchGameState(_lands(), _lands(), seed=1)
    mgs.gs_a.damage_dealt += 2                # A pings for 2, goldfish style
    mgs.gs_b.life -= 2                        # B's own shock land
    mgs.settle_damage()
    assert mgs.gs_b.life == 18                # truth would be 16


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_match_engine_apl_damage: OK")
