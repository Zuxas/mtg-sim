"""
apl/gruul_broodscale_match.py -- Gruul Broodscale Combo (Modern)

Basking Broodscale combo deck: a fast aggro-combo backbone that ramps on
turn 1 with mana dorks, deploys Basking Broodscale + Glaring Fleshraker, and
grows a +1/+1-counter / Eldrazi-Spawn token board (Grumgully payoff). The
real-world plan kills ~T3-5 via the Broodscale counter loop.

SYNTHETIC-MATCHUP CAVEAT
------------------------
This MatchAPL does NOT model the infinite Broodscale loop. It plays the deck
as an aggressive creature deck via the standard match-runner path: ramp on a
dork, dump creatures cheapest-first, and let the engine's combat resolve. Any
gauntlet win rate produced against this opponent is therefore a STUB/SYNTHETIC
number -- it fills the Low Curve field row so the gauntlet runs, but it is NOT
a primer-validated matchup result. Primer reference: 2-2 record, ~55% vs field.

We deliberately did NOT reuse engine.match_runner.ComboKillSampler: the gauntlet
calls the singular match_runner.run_match (full_field_gauntlet._run_matchup_job),
which never routes through the sampler (that path lives only in run_match_set /
_run_single_match). A sampler-backed stub would just play as a plain MatchAPL in
the gauntlet, so a real creature MatchAPL is both lower-risk and the only
actually-functional choice for this path.
"""
from apl.match_apl import MatchAPL
from data.card import Tag


class GruulBroodscaleMatchAPL(MatchAPL):
    name = "Gruul Broodscale"
    ARCHETYPE = "combo"
    win_condition_damage = 20
    max_turns = 15

    # Leave ATTACK_ALL_IN False: the base declare_attackers heuristic holds
    # mana dorks back instead of throwing Llanowar/Mystic/Birds into combat to
    # die, which models a dork-fueled creature-combo deck more plausibly.
    ATTACK_ALL_IN = False

    def keep(self, hand, mulligans, on_play):
        """Want a curve-out: 2-4 lands (a mana dork counts toward enabling
        green) plus action. Loosen as mulligans accumulate."""
        lands = sum(1 for c in hand if c.is_land())
        dorks = sum(1 for c in hand
                    if c.name in ("Llanowar Elves", "Elvish Mystic",
                                  "Birds of Paradise"))
        sources = lands + dorks
        if mulligans >= 2:
            return sources >= 1
        if lands == 0:
            # A 1-land hand is keepable only with a dork to fix the second land.
            return dorks >= 1 and sources >= 2
        return 2 <= sources <= 5

    def bottom(self, hand, n):
        """Bottom surplus lands first, then highest-CMC cards."""
        lands = [c for c in hand if c.is_land()]
        nonlands = sorted((c for c in hand if not c.is_land()),
                          key=lambda c: -getattr(c, "cmc", 0))
        # Keep ~3 lands; bottom the rest of the lands first, then fat.
        pool = lands[3:] + nonlands
        return pool[:n]

    def main_phase(self, gs):
        # Goldfish entrypoint -- no opponent awareness.
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        """Ramp + deploy: play a land, then cast everything castable
        cheapest-first (mana dorks come down first by CMC, enabling the
        combo creatures and payoffs the same/next turn)."""
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        # Spot removal first if we drew burn and they have a threat.
        self._match_cast_removal(gs, opponent)
        self._play_land_if_able(gs)
        self._cast_all_castable(gs)
