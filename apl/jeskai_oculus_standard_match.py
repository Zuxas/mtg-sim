"""
apl/jeskai_oculus_standard_match.py -- Jeskai Oculus (Standard 2026)

From UltimateGuard guide (Apr 2025). Proactive creature-based midrange with
dual win conditions.

Key cards:
  Proft's Eidetic Memory: enchantment; whenever creature with a counter attacks = draw
  Abhorrent Oculus:       Dimir reanimation target (Plan B)
  Marauding Mako {2B}:    sacrifice outlet; triggers on discard
  Fear of Missing Out:    sorcery; until EOT, whenever you attack, untap all creatures
  Steamcore Scholar:      secondary threat/draw
  Tersa Lightshatter:     secondary threat
  Torch the Tower {R}:    1-mana removal (Bargain = sacrifice artifact for 3 damage)
  Spell Pierce {U}:       counter vs non-creature spells

Favorable vs: Izzet Prowess (54% WR per guide), Mono Red, Esper Pixie, Azorius Omniscience
Weak vs: Domain Ramp, Dimir Midrange

Sideboard from guide:
  vs Izzet Prowess: +2 High Noon, +2 Sheltered by Ghosts, +1 Loran
                    -2 Spyglass Siren, -1 Winternight Stories, -1 Oculus, -1 Helping Hand
  vs Control:       +Disdainful Stroke, No More Lies, Negate, 2x Chandra, 2x Destroy Evil,
                    Exorcise, Loran | -Torch the Tower (4x), Sheltered, Glacial Dragonhunt (2x)
  vs Omniscience:   +2 Ghost Vacuum, No More Lies, Disdainful, Negate, 2x Destroy Evil,
                    Exorcise, High Noon | -Sheltered, Torch (4x), Glacial (2x), Winternight, Proft
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

PROFT         = "Proft's Eidetic Memory"
OCULUS        = "Abhorrent Oculus"
MAKO          = "Marauding Mako"
FEAR_MISSING  = "Fear of Missing Out"
STEAMCORE     = "Steamcore Scholar"
TERSA         = "Tersa Lightshatter"
TORCH         = "Torch the Tower"
SPYGLASS      = "Spyglass Siren"
SPELL_PIERCE  = "Spell Pierce"
GLACIAL       = "Glacial Dragonhunt"
WINTERNIGHT   = "Winternight Stories"

HIGH_NOON     = "High Noon"
SHELTERED     = "Sheltered by Ghosts"
LORAN         = "Loran of the Third Path"
GHOST_VAC     = "Ghost Vacuum"
DESTROY_EVIL  = "Destroy Evil"
EXORCISE      = "Exorcise"
NO_MORE_LIES  = "No More Lies"
DISDAINFUL    = "Disdainful Stroke"
NEGATE        = "Negate"
CHANDRA       = "Chandra"

# Kill priority: answer before they draw engine fires
KILL_PRIORITY = (
    PROFT,               # draw engine; exile if possible
    "Gran-Gran",         # Monument enabler
    "Mightform Harmonizer", # Landfall combo
    "Icetill Explorer",  # Landfall chain
    "Badgermole Cub",    # ramp
)

ENGINE_PIECES = {PROFT, OCULUS, MAKO, FEAR_MISSING, STEAMCORE, TERSA}


class JeskaiOculusMatchAPL(AwareMatchAPL):
    name = "Jeskai Oculus"
    ARCHETYPE = "combo"

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        has_engine = any(c.name in ENGINE_PIECES for c in hand)
        return has_engine or mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[3:]
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom
                         and c.name not in ENGINE_PIECES],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (to_bottom + filler)[:n]

    # Spell Pierce {U}: hold 1 mana when in hand
    COUNTER_COST  = 1
    COUNTER_CARDS = {SPELL_PIERCE, NO_MORE_LIES, NEGATE, DISDAINFUL}

    MATCH_REMOVAL = {
        TORCH: ("R", 3),  # 3 damage (Bargain mode = sacrifice artifact for extra damage)
    }
    MATCH_EXILE = {GLACIAL}  # Glacial Dragonhunt exiles

    SB_PLANS = {
        "tempo": (
            # vs Izzet Prowess: High Noon + Sheltered; trim clunky threats
            [HIGH_NOON, HIGH_NOON, SHELTERED, SHELTERED, LORAN],
            [SPYGLASS, SPYGLASS, WINTERNIGHT, OCULUS, "Helping Hand"],
        ),
        "aggro": (
            # vs Red Aggro: more removal + creatures; trim card engines
            [SHELTERED, SHELTERED, DESTROY_EVIL, DESTROY_EVIL, EXORCISE],
            [WINTERNIGHT, WINTERNIGHT, GLACIAL, GLACIAL, OCULUS],
        ),
        "control": (
            # vs Control/Jeskai: counters + Chandra threats
            [DISDAINFUL, NO_MORE_LIES, NEGATE, CHANDRA, CHANDRA,
             DESTROY_EVIL, DESTROY_EVIL, EXORCISE, LORAN],
            [TORCH, TORCH, TORCH, TORCH, SHELTERED,
             GLACIAL, GLACIAL, MAKO, OCULUS],
        ),
        "combo": (
            # vs Omniscience: GY hate + counters
            [GHOST_VAC, GHOST_VAC, NO_MORE_LIES, DISDAINFUL, NEGATE,
             DESTROY_EVIL, DESTROY_EVIL, EXORCISE, HIGH_NOON],
            [SHELTERED, TORCH, TORCH, TORCH, TORCH,
             GLACIAL, GLACIAL, WINTERNIGHT, PROFT],
        ),
        "midrange": (
            # vs Dimir Midrange: Destroy Evil for recursive threats; trim tempo pieces
            [DESTROY_EVIL, DESTROY_EVIL, EXORCISE, NEGATE, GHOST_VAC],
            [GLACIAL, GLACIAL, MAKO, SPYGLASS, OCULUS],
        ),
    }

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_pierce = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        gs.mana_reserve = self.COUNTER_COST if has_pierce else 0

    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._play_land_if_able(gs)
        if hasattr(self, 'reserve_mana'):
            self.reserve_mana(gs, opponent)
        gs.tap_lands()
        self._opp_gs = opponent

        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]

        # Kill priority targets with Torch
        for name in KILL_PRIORITY:
            target = next((c for c in opp_creatures if c.name == name), None)
            if target and safe_toughness(target) <= 3:
                if self._kill_with_removal(gs, opponent, target, prefer_exile=True):
                    break

        # Engine deployment priority: Proft first (enables card advantage), then threats
        for name in (PROFT, MAKO, STEAMCORE, TERSA, FEAR_MISSING, OCULUS):
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        self._cast_all_castable(gs)

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name and safe_toughness(c) <= 3:
                    if self._kill_with_removal(gs, opponent, c, prefer_exile=True):
                        gs._log(f"  [pre-combat] Torch killed {c.name}")
                        return
        super().pre_combat_instant(gs, opponent)

    def declare_blockers(self, gs: GameState, opponent: GameState, attackers: list):
        if not attackers:
            return {}
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        assignments = {}
        for atk, blk in zip(
            sorted(attackers, key=lambda c: -safe_power(c)),
            sorted(my_creatures, key=lambda c: -safe_toughness(c))
        ):
            assignments[id(atk)] = [blk]
        return assignments
