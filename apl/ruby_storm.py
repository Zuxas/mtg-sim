"""
ruby_storm.py — APL for Modern Ruby Storm (Teg / Grinding Breach slot)

Combo: Ral, Monsoon Mage → flips to Ral, Leyline Prodigy.
Each instant/sorcery deals 1 damage. Chain rituals + Past in Flames
to cast 20+ spells in one turn.

Key cards:
  - Ral, Monsoon Mage (2): flips after 3rd instant/sorcery. Leyline Prodigy
    deals 1 damage per instant/sorcery.
  - Desperate Ritual (4): {1}{R} → {R}{R}{R} (net +1 mana, storm trigger)
  - Pyretic Ritual (4): {1}{R} → {R}{R}{R} (net +1 mana)
  - Manamorphose (4): {1}{R/G} → draw 1 + 2 mana any color (free cantrip)
  - Glimpse the Impossible (4): {2}{R} → exile top 4, cast up to 2
  - Past in Flames (3): {3}{R} → flashback all instants/sorceries from GY
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

RITUALS = {"Desperate Ritual", "Pyretic Ritual"}
FREE_CANTRIP = {"Manamorphose"}
RAL = "Ral, Monsoon Mage"


class RubyStormAPL(BaseAPL):
    name = "Ruby Storm"
    win_condition_damage = 20
    max_turns = 12
    _storm_count = 0
    _ral_active = False

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        rituals = [c for c in hand if c.name in RITUALS]
        has_ral = any(c.name == RAL for c in hand)
        if len(hand) <= 4: return True
        if not lands: return False
        # Ral + rituals = keep
        if has_ral and rituals and lands: return True
        # 2 lands + rituals + draw = keep
        if len(lands) >= 2 and len(rituals) >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 2: to_bottom.extend(lands[2:])
        rest = sorted([c for c in hand if not c.is_land() and c.name != RAL],
                       key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def _cast_spell_storm(self, gs, card):
        """Cast a spell and track storm count + Ral damage."""
        if card.has(Tag.INSTANT) or card.has(Tag.SORCERY):
            self._storm_count += 1
            if self._ral_active:
                gs.damage_dealt += 1
        return True

    def _try_go_off(self, gs):
        """Attempt to combo off: chain rituals, cantrips, Past in Flames."""
        # Phase 1: Cast rituals for mana
        changed = True
        while changed:
            changed = False
            for card in list(gs.hand()):
                if card.name in RITUALS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.mana_pool.pay(card.mana_cost, card.cmc)
                    gs.zones.remove_from_hand(card)
                    gs.zones.graveyard.append(card)
                    gs.mana_pool.add("R", 3)  # ritual produces RRR
                    self._cast_spell_storm(gs, card)
                    gs._log(f"  Ritual: {card.name} (storm {self._storm_count}, dmg {gs.damage_dealt})")
                    changed = True
                    break
                if card.name in FREE_CANTRIP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.mana_pool.pay(card.mana_cost, card.cmc)
                    gs.zones.remove_from_hand(card)
                    gs.zones.graveyard.append(card)
                    gs.mana_pool.flex += 2  # Manamorphose: 2 mana any color
                    gs.zones.draw(1)
                    self._cast_spell_storm(gs, card)
                    gs._log(f"  Manamorphose (storm {self._storm_count}, dmg {gs.damage_dealt})")
                    changed = True
                    break
                if card.name == "Glimpse the Impossible" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs.zones.draw(2)  # simplified: draw 2
                    self._cast_spell_storm(gs, card)
                    gs._log(f"  Glimpse (storm {self._storm_count})")
                    changed = True
                    break
            if gs.damage_dealt >= 20:
                return True

        # Phase 2: Past in Flames — replay everything from GY
        pif = next((c for c in gs.hand() if c.name == "Past in Flames"
                     and gs.mana_pool.can_cast(c.mana_cost, c.cmc)), None)
        if pif:
            gs.cast_spell(pif)
            self._cast_spell_storm(gs, pif)
            gs._log(f"  Past in Flames (storm {self._storm_count})")
            # Replay all rituals from GY
            gy_rituals = [c for c in list(gs.zones.graveyard) if c.name in RITUALS]
            gy_cantrips = [c for c in list(gs.zones.graveyard) if c.name in FREE_CANTRIP]
            for card in gy_rituals + gy_cantrips:
                if card.name in RITUALS and gs.mana_pool.total() >= 2:
                    gs.mana_pool.pay("{1}{R}", 2)
                    gs.zones.graveyard.remove(card)
                    gs.zones.exile.append(card)
                    gs.mana_pool.add("R", 3)
                    self._cast_spell_storm(gs, card)
                elif card.name in FREE_CANTRIP and gs.mana_pool.total() >= 2:
                    gs.mana_pool.pay("{1}{R}", 2)
                    gs.zones.graveyard.remove(card)
                    gs.zones.exile.append(card)
                    gs.mana_pool.flex += 2
                    gs.zones.draw(1)
                    self._cast_spell_storm(gs, card)
                if gs.damage_dealt >= 20:
                    return True
            gs._log(f"  PiF chain done (storm {self._storm_count}, dmg {gs.damage_dealt})")

        return gs.damage_dealt >= 20

    def main_phase(self, gs):
        self._storm_count = 0
        self._play_land_if_able(gs)

        # Cast Ral first (needs to be in play before we go off)
        if not self._ral_active:
            for card in list(gs.hand()):
                if card.name == RAL and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    self._ral_active = True
                    gs._log(f"  Ral, Monsoon Mage deployed")
                    break

        # If Ral is active + we have rituals, try to go off
        if self._ral_active:
            self._try_go_off(gs)

    def main_phase2(self, gs):
        # Try again post-combat if didn't win in main1
        if gs.damage_dealt < 20 and self._ral_active:
            self._try_go_off(gs)
        # Cast anything leftover
        self._cast_all_castable(gs)
