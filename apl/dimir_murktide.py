"""
dimir_murktide.py — APL for Modern UR Murktide

Key: Ragavan T1 haste, DRC T1 (flips to 3/3 flyer), cantrips fill GY,
Murktide Regent delves for cheap 8/8 flyer. Bolt face.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

HASTE = {"Ragavan, Nimble Pilferer"}
CANTRIPS = {"Preordain", "Opt", "Consider", "Mishra's Bauble", "Expressive Iteration"}


class MurktideAPL(BaseAPL):
    name = "Dimir Murktide"
    win_condition_damage = 20
    max_turns = 10
    _treasures = 0

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        ones = [c for c in hand if c.has(Tag.ONE_DROP) and not c.is_land()]
        if len(hand) <= 4: return True
        if not lands: return False
        if len(lands) > 4: return False
        # Need a threat
        threats = [c for c in hand if c.has(Tag.CREATURE)]
        if threats and len(lands) >= 1: return True
        # Cantrip hand with land
        cantrips = [c for c in hand if c.name in CANTRIPS]
        if cantrips and lands and len(hand) - len(lands) >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 3: to_bottom.extend(lands[3:])
        # Bottom counters/removal (dead in goldfish)
        for c in hand:
            if len(to_bottom) >= n: break
            if c.name in ("Counterspell", "Spell Pierce", "Spell Snare") and c not in to_bottom:
                to_bottom.append(c)
        rest = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def main_phase(self, gs):
        """Pre-combat: land, haste creatures, cantrips."""
        if self._treasures > 0:
            gs.mana_pool.flex += min(self._treasures, 2)
            self._treasures -= min(self._treasures, 2)

        self._play_land_if_able(gs)
        # Ragavan (haste)
        for card in list(gs.hand()):
            if card.name in HASTE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        # Cantrips pre-combat to fill GY for Murktide
        for card in list(gs.hand()):
            if card.name in CANTRIPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                if card.name == "Expressive Iteration":
                    gs.zones.draw(1)  # simplified: net +1 card
                elif card.name != "Mishra's Bauble":
                    gs.zones.draw(1)
                break

    def main_phase2(self, gs):
        """Post-combat: Ragavan treasure, Murktide delve, more cantrips, Bolt face."""
        from engine.keywords import KWTag
        # Ragavan treasure
        ragavans = sum(1 for c in gs.zones.creatures_on_battlefield()
                       if c.name == "Ragavan, Nimble Pilferer"
                       and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        self._treasures += ragavans

        # Murktide Regent: costs {1}{U} + delve (exile cards from GY)
        # With 6+ cards in GY, costs just {U}{U} effectively
        for card in list(gs.hand()):
            if card.name == "Murktide Regent":
                gy_size = len(gs.zones.graveyard)
                # Delve reduces generic cost. Base: {5}{U}{U} = 7 mana. 
                # Each exiled card reduces by 1. With 5 in GY: costs {U}{U}
                delve = min(gy_size, 5)
                actual_cost = max(0, 7 - delve - gs.mana_pool.total()) 
                if gs.mana_pool.total() >= (7 - delve) and gs.mana_pool.U + gs.mana_pool.flex >= 2:
                    # Exile cards from GY for delve
                    for _ in range(delve):
                        if gs.zones.graveyard:
                            exiled = gs.zones.graveyard.pop(0)
                            gs.zones.exile.append(exiled)
                    gs.mana_pool.pay("{U}{U}", 2)
                    remaining = 5 - delve
                    if remaining > 0:
                        gs.mana_pool.pay("", remaining)
                    gs.zones.play_from_hand(card)
                    card.turn_entered = gs.turn
                    card.summoning_sickness = True
                    # Power = 8/8 base + cards exiled
                    card.power = str(8 + delve)
                    card.toughness = str(8 + delve)
                    gs._log(f"  Murktide Regent: {card.power}/{card.toughness} (delved {delve})")
                    break

        # DRC / Ledger Shredder: just cast as creatures
        for card in list(gs.hand()):
            if card.has(Tag.CREATURE) and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

        # Lightning Bolt face
        for card in list(gs.hand()):
            if card.name == "Lightning Bolt" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.damage_dealt += 3
                gs._log(f"  Bolt: 3 dmg ({gs.damage_dealt} total)")
                break

        # More cantrips
        for card in list(gs.hand()):
            if card.name in CANTRIPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                if card.name != "Mishra's Bauble":
                    gs.zones.draw(1)
