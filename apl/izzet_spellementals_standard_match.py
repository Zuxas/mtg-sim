"""
apl/izzet_spellementals_standard_match.py — Izzet Spellementals (Standard, PT SOS 2026)

Elemental synergy tempo/midrange. 8% of PT SOS field (26/325 players).
Key engine:
- Hearth Elemental (4x, not in oracle DB yet) — early Elemental
- Eddymurk Crab (4x) — cost-reduced by spell count, Elemental
- Colorstorm Stallion (2x) — {1}{U}{R} 3/3 haste, Opus (+1/+1 per spell)
- Sunderflock ({7}{U}{U}) — costs X less where X = greatest MV among Elementals
  With Eddymurk (CMC 7) on board: effective cost = {0}{U}{U} = 2 mana
- Flow State, Traumatic Critique, Prismari Charm — SOS cantrip/burn
"""
from apl.match_apl import MatchAPL
from apl.izzet_prowess_standard import (
    IzzetProwessAPL, COLORSTORM, FLOW_STATE,
    TRAUMATIC, PRISMARI_CHARM, IMPRACTICAL, BURST,
)

EDDYMURK    = "Eddymurk Crab"
SUNDERFLOCK = "Sunderflock"
HEARTH      = "Hearth Elemental"
WINTERNIGHT = "Winternight Stories"   # {2}{U}: draw 3, discard 2 (or 1 creature)
ELEMENTALS  = frozenset({EDDYMURK, HEARTH, COLORSTORM})


class IzzetSpellementalsStandardMatchAPL(MatchAPL, IzzetProwessAPL):
    name = "Izzet Spellementals"

    CREATURES = (
        HEARTH,
        COLORSTORM,
        EDDYMURK,
    )

    CANTRIP_SPELLS = (
        "Opt",
        "Sleight of Hand",
        FLOW_STATE,
        PRISMARI_CHARM,
        WINTERNIGHT,
    )

    BURN_SPELLS = {
        BURST:       (1, 2),
        IMPRACTICAL: (1, 3),
        TRAUMATIC:   (3, 3),
    }

    HASTE_CREATURES = frozenset({COLORSTORM})
    MULL_MIN_LANDS  = 2
    MULL_MAX_LANDS  = 4

    def main_phase_match(self, gs, opponent):
        elementals = [c for c in gs.zones.battlefield
                      if not c.is_land() and c.name in ELEMENTALS]
        max_mv = max((getattr(c, 'cmc', 0) for c in elementals), default=0)
        if max_mv:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, int(max_mv))
        self._opp_gs = opponent
        self._match_cast_removal(gs, opponent)
        self.main_phase(gs)
        # Sunderflock with Elemental discount
        for c in list(gs.zones.hand):
            if c.name == SUNDERFLOCK:
                effective = max(2, getattr(c, 'cmc', 9) - int(max_mv))
                gs.mana_pool.cost_reduction = int(max_mv)
                if gs.mana_pool.can_cast(c.mana_cost, effective):
                    gs.cast_spell(c)
                    gs._log(f"  Sunderflock: -{max_mv} discount -> {effective} eff cost")
                gs.mana_pool.cost_reduction = 0
                break

    ARCHETYPE = "tempo"
    SB_PLANS = {
        "aggro":   (["2 Eddymurk Crab", "2 Spell Pierce"],
                    ["2 Colorstorm Stallion", "2 Prismari Charm"]),
        "control": (["2 Spell Pierce", "2 Spell Snare"],
                    ["2 Winternight Stories"]),
        "combo":   (["3 Spell Pierce", "2 Soul-Guide Lantern"],
                    ["2 Colorstorm Stallion", "3 Winternight Stories"]),
        "ramp":    (["2 Spell Pierce"],
                    ["2 Winternight Stories"]),
        "tempo":   (["2 Spell Pierce", "2 Ral, Crackling Wit"],
                    ["2 Colorstorm Stallion", "2 Prismari Charm"]),
    }
