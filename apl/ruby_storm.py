"""
ruby_storm.py — APL for Modern Ruby Storm (Teg)

Ral flips after 3 instants/sorceries -> deals 1 per spell.
Ruby Medallion reduces red spells by {1} -> rituals cost {R} not {1}{R}.
With Medallion: ritual costs R, produces RRR = net +2R per ritual.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

RITUALS = {"Desperate Ritual", "Pyretic Ritual"}
FREE_CANTRIP = {"Manamorphose"}
DRAW_SPELLS = {"Glimpse the Impossible", "March of Reckless Joy", "Reckless Impulse"}
RAL = "Ral, Monsoon Mage"
PIF = "Past in Flames"
MEDALLION = "Ruby Medallion"


class RubyStormAPL(BaseAPL):
    name = "Ruby Storm"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._spells = 0
        self._ral_out = False
        self._ral_flipped = False
        self._medallions = 0

    def _reset_turn(self):
        """Reset per-turn state only. Ral state persists across turns."""
        self._spells = 0

    def _reset_game(self):
        """Reset per-game state."""
        self._spells = 0
        self._ral_out = False
        self._ral_flipped = False
        self._medallions = 0

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        rits = [c for c in hand if c.name in RITUALS]
        has_ral = any(c.name == RAL for c in hand)
        has_med = any(c.name == MEDALLION for c in hand)
        if len(hand) <= 4: return True
        if not lands: return False
        if len(lands) > 3: return False
        if has_ral and len(rits) >= 1 and lands: return True
        if has_med and len(rits) >= 2 and lands: return True
        if len(lands) >= 2 and len([c for c in hand if not c.is_land()]) >= 3: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 2: to_bottom.extend(lands[2:])
        keep_names = RITUALS | FREE_CANTRIP | {RAL, PIF, MEDALLION}
        rest = sorted([c for c in hand if not c.is_land() and c.name not in keep_names],
                       key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def _storm(self, gs, name):
        self._spells += 1
        if self._ral_out and not self._ral_flipped and self._spells >= 3:
            self._ral_flipped = True
            gs._log(f"  RAL FLIPS! ({self._spells} spells)")
        if self._ral_flipped:
            gs.damage_dealt += 1

    def _ritual_cost(self):
        """Ritual cost with Medallion. {1}{R} base, each Medallion -1 generic."""
        return max(0, 2 - self._medallions)  # 2 medallions = free

    def _chain(self, gs, from_gy=False):
        changed = True
        while changed and gs.damage_dealt < 20:
            changed = False
            src = list(gs.zones.graveyard) if from_gy else list(gs.hand())
            for card in src:
                cost = self._ritual_cost()
                if card.name in RITUALS and gs.mana_pool.total() >= cost:
                    if cost >= 2: gs.mana_pool.pay("{1}{R}", 2)
                    elif cost == 1: gs.mana_pool.pay("{R}", 1)
                    if from_gy:
                        gs.zones.graveyard.remove(card)
                        gs.zones.exile.append(card)
                    else:
                        gs.zones.remove_from_hand(card)
                        gs.zones.graveyard.append(card)
                    gs.mana_pool.add("R", 3)
                    self._storm(gs, card.name)
                    changed = True; break
                if card.name in FREE_CANTRIP and gs.mana_pool.total() >= cost:
                    if cost >= 2: gs.mana_pool.pay("{1}{R}", 2)
                    elif cost == 1: gs.mana_pool.pay("{R}", 1)
                    if from_gy:
                        gs.zones.graveyard.remove(card)
                        gs.zones.exile.append(card)
                    else:
                        gs.zones.remove_from_hand(card)
                        gs.zones.graveyard.append(card)
                    gs.mana_pool.flex += 2; gs.zones.draw(1)
                    self._storm(gs, card.name)
                    changed = True; break

    def _try_go_off(self, gs):
        self._chain(gs, from_gy=False)
        if gs.damage_dealt >= 20: return True
        for card in list(gs.hand()):
            if card.name in DRAW_SPELLS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card); gs.zones.draw(2)
                self._storm(gs, card.name)
                self._chain(gs, from_gy=False)
                if gs.damage_dealt >= 20: return True
        pif_cost = max(1, 4 - self._medallions)
        for card in list(gs.hand()):
            if card.name == PIF and gs.mana_pool.total() >= pif_cost:
                gs.mana_pool.pay("", pif_cost)
                gs.zones.remove_from_hand(card)
                gs.zones.graveyard.append(card)
                self._storm(gs, PIF)
                gs._log(f"  Past in Flames! ({self._spells} spells, {gs.damage_dealt} dmg)")
                self._chain(gs, from_gy=True)
                if gs.damage_dealt >= 20: return True
                break
        return gs.damage_dealt >= 20

    def main_phase(self, gs):
        self._reset_turn()
        self._medallions = sum(1 for c in gs.zones.battlefield if c.name == MEDALLION)
        self._ral_out = any(c.name == RAL for c in gs.zones.battlefield)
        self._play_land_if_able(gs)
        # Medallion first (reduces all costs)
        for card in list(gs.hand()):
            if card.name == MEDALLION and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                self._medallions += 1
                break
        # Ral
        if not self._ral_out:
            for card in list(gs.hand()):
                if card.name == RAL and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card); self._ral_out = True
                    gs._log(f"  Ral deployed (medallions: {self._medallions})")
                    break
        # Try combo
        if self._ral_out:
            rits = sum(1 for c in gs.hand() if c.name in RITUALS | FREE_CANTRIP)
            has_pif = any(c.name == PIF for c in gs.hand())
            if rits >= 2 or (rits >= 1 and has_pif) or self._medallions >= 1:
                if self._try_go_off(gs): return
        # Setup: cantrips
        for card in list(gs.hand()):
            if card.name in FREE_CANTRIP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card); gs.zones.draw(1)
                if self._ral_out: self._storm(gs, card.name)

    def main_phase2(self, gs):
        if gs.damage_dealt < 20 and self._ral_out: self._try_go_off(gs)
        self._cast_all_castable(gs)
