"""
modern_domain_zoo.py — APL for Modern Domain Zoo

Key cards: Leyline of the Guildpact (free T0), Scion of Draco (4/4 keywords),
Ragavan (haste), Doorkeeper Thrull (death trigger), Phlage (3 bolt), Lightning Bolt.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

HASTE = {"Ragavan, Nimble Pilferer"}
FACE_DAMAGE = {"Lightning Bolt": 3, "Phlage, Titan of Fire's Fury": 3}


class ModernDomainZooAPL(BaseAPL):
    name = "Domain Zoo"
    win_condition_damage = 20
    max_turns = 10
    _leyline_active = False

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        leyline = any(c.name == "Leyline of the Guildpact" for c in hand)
        creatures = [c for c in hand if c.has(Tag.CREATURE)]
        if len(hand) <= 4: return True
        if not lands and not leyline: return False
        # Leyline + threats = snap keep
        if leyline and creatures: return True
        if len(lands) >= 2 and len(creatures) >= 2: return True
        if any(c.name in HASTE for c in hand) and lands: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 3: to_bottom.extend(lands[3:])
        rest = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def main_phase(self, gs):
        """Pre-combat: Leyline (free), land, haste creatures."""
        # Leyline of the Guildpact — free if in opening hand (T0)
        if gs.turn == 1:
            for card in list(gs.hand()):
                if card.name == "Leyline of the Guildpact":
                    gs.zones.play_from_hand(card)
                    card.turn_entered = gs.turn
                    self._leyline_active = True
                    gs._log(f"  Leyline of the Guildpact: FREE (opening hand)")

        self._play_land_if_able(gs)
        # Haste creatures pre-combat
        for card in list(gs.hand()):
            if card.name in HASTE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

    def main_phase2(self, gs):
        """Post-combat: cast creatures, bolt face, Phlage bolt."""
        # Scion of Draco: 4/4 if domain >= 5 (Leyline gives all colors)
        for card in list(gs.hand()):
            if card.name == "Scion of Draco":
                # With Leyline, domain = 5, so cost is reduced to {2}
                cost = 2 if self._leyline_active else int(card.cmc)
                if gs.mana_pool.total() >= cost:
                    gs.mana_pool.pay("", cost)
                    gs.zones.play_from_hand(card)
                    card.turn_entered = gs.turn
                    card.summoning_sickness = True
                    gs._log(f"  Scion of Draco (domain cost {cost})")
                    break

        # Phlage — 3 damage burn
        for card in list(gs.hand()):
            if card.name == "Phlage, Titan of Fire's Fury" and gs.mana_pool.can_pay("{1}{R}{W}", 3):
                gs.mana_pool.pay("{1}{R}{W}", 3)
                gs.zones.remove_from_hand(card)
                gs.zones.graveyard.append(card)  # sacrifice (didn't escape)
                gs.damage_dealt += 3
                gs.life += 3
                gs._log(f"  Phlage: 3 dmg ({gs.damage_dealt} total)")
                break

        # Lightning Bolt face
        for card in list(gs.hand()):
            if card.name == "Lightning Bolt" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.damage_dealt += 3
                gs._log(f"  Bolt: 3 dmg ({gs.damage_dealt} total)")
                break

        # Leyline Binding (removal, dead in goldfish but cast for board presence)
        # Fill curve
        self._cast_all_castable(gs, Tag.CREATURE)
