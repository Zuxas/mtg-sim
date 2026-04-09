"""
eldrazi_ramp.py — APL for Modern Gruul Eldrazi Ramp

Key cards: Eldrazi Temple (2 mana for colorless), Sowing Mycospawn (finds Temple),
Malevolent Rumble (finds creatures), Kozilek's Command, Emrakul.

The deck ramps via Eldrazi Temple + green spells into huge Eldrazi threats.
Goldfish plan: ramp turns 1-3, slam threats turns 3-5.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

BIG_THREATS = {"Emrakul, the Promised End", "Sire of Seven Deaths", 
               "Devourer of Destiny", "Ulamog, the Ceaseless Hunger",
               "World Breaker"}


class EldraziRampAPL(BaseAPL):
    name = "Eldrazi Ramp"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        ramp = [c for c in hand if c.name in ("Sowing Mycospawn", "Malevolent Rumble",
                "Ancient Stirrings", "Kozilek's Command")]
        threats = [c for c in hand if c.name in BIG_THREATS]
        if len(hand) <= 4: return True
        if not lands: return False
        if len(lands) > 5: return False
        # Need land + ramp or land + threats
        if len(lands) >= 2 and (ramp or threats): return True
        if any(c.name == "Eldrazi Temple" for c in hand) and len(lands) >= 2: return True
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

    def _best_land(self, gs):
        lands = [c for c in gs.hand() if c.is_land()]
        if not lands: return None
        # Eldrazi Temple first (2 mana for Eldrazi spells)
        def score(c):
            n = c.name.lower()
            if "eldrazi temple" in n: return 0
            if "cavern" in n: return 1
            if "forest" in n or "stomping" in n: return 2
            return 3
        return min(lands, key=score)

    def main_phase(self, gs):
        """Ramp: play land, cast ramp spells, then slam biggest threat."""
        self._play_land_if_able(gs)

        # Eldrazi Temple: gives 2 colorless for Eldrazi spells
        # Model as extra mana when casting Eldrazi
        temples = sum(1 for c in gs.zones.lands_on_battlefield()
                      if c.name == "Eldrazi Temple")
        if temples > 0:
            # Each temple gives +1 extra for colorless creatures
            gs.mana_pool.C += temples  # extra colorless from temple

        # Cast ramp/dig spells first
        for card in list(gs.hand()):
            if card.name in ("Sowing Mycospawn", "Malevolent Rumble", "Ancient Stirrings",
                            "Formidable Speaker", "Icetill Explorer"):
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Sowing Mycospawn: find Eldrazi Temple or creature
                    if card.name == "Sowing Mycospawn":
                        gs.zones.draw(1)  # simplified: draws into gas
                    elif card.name in ("Malevolent Rumble", "Ancient Stirrings"):
                        gs.zones.draw(1)

        # Kozilek's Command: modal, often ramps + draws
        for card in list(gs.hand()):
            if card.name == "Kozilek's Command" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.zones.draw(1)  # simplified

    def main_phase2(self, gs):
        """Post-combat: slam biggest creature possible."""
        # Eldrazi Temple bonus again for post-combat casting
        temples = sum(1 for c in gs.zones.lands_on_battlefield()
                      if c.name == "Eldrazi Temple")
        if temples > 0:
            gs.mana_pool.C += temples

        # Cast biggest threat we can afford
        castable = [c for c in gs.hand() if c.has(Tag.CREATURE)
                    and gs.mana_pool.total() >= c.cmc]
        if castable:
            biggest = max(castable, key=lambda c: (int(c.power or 0), c.cmc))
            # Emrakul cost reduction: 1 less per card type in GY
            if biggest.name == "Emrakul, the Promised End":
                types_in_gy = set()
                for c in gs.zones.graveyard:
                    t = c.type_line.lower()
                    for typ in ("creature", "instant", "sorcery", "artifact",
                               "enchantment", "planeswalker", "land"):
                        if typ in t: types_in_gy.add(typ)
                reduction = len(types_in_gy)
                actual_cost = max(4, 13 - reduction)
                if gs.mana_pool.total() >= actual_cost:
                    gs.mana_pool.pay("", actual_cost)
                    gs.zones.play_from_hand(biggest)
                    biggest.turn_entered = gs.turn
                    biggest.summoning_sickness = True
                    gs._log(f"  Emrakul (cost {actual_cost}, reduced by {reduction})")
                    return

            if gs.mana_pool.can_cast(biggest.mana_cost, biggest.cmc):
                gs.cast_spell(biggest)

        # Kozilek's Return from GY: when big Eldrazi enters, deal 5 to all
        # (in goldfish this is just flavor, but track it for accuracy)

        # Fill remaining curve
        self._cast_all_castable(gs, Tag.CREATURE)
        self._cast_all_castable(gs)
