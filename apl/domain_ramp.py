"""apl/domain_ramp.py -- Domain Ramp APL (Standard)

5-color domain ramp shell. Composes RampAPL, declares the deck's
ramp / payoff / removal cards. Archetype hook: _cast_biggest_payoff
refuses to drop Atraxa before T6 even if we could afford her — in
goldfish she just sits in hand, but casting her on 7 with a fresh
Sunfall-cleared board is more valuable than 6 lines that never
resolve a second payoff.

Kill path: Topiary Stomper / Archangel of Wrath pressure → Atraxa
finishes → Sunfall for +X/+X tokens on the counter.
"""
from apl.ramp_base import RampAPL
from engine.game_state import GameState

# ── Ramp ────────────────────────────────────────────────────────────
BRIEFCASE    = "Courier's Briefcase"      # {1}{W}{B}: draw + treasure
INVASION     = "Invasion of Zendikar"     # {2}{G}: fetch 2 basics
MIGRATION    = "Herd Migration"           # {3}{G}{G}: fetch 2 basics + 3/3 tokens
TOPIARY      = "Topiary Stomper"          # {2}{G}: 4/4, play a land from hand

# ── Payoffs ─────────────────────────────────────────────────────────
LEYLINE      = "Leyline Binding"          # domain-cost removal
ARCHANGEL    = "Archangel of Wrath"       # {2}{W}{W}: flier + kicker modes
SUNFALL      = "Sunfall"                  # {3}{W}{W}: wipe + incubate X
VIRTUE       = "Virtue of Persistence"    # {5}{B}: drain + recur
ATRAXA       = "Atraxa, Grand Unifier"    # {3}{G}{W}{U}{B}: 7/7 lifelink flying

# ── Removal ─────────────────────────────────────────────────────────
THROAT       = "Go for the Throat"        # {1}{B}
DEPOPULATE   = "Depopulate"               # {3}{W}: wipe except tokens


class DomainRampAPL(RampAPL):
    name = "Domain Ramp"
    max_turns = 14

    RAMP_SPELLS = {
        BRIEFCASE: (3, 0),     # draws + treasure; +0 this turn, fixing later
        INVASION:  (3, 0),     # fetch basics (tapped); advances land drops
        TOPIARY:   (3, 0),     # 4/4 that puts a land into play tapped
        MIGRATION: (5, 0),     # fetch + tokens; explosive on T5
    }

    PAYOFFS = (
        LEYLINE,    # domain-scaled, castable on 4 lands with 4 colors
        ARCHANGEL,  # 4-cmc flier, kicker modes burn / gain life
        SUNFALL,    # wipe + incubate — splits threat / removal
        VIRTUE,     # 6-cmc permanent value engine
        ATRAXA,     # 7-cmc game-winner
    )

    REMOVAL = (
        THROAT,
        LEYLINE,       # also acts as removal
        DEPOPULATE,
    )

    # Ramp mulligans are land-hungry
    MULL_MIN_LANDS = 3
    MULL_MAX_LANDS = 6

    # ------------------------------------------------------------------
    # Archetype-specific tuning
    # ------------------------------------------------------------------

    def _after_ramp_cast(self, gs: GameState, name: str, card):
        """Topiary Stomper and Invasion of Zendikar put lands directly
        into play. Model the second land drop by adding +1 to the flex
        mana pool (approximating a tapped land available next turn)."""
        if name in (TOPIARY, INVASION, MIGRATION):
            # These fetch/play lands that enter tapped — next turn we
            # effectively have +1 permanent land. Goldfish approx:
            # bump the pool so later spells in the same turn can use
            # any extra mana these effects generated.
            gs.mana_pool.flex += 1
            gs._log(f"  {name}: +1 land (tapped) for next turn")

    def _after_payoff_cast(self, gs: GameState, name: str, card):
        """Atraxa is 7/7 flying lifelink — count it as 7 damage next
        turn. In goldfish we don't simulate haste-less attacks, so we
        stamp her as a big threat that will hit for 7 when
        _simulate_combat_triggers fires on the following turn."""
        pass   # Combat engine handles her next turn naturally
