"""
apl/neobrand_match.py — Neobrand (Modern)

Combo: Summoner's Pact -> Allosaurus Shepherd T0, then Neoform (sac 1-drop
-> Griselbrand), draw 14, win. Or Eldritch Evolution path. Kill T1 on play
~30%, T2 ~50%. Critical failure mode: Summoner's Pact upkeep trigger if they
don't win — opponent can Consign to Memory to make them lose the game.

Kill distribution (from format_config.py): T1 30%, T2 50%, T3 20%.
As opponent: routed to ComboKillSampler via format_config 'combo' set.
"""
from apl.match_apl import MatchAPL
from data.card import Tag


PACT = "Summoner's Pact"
GRISELBRAND = "Griselbrand"
NEOFORM = "Neoform"


class NeobrandMatchAPL(MatchAPL):
    name = "Neobrand"
    win_condition_damage = 20
    max_turns = 4

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 3:
            return True
        has_pact = any(c.name == PACT for c in hand)
        has_neoform = any(c.name == NEOFORM for c in hand)
        has_combo = has_pact or has_neoform
        lands = sum(1 for c in hand if c.is_land())
        return (has_combo and lands >= 1) or mulligans >= 2

    def bottom(self, hand, n):
        excess = [c for c in hand if c.is_land()]
        other = [c for c in hand if not c.is_land()]
        return (excess[2:] + other)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        self._cast_all_castable(gs)

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent): pass
