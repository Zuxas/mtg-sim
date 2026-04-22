"""apl/boros_aggro_standard.py -- Boros Aggro APL (Standard)

Real-Magic Boros Aggro build composed from AggroAPL. Archetype-specific
twist: Kumano Faces Kakkazan ETB puts a +1/+1 counter on the biggest
creature (preferring Swiftspear so prowess stacks), modeled via the
_after_creature_etb hook.

Plays: Swiftspear/Phoenix/Epicure turn one, Kumano/Adversary/Scoundrel
turn two, Squee/Feldon/Goddric as curve-out, burn face in both main
phases with Monstrous Rage on the biggest attacker.
"""
from apl.aggro_base import AggroAPL, _power_of
from engine.game_state import GameState

# ── 1-drops ──────────────────────────────────────────────────────────
SWIFTSPEAR   = "Monastery Swiftspear"
PHOENIX      = "Phoenix Chick"
EPICURE      = "Voldaren Epicure"

# ── 2-drops ──────────────────────────────────────────────────────────
KUMANO       = "Kumano Faces Kakkazan"
ADVERSARY    = "Bloodthirsty Adversary"
SCOUNDREL    = "Charming Scoundrel"

# ── 3-drops ──────────────────────────────────────────────────────────
SQUEE        = "Squee, Dubious Monarch"
FELDON       = "Feldon, Ronom Excavator"

# ── 4-drop ──────────────────────────────────────────────────────────
GODDRIC      = "Goddric, Cloaked Reveler"

# ── Burn / pump ─────────────────────────────────────────────────────
PLAY_FIRE    = "Play with Fire"
LIGHTNING    = "Lightning Strike"
RAGE         = "Monstrous Rage"


class BorosAggroStandardAPL(AggroAPL):
    name = "Boros Aggro"

    CREATURES = (
        SWIFTSPEAR, PHOENIX, EPICURE,          # 1-drops
        KUMANO, ADVERSARY, SCOUNDREL,          # 2-drops
        SQUEE, FELDON,                         # 3-drops
        GODDRIC,                               # 4-drop
    )

    BURN_SPELLS = {
        PLAY_FIRE: (1, 2),    # {R}: 2 damage
        LIGHTNING: (2, 3),    # {1}{R}: 3 damage
    }

    PUMP_SPELLS = {
        RAGE: (1, 2, True),   # {R}: +2/+0 trample
    }

    HASTE_CREATURES = frozenset({PHOENIX, ADVERSARY})

    # ------------------------------------------------------------------
    # Archetype hooks
    # ------------------------------------------------------------------

    def _after_creature_etb(self, gs: GameState, name: str, card):
        """Kumano Faces Kakkazan ETB: +1/+1 counter on a creature we
        control. Prefer Swiftspear (prowess + counter stacks)."""
        if name != KUMANO:
            return
        targets = [
            c for c in gs.zones.creatures_on_battlefield()
            if c.name != KUMANO
        ]
        if not targets:
            return
        targets.sort(
            key=lambda c: (c.name == SWIFTSPEAR, _power_of(c)),
            reverse=True,
        )
        targets[0].counters += 1
        gs._log(f"  Kumano ETB: +1/+1 on {targets[0].name}")

    def _pick_pump_target(self, gs: GameState):
        """Prefer Swiftspear for Monstrous Rage — prowess + Rage stack."""
        from engine.keywords import KWTag
        candidates = [
            c for c in gs.zones.creatures_on_battlefield()
            if not c.summoning_sickness or KWTag.HASTE in c.tags
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda c: (c.name == SWIFTSPEAR, _power_of(c)),
            reverse=True,
        )
        return candidates[0]
