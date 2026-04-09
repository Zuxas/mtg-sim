"""
standard_aggro.py — Universal APL for Standard aggro decks

Handles: Mono Red, Gruul, Boros, Dimir Aggro, Izzet Prowess.
Logic: curve creatures, burn face, haste attacks.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from engine.keywords import KWTag

# Spells that deal face damage in goldfish
FACE_BURN = {
    "Burst Lightning": 2, "Lightning Strike": 3, "Shock": 2,
    "Witchstalker Frenzy": 4, "Play with Fire": 2, "Strangle": 2,
    "Galvanic Discharge": 0,  # creature only
    "Go for the Throat": 0,  # creature only
    "Cut Down": 0,  # creature only
}

# Pump spells (cast pre-combat on best attacker)
PUMP = {"Monstrous Rage", "Giant Growth", "Titanic Growth", "Audacity"}

HASTE_NAMES = {"Screaming Nemesis", "Monastery Swiftspear", "Burnout Bashtronaut",
               "Heartfire Hero", "Hired Claw", "Goblin Guide"}


class StandardAggroAPL(BaseAPL):
    name = "Standard Aggro"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        creatures = [c for c in hand if c.has(Tag.CREATURE)]
        if len(hand) <= 4: return True
        if not lands: return False
        if len(lands) > 4: return False
        if creatures and len(lands) >= 1: return True
        if len(lands) >= 2 and len([c for c in hand if not c.is_land()]) >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 2: to_bottom.extend(lands[2:])
        # Bottom creature-only removal (dead in goldfish)
        dead = [c for c in hand if c.name in FACE_BURN and FACE_BURN[c.name] == 0]
        to_bottom.extend(dead)
        rest = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def main_phase(self, gs):
        """Pre-combat: land, haste creatures, pump spells on attackers."""
        self._play_land_if_able(gs)

        # Haste creatures pre-combat
        for card in list(gs.hand()):
            if (card.has(Tag.CREATURE) and
                (KWTag.HASTE in card.tags or card.name in HASTE_NAMES) and
                gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs.cast_spell(card)

        # Pump spells on best attacker
        attackers = [c for c in gs.zones.creatures_on_battlefield()
                     if not c.summoning_sickness or KWTag.HASTE in c.tags]
        if attackers:
            best = max(attackers, key=lambda c: c.effective_power())
            for card in list(gs.hand()):
                if card.name in PUMP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    best.counters += 2  # +2/+0 simplified
                    gs._log(f"  Pump: {card.name} on {best.name}")
                    break

    def main_phase2(self, gs):
        """Post-combat: burn face, cast remaining creatures."""
        # Burn face
        for card in list(gs.hand()):
            dmg = FACE_BURN.get(card.name, -1)
            if dmg > 0 and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.damage_dealt += dmg
                gs._log(f"  {card.name} face: {dmg} ({gs.damage_dealt} total)")

        # Cast remaining creatures
        self._cast_all_castable(gs, Tag.CREATURE)
        # Cast anything else
        self._cast_all_castable(gs)
