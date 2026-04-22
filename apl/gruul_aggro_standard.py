"""apl/gruul_aggro_standard.py -- Gruul Aggro APL (Standard)

Heartfire Hero + Monstrous Rage core with Slickshot Show-Off for
flying reach. Uses AggroAPL; archetype-specific twist is that the
preferred pump target is Heartfire Hero (its haste + Rage trigger
a quick kill).

Supersedes apl/gruul_aggro.py (the template) via the _standard
suffix convention.
"""
from apl.aggro_base import AggroAPL, _power_of
from engine.game_state import GameState
from engine.keywords import KWTag

# ── 1-drops ──────────────────────────────────────────────────────────
HEARTFIRE    = "Heartfire Hero"         # 1/1 haste, dies trigger
SLICKSHOT    = "Slickshot Show-Off"     # flying haste when 3+ damage dealt

# ── 2-drops ──────────────────────────────────────────────────────────
SWIFTSPEAR   = "Monastery Swiftspear"
EMBERHEART   = "Emberheart Challenger"
MANIFOLD     = "Manifold Mouse"

# ── 3-drops ──────────────────────────────────────────────────────────
QUESTING     = "Questing Druid"

# ── Burn / pump ─────────────────────────────────────────────────────
SHOCK        = "Shock"
RAGE         = "Monstrous Rage"
SNAKESKIN    = "Snakeskin Veil"         # +1/+1 + hexproof until EOT
TALENT       = "Innkeeper's Talent"     # enchantment, Level-up pump


class GruulAggroStandardAPL(AggroAPL):
    name = "Gruul Aggro"
    max_turns = 10

    CREATURES = (
        HEARTFIRE, SLICKSHOT,           # 1-drops
        SWIFTSPEAR, EMBERHEART, MANIFOLD,  # 2-drops
        QUESTING,                       # 3-drop
    )

    BURN_SPELLS = {
        SHOCK: (1, 2),                  # {R}: 2 dmg
    }

    PUMP_SPELLS = {
        RAGE:      (1, 2, True),        # {R}:  +2/+0 trample
        SNAKESKIN: (1, 1, False),       # {G}:  +1/+1 hexproof
    }

    HASTE_CREATURES = frozenset({HEARTFIRE, SLICKSHOT})

    # Aggro mulligan — wants 2-3 lands + heavy threats
    MULL_MIN_LANDS = 1
    MULL_MAX_LANDS = 4

    def _pick_pump_target(self, gs: GameState):
        """Prefer Heartfire Hero (1-mana haste, rage turns it into
        a 3/1 trampler on T2)."""
        candidates = [
            c for c in gs.zones.creatures_on_battlefield()
            if not c.summoning_sickness or KWTag.HASTE in c.tags
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda c: (c.name == HEARTFIRE, c.name == SWIFTSPEAR,
                            _power_of(c)),
            reverse=True,
        )
        return candidates[0]
