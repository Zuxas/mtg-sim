"""
apl/boros_energy.py — Boros Energy APL (Modern)

Deck: Ocelot Pride + Guide of Souls energy engine with Ragavan + Phlage top end.
Kill clock: T3.8 avg (can kill T2-3 with good hands)

Priority order:
  T1: Ragavan > Guide of Souls > Ocelot Pride
  T2: Ocelot Pride > Ajani > Seasoned Pyromancer > Guide of Souls
  T3: Phlage > Seasoned Pyromancer > Ajani > pump + attack
  Combat: attack every turn, use energy for +2/+2 flying via Guide of Souls

Key mechanic: Ocelot Pride creates Cat tokens whenever we cast a noncreature spell.
Goblin Bombardment = sacrifice outlet to push through damage.
"""

from apl.base_apl import BaseAPL
from data.card import Card, Tag
from engine.game_state import GameState

RAGAVAN       = "Ragavan, Nimble Pilferer"
GUIDE         = "Guide of Souls"
OCELOT        = "Ocelot Pride"
AJANI         = "Ajani, Nacatl Pariah"
PYROMANCER    = "Seasoned Pyromancer"
PHLAGE        = "Phlage, Titan of Fire's Fury"
VOICE         = "Voice of Victory"
GALVANIC      = "Galvanic Discharge"
BOMBARDMENT   = "Goblin Bombardment"
THRABEN       = "Thraben Charm"
BLOOD_MOON    = "Blood Moon"
STATIC_PRISON = "Static Prison"


class BorosEnergyAPL(BaseAPL):
    """
    Boros Energy — energy-based Ocelot Pride aggro.
    Aggressive curve, pump creatures with Guide of Souls energy.
    """

    name = "Boros Energy"
    win_condition_damage = 20
    max_turns = 12

    # ── Sideboard plan ────────────────────────────────────────────────────
    # Real SB: 3x Obsidian Charmaw, 2x Surgical Extraction, 2x Vexing Bauble,
    #          2x Wear//Tear, 2x Wrath of the Skies, 1x Blood Moon,
    #          1x Celestial Purge, 1x Clarion Conqueror, 1x Orim's Chant

    def sideboard_premium(self, opp_name: str, format_name: str) -> float:
        opp = opp_name.lower()
        # Blood Moon + Obsidian Charmaw crush multiland combo/ramp
        if any(k in opp for k in ("titan", "amulet")):
            return 14.0   # Blood Moon + Charmaw + Bauble — near-lock
        if any(k in opp for k in ("breach", "grinding")):
            return 13.0   # Blood Moon + Charmaw + Surgical + Bauble
        if any(k in opp for k in ("neoform", "simic ritual")):
            return 12.0   # Surgical + Vexing Bauble
        if any(k in opp for k in ("goryo", "reanimator", "esper reanimator")):
            return 11.0   # Surgical + Cage + Celestial Purge
        if any(k in opp for k in ("tron", "eldrazi ramp")):
            return 10.0   # Blood Moon is game-ending vs Tron
        if any(k in opp for k in ("mono red", "aggro", "burn")):
            return 8.0    # Wrath of Skies + Clarion + Purge
        if any(k in opp for k in ("prowess",)):
            return 7.0    # Wrath of Skies + Clarion
        if any(k in opp for k in ("domain", "zoo")):
            return 7.0    # Wrath + Clarion + Wear/Tear
        if any(k in opp for k in ("blink", "orzhov", "jeskai", "esper")):
            return 4.0    # Charmaw + Moon, but they also SB well vs us
        if any(k in opp for k in ("dimir", "murktide", "frog")):
            return 5.0    # Clarion + Orim's Chant
        if any(k in opp for k in ("affinity",)):
            return 8.0    # Wear/Tear + Meltdown + Wrath
        return 6.0

    # ── Opponent-aware mulligan ───────────────────────────────────────────

    def keep_vs(self, hand, mulligans, on_play, opp_archetype):
        opp = opp_archetype.lower()
        lands    = sum(1 for c in hand if c.is_land())
        threats  = sum(1 for c in hand if c.name in {RAGAVAN, GUIDE, OCELOT, AJANI})
        one_drops= sum(1 for c in hand if c.name in {RAGAVAN, GUIDE})

        # vs fast combo: need a clock, not fair quality
        if any(k in opp for k in ("goryo", "neoform", "breach", "doomsday")):
            if len(hand) <= 4: return True
            if lands == 0: return False
            # Need threat + land to race — keep any 1+ land with threat
            return (lands >= 1 and threats >= 1) or mulligans >= 2

        # vs Tron/ramp: need aggression, Blood Moon in SB
        if any(k in opp for k in ("tron", "titan", "ramp")):
            if len(hand) <= 4: return True
            if lands == 0: return False
            # Aggressive keep — we just need to curve out before they ramp
            return (lands >= 1 and one_drops >= 1) or (lands >= 2 and threats >= 1) or mulligans >= 2

        # vs aggro mirror: keep hands with interaction + threat
        if any(k in opp for k in ("mono red", "prowess", "domain", "zoo")):
            if len(hand) <= 4: return True
            if lands == 0: return False
            has_removal = any(c.name in {GALVANIC, THRABEN} for c in hand)
            return (lands >= 2 and (threats >= 1 or has_removal)) or mulligans >= 2

        # default
        return self.keep(hand, mulligans, on_play)

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands    = sum(1 for c in hand if c.is_land())
        threats  = sum(1 for c in hand if c.name in {RAGAVAN, GUIDE, OCELOT, AJANI})
        has_phlage = any(c.name == PHLAGE for c in hand)

        if lands == 0: return False
        if lands == 1 and len(hand) >= 6 and not (threats >= 2): return False
        if lands >= 2 and (threats >= 1 or has_phlage): return True
        if len(hand) <= 5 or mulligans >= 2: return True
        return lands >= 2 and sum(1 for c in hand if not c.is_land()) >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        extra_lands = lands[3:] if len(lands) > 3 else []
        slow = [c for c in hand if c.name in {BLOOD_MOON, BOMBARDMENT} and len(lands) < 3]
        return (extra_lands + slow)[:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        mana = gs.mana_pool.available()

        # T1 priority: Ragavan > Guide > Ocelot
        for name in (RAGAVAN, GUIDE, OCELOT):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # T2+ priority: Ocelot > Ajani > Pyromancer > Guide
        for name in (OCELOT, AJANI, PYROMANCER, GUIDE):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # T3+ threats
        for name in (PHLAGE, VOICE, STATIC_PRISON):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Removal/pump if mana left
        for card in list(gs.hand()):
            if card.name in {GALVANIC, THRABEN} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                # Use as face damage if we have creatures swinging
                if len([c for c in gs.battlefield() if not c.is_land()]) >= 2:
                    gs.damage_dealt += 2
                    gs.hand().remove(card)
                    gs.zones.graveyard.append(card)
                    gs._log(f"  {card.name} → face (2 dmg)")
                break

    def main_phase2(self, gs: GameState):
        # Post-combat: deploy Goblin Bombardment if we have tokens
        for card in list(gs.hand()):
            if card.name == BOMBARDMENT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
