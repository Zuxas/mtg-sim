"""
apl/azorius_blink_standard_match.py -- Azorius Blink match APL (Standard / PT SOS 2026)

2.5% of PT SOS field (12/481 players).
Engine: Enduring Innocence (draw on ETB) + Nurturing Pixie (blink enabler)
        + Novice Inspector (Treasure ETB) for sustained card advantage.
Flying beatdown backed by Shardmage's Rescue (instant blink for protection/triggers)
and Get Lost (removal).

SB profile:
  vs aggro: Authority of the Consuls slows opponents, Doorkeeper Thrull shuts ETBs
  vs control: Rest in Peace blanks GY synergies, Sheltered by Ghosts protects threats
  vs combo: Flashfreeze, Soul-Guide Lantern
"""
from data.card import Tag
from apl.match_apl import MatchAPL
from apl.azorius_blink_standard import AzoriusBlinkAPL
from engine.match_state import safe_power

INSPECTOR  = "Novice Inspector"
PIXIE      = "Nurturing Pixie"
INNOCENCE  = "Enduring Innocence"
VOICE      = "Voice of Victory"
SHEPHERD   = "Starfield Shepherd"
MOMO       = "Momo, Friendly Flier"
HALIYA     = "Haliya, Guided by Light"
RESCUE     = "Shardmage's Rescue"
ZENITH     = "Cosmogrand Zenith"
GET_LOST   = "Get Lost"
SEAM_RIP   = "Seam Rip"
AUTHORITY  = "Authority of the Consuls"
THRULL     = "Doorkeeper Thrull"
SHELTERED  = "Sheltered by Ghosts"
REST_PEACE = "Rest in Peace"
FLASHFREEZE = "Flashfreeze"
LANTERN    = "Soul-Guide Lantern"


class AzoriusBlinkStandardMatchAPL(MatchAPL, AzoriusBlinkAPL):
    ARCHETYPE = "tempo"
    SB_PLANS = {
        "aggro": (
            ["2 Authority of the Consuls", "2 Doorkeeper Thrull", "1 Rest in Peace"],
            ["2 Cosmogrand Zenith", "2 Seam Rip", "1 Flow State"],
        ),
        "control": (
            ["2 Sheltered by Ghosts", "2 Rest in Peace", "1 Clarion Conqueror"],
            ["2 Seam Rip", "2 Get Lost", "1 Cosmogrand Zenith"],
        ),
        "combo": (
            ["2 Flashfreeze", "2 Soul-Guide Lantern", "1 Doorkeeper Thrull"],
            ["2 Seam Rip", "2 Starfield Shepherd", "1 Opt"],
        ),
        "ramp": (
            ["2 Flashfreeze", "2 Sheltered by Ghosts"],
            ["2 Seam Rip", "2 Get Lost"],
        ),
        "tempo": (
            ["2 Doorkeeper Thrull", "2 Authority of the Consuls"],
            ["2 Seam Rip", "2 Get Lost"],
        ),
    }

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Removal on large threats
        if opponent:
            threats = [c for c in opponent.zones.battlefield
                       if not c.is_land() and safe_power(c) >= 3]
            if threats:
                for c in list(gs.zones.hand):
                    if c.name == GET_LOST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        target = max(threats, key=lambda x: safe_power(x))
                        gs.cast_spell(c)
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.exile.append(target)
                        gs._log(f"  Get Lost exiles {target.name}")
                        break

        # Deploy in curve order (Innocence early = max draw value)
        for name in (INSPECTOR, INNOCENCE, PIXIE, VOICE, SHEPHERD, HALIYA, MOMO, ZENITH):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == INSPECTOR:
                        gs._log("  Novice Inspector ETB: create Treasure")
                    break

        # Dump remaining
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def declare_attackers(self, gs, opponent):
        attackers = [
            c for c in gs.zones.battlefield
            if not c.is_land()
            and c.has(Tag.CREATURE)
            and not getattr(c, 'summoning_sickness', False)
            and not getattr(c, 'tapped', False)
        ]
        return attackers
