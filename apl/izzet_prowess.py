"""
apl/izzet_prowess.py — Izzet Prowess APL (Modern)

VERIFIED mechanics:
  - Prowess: whenever you cast a noncreature spell, this creature gets +1/+1 until EOT
  - Monastery Swiftspear: 1/2 haste, prowess
  - Dragon's Rage Channeler: 1/1, surveil 1 on cast. Delirium → 3/3 flying
  - Slickshot Show-Off: 3/1 flying haste, prowess (double strike with plot?)
  - Cori-Steel Cutter: 2/1, prowess
  - Lightning Bolt: 3 damage any target
  - Lava Dart: 1 damage. Flashback: sac a Mountain
  - Mutagenic Growth: {G/P} → +2/+2 until EOT (pay 2 life)
  - Mishra's Bauble: 0 mana artifact, sac → draw next upkeep
  - Expressive Iteration: look at 3, put 1 in hand, 1 on top
  - Preordain: scry 2, draw 1

Goldfish model:
  - Deploy threats T1-T2
  - T2-T3: chain free/cheap spells to pump prowess creatures
  - Each noncreature spell = +1/+1 to EACH prowess creature
  - Bolt/Dart go face for direct damage
  - Kill by accumulating prowess triggers + combat damage
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

SWIFTSPEAR = "Monastery Swiftspear"
DRC        = "Dragon's Rage Channeler"
SLICKSHOT  = "Slickshot Show-Off"
CORI       = "Cori-Steel Cutter"
BOLT       = "Lightning Bolt"
LAVA_DART  = "Lava Dart"
ITERATION  = "Expressive Iteration"
PREORDAIN  = "Preordain"
BAUBLE     = "Mishra's Bauble"
MUTAGENIC  = "Mutagenic Growth"
VIOLENT    = "Violent Urge"

# All prowess creatures
PROWESS_CREATURES = {SWIFTSPEAR, SLICKSHOT, CORI}


class IzzetProwessAPL(BaseAPL):
    name = "Izzet Prowess"
    win_condition_damage = 20
    max_turns = 10

    _prowess_boosts = []  # track temporary boosts for EOT cleanup

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in PROWESS_CREATURES or c.name == DRC)
        spells = sum(1 for c in hand if c.name in {BOLT, LAVA_DART, MUTAGENIC, BAUBLE})
        if lands == 0: return False
        if threats == 0 and mulligans < 2: return False
        if lands == 1 and threats >= 1 and spells >= 1: return True
        if lands >= 2 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
        to_bottom = []
        if len(lands) > 2:
            to_bottom.extend(lands[2:])
        for c in spells:
            if len(to_bottom) >= n: break
            if c not in to_bottom:
                to_bottom.append(c)
        return to_bottom[:n]

    def _count_prowess_creatures(self, gs):
        """Count prowess creatures on the battlefield."""
        return sum(1 for c in gs.zones.creatures_on_battlefield()
                   if c.name in PROWESS_CREATURES)

    def _trigger_prowess(self, gs, spell_name="spell"):
        """Give all prowess creatures +1/+1 until EOT."""
        for c in gs.zones.creatures_on_battlefield():
            if c.name in PROWESS_CREATURES:
                c.counters += 1
                self._prowess_boosts.append(c)
        count = self._count_prowess_creatures(gs)
        if count:
            gs._log(f"  Prowess: {spell_name} → +1/+1 to {count} creature(s)")

    def _cast_free_spell(self, gs, card):
        """Cast a free spell (Mutagenic/Bauble/Lava Dart) and trigger prowess."""
        if card.name == MUTAGENIC:
            # Pay 2 life instead of {G}
            gs.life -= 2
            gs.zones.hand.remove(card)
            gs.zones.graveyard.append(card)
            # +2/+2 to best attacker (on top of prowess)
            from engine.keywords import KWTag
            attackers = [c for c in gs.zones.creatures_on_battlefield()
                         if not c.summoning_sickness or KWTag.HASTE in c.tags]
            if attackers:
                best = max(attackers, key=lambda c: c.effective_power())
                best.counters += 2
                self._prowess_boosts.append(best)
                self._prowess_boosts.append(best)  # track 2 counters
                gs._log(f"  Mutagenic Growth (2 life) → +2/+2 on {best.name}")
            self._trigger_prowess(gs, MUTAGENIC)
            return True

        elif card.name == BAUBLE:
            # 0 mana, sac → draw next upkeep (model as draw 1 now)
            gs.zones.hand.remove(card)
            gs.zones.graveyard.append(card)
            gs.zones.draw(1)
            self._trigger_prowess(gs, BAUBLE)
            gs._log(f"  Bauble: draw 1")
            return True

        elif card.name == LAVA_DART:
            if card in gs.zones.hand:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.mana_pool.pay(card.mana_cost, card.cmc)
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    gs.damage_dealt += 1
                    self._trigger_prowess(gs, LAVA_DART)
                    gs._log(f"  Lava Dart: 1 dmg face ({gs.damage_dealt} total)")
                    return True
            return False

        return False

    def _flashback_lava_dart(self, gs):
        """Flashback Lava Dart from GY: sac a Mountain → 1 damage."""
        dart_in_gy = next((c for c in gs.zones.graveyard if c.name == LAVA_DART), None)
        if not dart_in_gy:
            return False
        mountains = [c for c in gs.zones.lands_on_battlefield()
                     if "mountain" in c.type_line.lower() and not c.tapped]
        if not mountains:
            return False
        # Sac mountain
        mtn = mountains[0]
        gs.zones.battlefield.remove(mtn)
        gs.zones.graveyard.append(mtn)
        # Exile dart
        gs.zones.graveyard.remove(dart_in_gy)
        gs.zones.exile.append(dart_in_gy)
        gs.damage_dealt += 1
        self._trigger_prowess(gs, "Lava Dart (flashback)")
        gs._log(f"  Lava Dart flashback: sac Mountain, 1 dmg ({gs.damage_dealt} total)")
        return True

    def main_phase(self, gs: GameState):
        """Pre-combat: deploy threats, chain prowess spells, bolt face."""
        self._prowess_boosts = []

        # 1. Land
        self._play_land_if_able(gs)

        # 2. Deploy threats — haste creatures first (attack this turn)
        for name in (SWIFTSPEAR, SLICKSHOT, DRC, CORI):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # 3. Free spells (trigger prowess before combat)
        # Mutagenic Growth — pay 2 life, +2/+2 + prowess trigger
        for card in list(gs.hand()):
            if card.name == MUTAGENIC:
                self._cast_free_spell(gs, card)
                break

        # Bauble — 0 mana, draw + prowess
        for card in list(gs.hand()):
            if card.name == BAUBLE:
                self._cast_free_spell(gs, card)
                break

        # 4. Lava Dart face (from hand)
        for card in list(gs.hand()):
            if card.name == LAVA_DART:
                self._cast_free_spell(gs, card)
                break

        # 5. Lava Dart flashback from GY
        self._flashback_lava_dart(gs)

        # 6. Lightning Bolt face — biggest prowess trigger + 3 damage
        for card in list(gs.hand()):
            if card.name == BOLT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.mana_pool.pay(card.mana_cost, card.cmc)
                gs.zones.hand.remove(card)
                gs.zones.graveyard.append(card)
                gs.damage_dealt += 3
                self._trigger_prowess(gs, BOLT)
                gs._log(f"  Bolt face: 3 dmg ({gs.damage_dealt} total)")
                break

        # 7. Cantrips (prowess trigger + dig)
        for card in list(gs.hand()):
            if card.name in (PREORDAIN, ITERATION) and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.zones.draw(1)  # simplified cantrip draw
                self._trigger_prowess(gs, card.name)
                break

    def main_phase2(self, gs: GameState):
        """Post-combat: cast remaining creatures, clean up prowess boosts."""
        # Cast any remaining threats (summoning sick, but ready next turn)
        for name in (SWIFTSPEAR, DRC, CORI, SLICKSHOT):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Second bolt if available
        for card in list(gs.hand()):
            if card.name == BOLT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.mana_pool.pay(card.mana_cost, card.cmc)
                gs.zones.hand.remove(card)
                gs.zones.graveyard.append(card)
                gs.damage_dealt += 3
                gs._log(f"  Bolt face: 3 dmg ({gs.damage_dealt} total)")
                break

        # Remove prowess boosts at end of turn
        for c in self._prowess_boosts:
            if c in gs.zones.battlefield:
                c.counters = max(0, c.counters - 1)
        self._prowess_boosts = []
