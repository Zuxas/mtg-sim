"""
painter.py — APL for Legacy Painter

Win condition: Painter's Servant + Grindstone
Both in play → activate Grindstone → mill entire deck instantly

Turn sequence:
  T1: Ancient Tomb → Painter's Servant (2 mana) OR Imperial Recruiter
  T2: Grindstone (1 mana) → activate for 3 mana → win
  Backup: Goblin Engineer → fetch Grindstone from deck to graveyard → use
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from apl.mulligan import generic_bottom


COMBO_A = "Painter's Servant"
COMBO_B = "Grindstone"
TUTORS  = {"Imperial Recruiter", "Goblin Engineer"}
# Also catch common OCR/export variants
COMBO_A_VARIANTS = {"Painter's Servant", "Painter Servant", "Painters Servant"}
COMBO_B_VARIANTS = {"Grindstone"}


class PainterAPL(BaseAPL):

    name = "Painter"
    win_condition_damage = 20  # We model combo as instant win (20 dmg)
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        lands   = [c for c in hand if c.is_land()]
        painter = [c for c in hand if c.name == COMBO_A]
        grind   = [c for c in hand if c.name == COMBO_B]
        tutors  = [c for c in hand if c.name in TUTORS]
        accel   = [c for c in hand if c.name in ("Ancient Tomb", "City of Traitors")]
        size = len(hand)

        if size <= 4: return True

        has_mana = len(lands) >= 1 or bool(accel)
        has_piece = bool(painter or grind or tutors)

        if not has_mana: return False
        if has_mana and has_piece: return True
        if len(lands) >= 2 and len(tutors) >= 1: return True
        if mulligans >= 3: return has_mana
        return len(lands) >= 2

    def bottom(self, hand, n):
        return generic_bottom(hand, n)

    def main_phase(self, gs: GameState):
        """
        Painter priority:
          1. Land / Ancient Tomb
          2. Imperial Recruiter (find Painter's Servant)
          3. Goblin Engineer (find Grindstone)
          4. Painter's Servant (half the combo)
          5. Grindstone (other half — activates for {3})
          6. Activate combo if both in play
        """
        self._play_land_if_able(gs)

        # Imperial Recruiter → find Painter's Servant or another Recruiter
        for c in list(gs.hand()):
            if c.name == "Imperial Recruiter" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                target = self._find_in_library(gs,
                    ["Painter's Servant", "Grindstone", "Goblin Engineer"])
                if target:
                    gs.cast_spell(c)
                    gs.zones.library.remove(target)
                    gs.zones.hand.append(target)
                    gs._log(f"  Imperial Recruiter → {target.name}")
                    break

        # Goblin Engineer → find Grindstone
        for c in list(gs.hand()):
            if c.name == "Goblin Engineer" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                grind = next((l for l in gs.zones.library if l.name == COMBO_B), None)
                if grind:
                    gs.cast_spell(c)
                    gs.zones.library.remove(grind)
                    gs.zones.graveyard.append(grind)
                    gs._log("  Goblin Engineer → Grindstone to graveyard")
                break

        # Painter's Servant (any name variant)
        for c in list(gs.hand()):
            if c.name in COMBO_A_VARIANTS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # Grindstone
        for c in list(gs.hand()):
            if c.name in COMBO_B_VARIANTS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # Activate combo
        self._try_activate_combo(gs)

        # Pyroblast / REB as extra damage if combo is assembled
        for c in list(gs.hand()):
            if c.name in ("Pyroblast", "Red Elemental Blast") \
               and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.damage_dealt += 3

    def _find_in_library(self, gs, priority_list):
        for name in priority_list:
            card = next((c for c in gs.zones.library if c.name == name), None)
            if card:
                return card
        return None

    def _try_activate_combo(self, gs):
        """If any Painter's Servant variant + Grindstone in play → win."""
        has_painter  = any(c.name in COMBO_A_VARIANTS for c in gs.zones.battlefield)
        has_grindstone = any(c.name in COMBO_B_VARIANTS for c in gs.zones.battlefield)

        if has_painter and has_grindstone and gs.mana_pool.total() >= 3:
            gs.mana_pool.pay("", 3)
            gs.damage_dealt = 20
            gs._log("  Painter's Servant + Grindstone activated → mill entire deck → WIN")

    def main_phase2(self, gs: GameState):
        self._try_activate_combo(gs)
