"""
grinding_breach.py — APL for Modern Grinding Breach (Teg)

Combo: Underworld Breach + Grinding Station + cheap artifacts = infinite mill/damage.
Goldfish model: cantrip and dig until combo assembled, then instant win.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

COMBO_PIECES = {"Underworld Breach", "Grinding Station"}
CANTRIPS = {"Mishra's Bauble", "Chromatic Star", "Chromatic Sphere",
            "Thought Scour", "Consider", "Preordain", "Serum Visions"}
ENABLERS = {"Emry, Lurker of the Loch", "Mox Opal", "Mox Amber",
            "Urza's Saga", "Grinding Station", "Springleaf Drum"}


class GrindingBreachAPL(BaseAPL):
    name = "Grinding Breach"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        combo = [c for c in hand if c.name in COMBO_PIECES]
        if len(hand) <= 4: return True
        if not lands: return False
        # Combo piece + enablers = keep
        if combo and len(lands) >= 1: return True
        if len(lands) >= 2 and len([c for c in hand if not c.is_land()]) >= 3: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 3: to_bottom.extend(lands[3:])
        rest = sorted([c for c in hand if not c.is_land() and c.name not in COMBO_PIECES],
                       key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def _check_combo(self, gs):
        """Check if we can combo off: Breach + Station in hand/BF + 3 mana + cards in GY."""
        bf_names = {c.name for c in gs.zones.battlefield}
        hand_names = {c.name for c in gs.hand()}
        all_available = bf_names | hand_names

        has_breach = "Underworld Breach" in all_available
        has_station = "Grinding Station" in all_available
        enough_gy = len(gs.zones.graveyard) >= 3
        enough_mana = gs.mana_pool.total() >= 3

        return has_breach and has_station and enough_gy and enough_mana

    def main_phase(self, gs):
        """Land, cantrip to find combo, cast enablers."""
        self._play_land_if_able(gs)

        # Check if we can combo off
        if self._check_combo(gs):
            gs.damage_dealt = 20
            gs._log(f"  COMBO: Underworld Breach + Grinding Station → infinite mill/damage")
            return

        # Cast cantrips to dig
        for card in list(gs.hand()):
            if card.name in CANTRIPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                if card.name not in ("Mishra's Bauble",):
                    gs.zones.draw(1)

        # Cast enablers
        for card in list(gs.hand()):
            if card.name in ENABLERS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        """Post-combat: check combo again, cast remaining."""
        if self._check_combo(gs):
            gs.damage_dealt = 20
            gs._log(f"  COMBO: Breach + Station → win")
            return

        # Cast anything remaining
        self._cast_all_castable(gs)
        # More cantrips
        for card in list(gs.hand()):
            if card.name in CANTRIPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.zones.draw(1)
