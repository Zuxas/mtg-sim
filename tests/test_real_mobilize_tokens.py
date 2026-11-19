"""Voice of Victory's Mobilize 2 makes real Warrior tokens.

"Whenever this creature attacks, create two tapped and attacking 1/1 red
Warrior creature tokens. Sacrifice them at the beginning of the next end step."

The match APL only counted them: they never attacked, could not be blocked or
die, and Goblin Bombardment was paid for them a turn late, at the opponent's
end step, whether or not they would still have been alive.

Run: python tests/test_real_mobilize_tokens.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from engine import match_engine
from apl.boros_energy_match import BorosEnergyMatchAPL

DECK, _ = load_deck_from_file("decks/boros_energy_modern.txt")


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def _attack(board):
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 3
    for name in board:
        c = _card(name)
        c.summoning_sickness = False
        gs.zones.battlefield.append(c)
    apl = BorosEnergyMatchAPL()
    attackers = apl.declare_attackers(gs, opp)
    return apl, gs, opp, attackers


def _warriors(cards):
    return [c for c in cards if c.name == "Warrior Token"]


def test_two_tapped_attacking_warriors_per_voice():
    _, gs, _, attackers = _attack(["Voice of Victory"])
    on_board = _warriors(gs.zones.battlefield)
    assert len(on_board) == 2 and all(w.tapped for w in on_board)
    assert len(_warriors(attackers)) == 2, "the Warriors are attacking"
    assert all(str(w.power) == "1" for w in on_board)


def test_guide_of_souls_triggers_once_per_warrior():
    apl, gs, _, _ = _attack(["Voice of Victory", "Guide of Souls"])
    assert gs.life == 22 and gs.energy == 2
    assert apl._gained_life_this_turn


def test_sacrificed_at_our_own_end_step():
    apl, gs, opp, _ = _attack(["Voice of Victory"])
    apl.own_end_step(gs, opp)
    assert not _warriors(gs.zones.battlefield)
    assert gs.damage_dealt == 0, "no Bombardment, no damage"


def test_bombardment_gets_one_damage_per_living_warrior():
    apl, gs, opp, _ = _attack(["Voice of Victory", "Goblin Bombardment"])
    dead = _warriors(gs.zones.battlefield)[0]
    gs.zones.battlefield.remove(dead)          # one Warrior died in combat
    apl.own_end_step(gs, opp)
    assert not _warriors(gs.zones.battlefield)
    assert gs.damage_dealt == 1, "only the Warrior still alive can be sacrificed"


def test_opponents_end_step_pays_no_mobilize_damage():
    apl, gs, opp, _ = _attack(["Voice of Victory", "Goblin Bombardment"])
    apl.own_end_step(gs, opp)
    after_own = gs.damage_dealt
    apl.end_step_actions(gs, opp)              # the opponent's end step, later
    assert gs.damage_dealt == after_own == 2


def test_no_warrior_outlives_the_turn_in_a_real_game():
    class Watch(BorosEnergyMatchAPL):
        made = 0

        def declare_attackers(self, gs, opponent):
            out = super().declare_attackers(gs, opponent)
            Watch.made += len(_warriors(out))
            return out

        def end_step_actions(self, gs, opponent):     # opponent's end step
            assert not _warriors(gs.zones.battlefield), "a Warrior survived our turn"
            return super().end_step_actions(gs, opponent)

    for seed in range(40):
        match_engine.run_match(Watch(), DECK, Watch(), DECK, seed=seed)
    assert Watch.made > 0, "no Voice of Victory ever attacked in 40 games"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_real_mobilize_tokens: OK")
