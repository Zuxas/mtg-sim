"""
apl/temur_crashcade_match.py -- Temur Crashcade (Modern), post-ban archetype.

Cascade-tempo deck re-enabled by the May-2026 unban of Violent Outburst:
cast a turn-2/3 cascade spell (Violent Outburst / Shardless Agent) to flip
Crashing Footfalls for two 4/4 trampling Rhinos, then protect the board with
free interaction (Force of Negation / Fury / Subtlety / Endurance) and grind
with Temur value (Tireless Tracker, Wrenn and Six).

SYNTHETIC-MATCHUP CAVEAT
------------------------
This MatchAPL is a STUB. It does NOT model cascade resolution, the
Crashing-Footfalls suspend flip, or pitch/evoke free spells. It plays the
deck as a generic tempo creature deck via the standard match-runner path:
develop lands, cast castable threats cheapest-first, swing. Any gauntlet
number produced against this opponent is therefore a STUB/SYNTHETIC result
that fills the post-ban Modern field row so gauntlets RUN -- it is NOT a
primer-validated matchup. Promote to a real APL before trusting its cells.
(Pattern mirrors apl/gruul_broodscale_match.py.)
"""
from apl.match_apl import MatchAPL


class TemurCrashcadeMatchAPL(MatchAPL):
    name = "Temur Crashcade"
    ARCHETYPE = "tempo"
    win_condition_damage = 20
    max_turns = 15

    ATTACK_ALL_IN = False

    def keep(self, hand, mulligans, on_play):
        """Want 2-4 lands plus a cascade enabler or threat. Loosen with
        mulligans."""
        lands = sum(1 for c in hand if c.is_land())
        enablers = sum(1 for c in hand
                       if c.name in ("Violent Outburst", "Shardless Agent"))
        if mulligans >= 2:
            return lands >= 1
        if lands <= 1:
            return lands == 1 and enablers >= 1
        return 2 <= lands <= 5

    def bottom(self, hand, n):
        """Bottom surplus lands first, then highest-CMC spells -- but keep
        Crashing Footfalls and cascade enablers."""
        keep_names = {"Crashing Footfalls", "Violent Outburst",
                      "Shardless Agent"}
        lands = [c for c in hand if c.is_land()]
        nonlands = sorted(
            (c for c in hand if not c.is_land() and c.name not in keep_names),
            key=lambda c: -getattr(c, "cmc", 0))
        pool = lands[3:] + nonlands
        return pool[:n]

    def main_phase(self, gs):
        # Goldfish entrypoint -- no opponent awareness.
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        self._match_cast_removal(gs, opponent)
        self._play_land_if_able(gs)
        self._cast_all_castable(gs)
