"""Issue #32: "at the beginning of your end step" triggers fire on YOUR turn.

BorosEnergyMatchAPL made Ocelot Pride's Cat inside end_step_actions, which both
engines call at the OPPONENT's end step. own_end_step is the active player's
hook; Ocelot Pride lives there now and nowhere else.

Run: python tests/test_own_end_step.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from data.deck import load_deck_from_file
from engine.game_state import GameState
from engine import match_engine, match_runner
from apl.boros_energy_match import BorosEnergyMatchAPL, OCELOT_PRIDE


def _cats(gs):
    return sum(1 for c in gs.zones.battlefield if c.name == "Cat Token")


def _board(gained_life):
    gs = GameState(mainboard=[], on_play=True)
    ocelot = Card(name=OCELOT_PRIDE, mana_cost="{W}", cmc=1.0, type_line="Creature - Cat")
    ocelot.tags = {Tag.CREATURE}
    gs.zones.battlefield.append(ocelot)
    apl = BorosEnergyMatchAPL()
    apl._gained_life_this_turn = gained_life
    return apl, gs


def test_ocelot_makes_its_cat_at_our_own_end_step():
    apl, gs = _board(gained_life=True)
    apl.own_end_step(gs, GameState(mainboard=[], on_play=False))
    assert _cats(gs) == 1


def test_no_cat_without_life_gain():
    apl, gs = _board(gained_life=False)
    apl.own_end_step(gs, GameState(mainboard=[], on_play=False))
    assert _cats(gs) == 0


def test_opponents_end_step_makes_no_cat():
    # The old home of the trigger. With the flag still set, it must not fire
    # again there (that would be a second Cat for one trigger).
    apl, gs = _board(gained_life=True)
    apl.end_step_actions(gs, GameState(mainboard=[], on_play=False))
    assert _cats(gs) == 0


def test_one_trigger_one_cat_across_both_end_steps():
    # Our end step, then the opponent's (where the old code lived): still 1.
    apl, gs = _board(gained_life=True)
    opp = GameState(mainboard=[], on_play=False)
    apl.own_end_step(gs, opp)
    assert _cats(gs) == 1
    apl.end_step_actions(gs, opp)
    assert _cats(gs) == 1


class _Spy(BorosEnergyMatchAPL):
    """Records the order the engine calls the turn hooks in."""

    def __init__(self):
        super().__init__()
        self.events = []
        self.cats_from_opp_end_step = 0

    def main_phase_match(self, gs, opponent):
        self.events.append("main")
        return super().main_phase_match(gs, opponent)

    def own_end_step(self, gs, opponent):
        self.events.append("own_end")
        return super().own_end_step(gs, opponent)

    def end_step_actions(self, gs, opponent):
        self.events.append("opp_end")
        before = _cats(gs)
        out = super().end_step_actions(gs, opponent)
        self.cats_from_opp_end_step += max(0, _cats(gs) - before)
        return out


def _check_engine(engine):
    deck, _ = load_deck_from_file("decks/boros_energy_modern.txt")
    for seed in range(5):
        a, b = _Spy(), _Spy()
        engine.run_match(a, deck, b, deck, seed=seed)
        for spy in (a, b):
            ev = spy.events
            assert "own_end" in ev, f"{engine.__name__}: own_end_step never called"
            for i, e in enumerate(ev):
                if e == "own_end":
                    # once per own turn: straight after our main phase, never
                    # twice in a row and never at the opponent's end step
                    prev = [x for x in ev[:i] if x != "opp_end"][-1:]
                    assert prev == ["main"], f"{engine.__name__}: {ev[:i + 1]}"
            assert spy.cats_from_opp_end_step == 0


def test_match_engine_calls_it_once_per_own_turn():
    _check_engine(match_engine)


def test_match_runner_calls_it_once_per_own_turn():
    _check_engine(match_runner)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_own_end_step: OK")
