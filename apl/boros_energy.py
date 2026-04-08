"""
boros_energy.py — APL for Modern Boros Energy/Ocelot

Key mechanics modeled:
  - Ragavan: haste, creates Treasure on combat damage (extra mana)
  - Ocelot Pride: first_strike/lifelink, first combat damage each turn creates 1/1 Cat
  - Ajani, Nacatl Pariah: grows from tokens entering, flips to planeswalker
  - Guide of Souls: energy on creature entering attacking, spend 3 for +2/+2
  - Goblin Bombardment: sacrifice creature → 1 damage (finisher)
  - Voice of Victory: Mobilize 2 (2x 1/1 attacking tokens)
  - Seasoned Pyromancer: discard 2, draw 2, create tokens
  - Phlage: 3 damage ETB (escape from graveyard)
  - Screaming Nemesis: 3/3 haste

Goldfish sequencing:
  T1: Ragavan (haste, attacks for treasure) > Ocelot Pride > Guide > Ajani
  T2: More 1-drops, attack generates Ocelot tokens, Ajani grows
  T3: Goblin Bombardment / Voice / Seasoned Pyromancer
  T4+: Sacrifice tokens to Bombardment, overwhelm with board
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL


# Card name constants
RAGAVAN          = "Ragavan, Nimble Pilferer"
OCELOT_PRIDE     = "Ocelot Pride"
AJANI            = "Ajani, Nacatl Pariah"
GUIDE_OF_SOULS   = "Guide of Souls"
GOBLIN_BOMBARD   = "Goblin Bombardment"
VOICE_OF_VICTORY = "Voice of Victory"
SEASONED_PYRO    = "Seasoned Pyromancer"
PHLAGE           = "Phlage, Titan of Fire's Fury"
SCREAMING_NEMESIS = "Screaming Nemesis"
GALVANIC         = "Galvanic Discharge"
STATIC_PRISON    = "Static Prison"
THRABEN_CHARM    = "Thraben Charm"
LIGHTNING_BOLT   = "Lightning Bolt"


class BorosEnergyAPL(BaseAPL):

    name = "Boros Energy"
    win_condition_damage = 20
    max_turns = 12

    # Track Ocelot token generation and Ragavan treasures
    _treasures = 0
    _ocelot_triggered_this_turn = False

    # Cards with reduced value in goldfish but NOT dead:
    # - Galvanic Discharge: target own creature for 0 energy, feeds Guide/Wrath energy
    # - Thraben Charm: +1/+2 pump mode is live in combat
    # - Static Prison: 2 energy on ETB feeds Guide of Souls
    # Only truly dead: Exorcise (opponent permanent only, no energy)
    DEAD_IN_GOLDFISH = {"Exorcise"}

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        lands = [c for c in hand if c.is_land()]
        creatures = [c for c in hand if c.has(Tag.CREATURE)]
        dead = [c for c in hand if c.name in self.DEAD_IN_GOLDFISH]
        ones = [c for c in hand if c.has(Tag.ONE_DROP) and not c.is_land()]
        size = len(hand)

        if size <= 4: return True
        if len(lands) == 0: return False
        if len(lands) == 1 and size >= 6 and mulligans < 3: return False
        if len(lands) > 4: return False
        # MUST have at least 1 creature
        if not creatures and mulligans < 2: return False
        # Too many dead cards = mull
        if len(dead) >= 3 and mulligans < 2: return False

        # Ragavan + land = always keep
        if any(c.name == RAGAVAN for c in hand) and len(lands) >= 1:
            return True
        # 2 lands + 1-drop = keep
        if len(lands) >= 2 and ones:
            return True
        # 2 lands + creatures = keep
        if len(lands) >= 2 and len(creatures) >= 2:
            return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        dead = [c for c in hand if c.name in self.DEAD_IN_GOLDFISH]
        spells = sorted([c for c in hand if not c.is_land() and c.name not in self.DEAD_IN_GOLDFISH],
                        key=lambda c: -c.cmc)
        to_bottom = []
        # Dead goldfish cards first
        to_bottom.extend(dead)
        # Excess lands
        if len(lands) > 3:
            to_bottom.extend(lands[3:])
        # High CMC spells
        for card in spells:
            if len(to_bottom) >= n: break
            if card.cmc >= 3 and card not in to_bottom:
                to_bottom.append(card)
        for card in spells:
            if len(to_bottom) >= n: break
            if card not in to_bottom:
                to_bottom.append(card)
        return to_bottom[:n]

    def _best_land(self, gs: GameState) -> Optional[Card]:
        """Fetch > Shock > Arena of Glory > Elegant Parlor > basics > utility."""
        lands = [c for c in gs.hand() if c.is_land()]
        if not lands: return None
        if len(lands) == 1: return lands[0]

        def score(c):
            n = c.name.lower()
            # Fetches first — they find shocks and thin the deck
            if n in ("arid mesa", "flooded strand", "marsh flats", "windswept heath"):
                return 0
            if n in ("sacred foundry",):
                return 1
            if n in ("arena of glory",):
                return 2  # R/W fast land
            if n in ("elegant parlor",):
                return 3  # tap land but fixes colors
            if n == "mountain" or n == "plains":
                return 4
            if n in ("dalkovan encampment",):
                return 5
            return 6
        return min(lands, key=score)

    def _simulate_ocelot_tokens(self, gs: GameState, num_attackers: int):
        """
        Ocelot Pride: when a creature you control deals combat damage to a player
        for the first time each turn, create a 1/1 white Cat creature token.
        In goldfish, every attacker deals damage, so each Ocelot creates tokens
        equal to the number of OTHER creatures that dealt damage.
        Simplified: each Ocelot in play → 1 token per attacking non-Ocelot creature.
        """
        ocelots = sum(1 for c in gs.zones.creatures_on_battlefield()
                      if c.name == OCELOT_PRIDE or c.name == "Cat Token")
        # Each creature dealing damage for the first time creates a token per Ocelot
        # But Ocelot itself also attacks and triggers off others
        if ocelots > 0 and num_attackers > 0:
            # Each Ocelot sees (attackers - itself) creatures dealing damage first time
            # Plus Ocelot's own first damage triggers other Ocelots
            tokens_created = ocelots * max(1, num_attackers - ocelots) + max(0, ocelots - 1)
            tokens_created = min(tokens_created, num_attackers)  # cap at attackers
            for _ in range(tokens_created):
                token = gs._make_token("Cat Token", "1", "1", "Creature — Cat")
                token.summoning_sickness = False  # enters tapped and attacking (effectively)
                self._trigger_ajani_growth(gs)
            if tokens_created:
                gs._log(f"  Ocelot Pride: created {tokens_created} Cat token(s)")

    def _trigger_ajani_growth(self, gs: GameState):
        """Ajani grows +1/+1 when a token enters."""
        for c in gs.zones.battlefield:
            if c.name == AJANI and not getattr(c, "_flipped", False):
                c.counters += 1
                # Flip at 3+ counters (simplified)
                if c.counters >= 3:
                    c._flipped = True
                    c.power = "4"
                    c.toughness = "4"
                    c.type_line = "Legendary Planeswalker — Ajani"
                    gs._log(f"  Ajani flips → planeswalker (4/4)")

    def _simulate_ragavan_treasure(self, gs: GameState):
        """Ragavan creates a Treasure token on combat damage to a player."""
        from engine.keywords import KWTag
        ragavans_attacking = sum(
            1 for c in gs.zones.creatures_on_battlefield()
            if c.name == RAGAVAN and (not c.summoning_sickness or KWTag.HASTE in c.tags)
        )
        if ragavans_attacking > 0:
            self._treasures += ragavans_attacking
            gs._log(f"  Ragavan: +{ragavans_attacking} Treasure(s) (total: {self._treasures})")
            # Each treasure triggers Ajani
            for _ in range(ragavans_attacking):
                self._trigger_ajani_growth(gs)

    def _bombardment_finish(self, gs: GameState):
        """Use Goblin Bombardment to sacrifice creatures for lethal."""
        bombardments = [c for c in gs.zones.battlefield if c.name == GOBLIN_BOMBARD]
        if not bombardments:
            return
        remaining = 20 - gs.damage_dealt
        if remaining <= 0:
            return
        # Sacrifice creatures for 1 damage each (tokens first)
        sacrificeable = sorted(
            [c for c in gs.zones.creatures_on_battlefield()],
            key=lambda c: (0 if "Token" in c.name else 1, c.effective_power())
        )
        sacrificed = 0
        for creature in list(sacrificeable):
            if gs.damage_dealt >= 20:
                break
            if creature in gs.zones.battlefield:
                gs.zones.battlefield.remove(creature)
                gs.zones.graveyard.append(creature)
                gs.damage_dealt += 1
                sacrificed += 1
        if sacrificed:
            gs._log(f"  Bombardment: sacrificed {sacrificed} creatures "
                    f"({gs.damage_dealt} total dmg)")

    def main_phase(self, gs: GameState):
        """
        Pre-combat: play land, cast creatures that benefit from attacking now.
        Ragavan (haste) and Screaming Nemesis (haste) should be cast pre-combat.
        """
        from engine.keywords import KWTag

        # Reset per-turn state
        self._ocelot_triggered_this_turn = False

        # Treasure mana (Ragavan) — add to pool
        if self._treasures > 0:
            available = min(self._treasures, 3)  # use up to 3 treasures per turn
            for _ in range(available):
                gs.mana_pool.flex += 1
                self._treasures -= 1
            if available:
                gs._log(f"  Cracked {available} Treasure(s) for mana")

        # 1. Land
        self._play_land_if_able(gs)

        # 2. Haste creatures pre-combat (they attack this turn)
        for name in (RAGAVAN, SCREAMING_NEMESIS):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs._log(f"  [PRE-COMBAT] {card.name} (haste — attacks now)")
                    gs.cast_spell(card)
                    break

        # 3. Goblin Bombardment (enchantment, cast early for later value)
        for card in list(gs.hand()):
            if card.name == GOBLIN_BOMBARD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

        # 4. Creatures that grow from combat (Ajani wants tokens from Ocelot)
        #    Cast Ajani pre-combat if Ocelot is attacking (tokens grow Ajani)
        has_attacking_ocelot = any(
            c.name == OCELOT_PRIDE and not c.summoning_sickness
            for c in gs.zones.creatures_on_battlefield()
        )
        if has_attacking_ocelot:
            for card in list(gs.hand()):
                if card.name == AJANI and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs._log(f"  [PRE-COMBAT] Ajani (will grow from Ocelot tokens)")
                    gs.cast_spell(card)
                    break

        # 5. Thraben Charm — +1/+2 pump on best attacker pre-combat
        attackers = [
            c for c in gs.zones.creatures_on_battlefield()
            if not c.summoning_sickness or hasattr(c, 'tags') and 'haste' in c.tags
        ]
        if attackers:
            for card in list(gs.hand()):
                if card.name == THRABEN_CHARM and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    best = max(attackers, key=lambda c: c.effective_power())
                    # +1/+2 until EOT — model as temporary counter
                    best.counters += 1  # +1 power for this combat
                    best._thraben_boost = True
                    gs.cast_spell(card)
                    gs._log(f"  [PRE-COMBAT] Thraben Charm: +1/+2 on {best.name}")
                    break

        # 6. Static Prison — cast for 2 energy (no target needed in goldfish)
        for card in list(gs.hand()):
            if card.name == STATIC_PRISON and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.energy += 2
                gs._log(f"  Static Prison: +2 energy ({gs.energy} total)")
                break

    def main_phase2(self, gs: GameState):
        """
        Post-combat:
        1. Simulate Ocelot Pride tokens (created during combat)
        2. Simulate Ragavan treasure
        3. Cast remaining creatures
        4. Bombardment sacrifice for lethal if possible
        """
        from engine.keywords import KWTag

        # Count attackers that just dealt damage
        attackers = [
            c for c in gs.zones.creatures_on_battlefield()
            if not c.summoning_sickness or KWTag.HASTE in c.tags
        ]
        num_attackers = len(attackers)

        # Simulate combat triggers
        if num_attackers > 0:
            self._simulate_ocelot_tokens(gs, num_attackers)
            self._simulate_ragavan_treasure(gs)

        # Cast remaining creatures (summoning sick, doesn't matter)
        priority = (OCELOT_PRIDE, AJANI, GUIDE_OF_SOULS, RAGAVAN)
        for name in priority:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Voice of Victory (creates tokens)
        for card in list(gs.hand()):
            if card.name == VOICE_OF_VICTORY and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

        # Phlage — 3 damage ETB (always bolt face in goldfish)
        for card in list(gs.hand()):
            if card.name == PHLAGE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.damage_dealt += 3
                gs.life += 3
                gs._log(f"  Phlage ETB: 3 dmg to face ({gs.damage_dealt} total), gain 3 life")
                break

        # Seasoned Pyromancer (draw engine + tokens)
        for card in list(gs.hand()):
            if card.name == SEASONED_PYRO and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Simplified: creates 2x 1/1 tokens
                gs._make_token("Elemental Token", "1", "1", "Creature — Elemental")
                gs._make_token("Elemental Token", "1", "1", "Creature — Elemental")
                gs._log(f"  Seasoned Pyromancer: 2x 1/1 Elemental tokens")
                self._trigger_ajani_growth(gs)
                self._trigger_ajani_growth(gs)
                break

        # Fill curve — any remaining castable creature
        while True:
            creatures = [
                c for c in gs.hand()
                if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            ]
            if not creatures: break
            card = min(creatures, key=lambda c: (c.cmc, c.name))
            if not gs.cast_spell(card): break

        # Non-creature spells (removal — goldfish: less relevant)
        for card in list(gs.hand()):
            if (card.name in (LIGHTNING_BOLT,) and
                gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                # Bolt face in goldfish
                gs.cast_spell(card)
                gs.damage_dealt += 3
                gs._log(f"  Lightning Bolt to face (3 dmg, {gs.damage_dealt} total)")
                break

        # Galvanic Discharge — cast for energy generation
        # Get 2 energy, pay 0, target own creature with toughness > 2 (survives)
        # Or target own token (it dies but you got the energy)
        for card in list(gs.hand()):
            if card.name == GALVANIC and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.energy += 2
                # Find a target that survives (toughness > 2) or a token we don't mind losing
                target = None
                # Prefer targeting creature with toughness > 2 (survives)
                survivors = [c for c in gs.zones.creatures_on_battlefield()
                             if c.effective_toughness() > 2]
                tokens = [c for c in gs.zones.creatures_on_battlefield()
                          if "Token" in c.name]
                if survivors:
                    target = survivors[0]
                    gs.cast_spell(card)
                    gs._log(f"  Galvanic Discharge: +2 energy ({gs.energy}), "
                            f"2 dmg to own {target.name} (survives)")
                elif tokens:
                    target = tokens[0]
                    gs.zones.battlefield.remove(target)
                    gs.zones.graveyard.append(target)
                    gs.cast_spell(card)
                    gs._log(f"  Galvanic Discharge: +2 energy ({gs.energy}), "
                            f"sacrificed {target.name}")
                elif gs.zones.creatures_on_battlefield():
                    # Last resort: don't cast if it kills our only threats
                    # Only cast if we have 3+ creatures (can afford to lose one)
                    if len(gs.zones.creatures_on_battlefield()) >= 3:
                        target = min(gs.zones.creatures_on_battlefield(),
                                     key=lambda c: c.effective_power())
                        gs.zones.battlefield.remove(target)
                        gs.zones.graveyard.append(target)
                        gs.cast_spell(card)
                        gs._log(f"  Galvanic Discharge: +2 energy ({gs.energy}), "
                                f"killed own {target.name}")
                break

        # Bombardment finish — sacrifice tokens/creatures for lethal
        self._bombardment_finish(gs)
