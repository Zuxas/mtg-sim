"""
apl/death_and_taxes_match.py -- Death and Taxes (Modern), post-ban archetype.

Mono-White Aether Vial hatebears: Thalia / Leonin Arbiter / Mother of Runes
tax-and-disrupt shell whose post-ban (May 2026) payoff is the unbanned
Umezawa's Jitte plus Skyclave Apparition / Solitude removal. Plays a grindy
creature-aggro game backed by Swords to Plowshares and Ghost Quarter
manabase attacks.

SYNTHETIC-MATCHUP CAVEAT
------------------------
This MatchAPL is a STUB. It does NOT model the deck's real edges -- Aether
Vial flash-ins, Leonin Arbiter / Ghost Quarter mana denial, Mother-of-Runes
protection, or Jitte counter accrual. It plays Death and Taxes as a generic
white creature-aggro deck via the standard match-runner path: curve out cheap
creatures, hold up nothing, and let the engine resolve combat + removal. Any
gauntlet number produced against this opponent is therefore a STUB/SYNTHETIC
result that fills the post-ban Modern field row so gauntlets RUN -- it is NOT
a primer-validated matchup. Promote to a real APL before trusting its cells.
(Pattern mirrors the RETIRED 2026-06-29 broodscale synthetic stub; that file
is now a real combo APL -- see decks/archive/gruul_broodscale_modern_synthetic_stub_2026-06-29.txt.)
"""
from apl.match_apl import MatchAPL


class DeathAndTaxesMatchAPL(MatchAPL):
    name = "Death and Taxes"
    ARCHETYPE = "aggro"
    win_condition_damage = 20
    max_turns = 15

    # White hatebears want their bodies attacking; the base lethal/trade
    # heuristics handle when to hold back.
    ATTACK_ALL_IN = False

    def keep(self, hand, mulligans, on_play):
        """Want 2-4 lands plus action. An Aether Vial in hand counts as
        half a land for development purposes. Loosen as mulligans pile up."""
        lands = sum(1 for c in hand if c.is_land())
        vial = any(c.name == "Aether Vial" for c in hand)
        if mulligans >= 2:
            return lands >= 1
        if lands <= 1:
            return lands == 1 and vial
        return 2 <= lands <= 5

    def bottom(self, hand, n):
        """Bottom surplus lands first, then the highest-CMC spells."""
        lands = [c for c in hand if c.is_land()]
        nonlands = sorted((c for c in hand if not c.is_land()),
                          key=lambda c: -getattr(c, "cmc", 0))
        pool = lands[3:] + nonlands
        return pool[:n]

    def main_phase(self, gs):
        # Goldfish entrypoint -- no opponent awareness.
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        """Spot removal if relevant, drop a land, then deploy creatures /
        equipment cheapest-first."""
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        self._match_cast_removal(gs, opponent)
        self._play_land_if_able(gs)
        self._cast_all_castable(gs)
