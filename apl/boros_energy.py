"""
boros_energy.py — APL for Modern Boros Energy/Ocelot

VERIFIED card interactions (from oracle text):
  - Ragavan: haste, combat damage → Treasure + exile top card. Dash {1}{R}.
  - Ocelot Pride: first_strike, lifelink. END STEP: if you gained life, create
    1/1 Cat token. City's blessing: copy each token that entered this turn.
  - Ajani, Nacatl Pariah: ETB creates 2/1 Cat Warrior token. When 1+ other Cats
    you control die, exile Ajani → return transformed (planeswalker).
  - Guide of Souls: creature enters → gain 1 life + 1 energy.
    Attack trigger: pay 3E → +2/+2 and flying counter on attacker.
  - Goblin Bombardment: sac creature → 1 damage to any target.
  - Voice of Victory: Mobilize 2 (2x 1/1 tapped attacking Warriors, sac EOT).
  - Seasoned Pyromancer: ETB discard 2, draw 2. Per nonland discarded → 1/1 Elemental.
  - Phlage: {1}{R}{W}. ETB/attack → 3 damage any target + gain 3 life.
    Sacrifice on ETB unless escaped. Escape {R}{R}{W}{W} + exile 5 from GY.
    Hard cast = 3-mana Lightning Helix that goes to GY for later escape.
    Escape = 4-mana 6/6 that deals 3 + stays on board.
  - Galvanic Discharge: get {E}{E}{E}, then pay any amount of {E} → that much damage
    to target creature/PW. Goldfish: target own creature, pay 0 → +3 energy net.
  - Thraben Charm: 2x creature count damage to target CREATURE / destroy enchantment /
    exile graveyards. All modes are dead in goldfish.
  - Static Prison: exile opponent's nonland permanent (can't cast in goldfish).
    Gives {E}{E} but requires a target.
  - Screaming Nemesis: 3/3 haste.
  - Lightning Bolt: 3 damage any target.
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

    # Per-game state (reset each game)
    _treasures = 0
    _gained_life_this_turn = False
    _tokens_entered_this_turn = 0

    # Cards that literally cannot be cast in goldfish (no valid target)
    DEAD_IN_GOLDFISH = {STATIC_PRISON, "Exorcise"}
    # Cards with very limited goldfish value (creature-only removal, no face)
    LOW_VALUE_GOLDFISH = {THRABEN_CHARM, GALVANIC}

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        lands = [c for c in hand if c.is_land()]
        creatures = [c for c in hand if c.has(Tag.CREATURE)]
        dead = [c for c in hand if c.name in self.DEAD_IN_GOLDFISH]
        low = [c for c in hand if c.name in self.LOW_VALUE_GOLDFISH]
        ones = [c for c in hand if c.has(Tag.ONE_DROP) and not c.is_land()]
        size = len(hand)

        if size <= 4: return True
        if len(lands) == 0: return False
        if len(lands) == 1 and size >= 6 and mulligans < 3: return False
        if len(lands) > 4: return False
        if not creatures and mulligans < 2: return False
        # Too many dead/low value = mull
        if len(dead) + len(low) >= 3 and mulligans < 2: return False

        if any(c.name == RAGAVAN for c in hand) and len(lands) >= 1: return True
        if len(lands) >= 2 and ones: return True
        if len(lands) >= 2 and len(creatures) >= 2: return True
        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        dead = [c for c in hand if c.name in self.DEAD_IN_GOLDFISH]
        low = [c for c in hand if c.name in self.LOW_VALUE_GOLDFISH]
        spells = sorted([c for c in hand if not c.is_land()
                         and c.name not in self.DEAD_IN_GOLDFISH
                         and c.name not in self.LOW_VALUE_GOLDFISH],
                        key=lambda c: -c.cmc)
        to_bottom = []
        to_bottom.extend(dead)
        to_bottom.extend(low)
        if len(lands) > 3:
            to_bottom.extend(lands[3:])
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
        lands = [c for c in gs.hand() if c.is_land()]
        if not lands: return None
        if len(lands) == 1: return lands[0]
        def score(c):
            n = c.name.lower()
            if n in ("arid mesa", "flooded strand", "marsh flats", "windswept heath"):
                return 0  # fetches first
            if n in ("sacred foundry",): return 1
            if n in ("arena of glory",): return 2
            if n in ("elegant parlor",): return 3
            if n in ("mountain", "plains"): return 4
            if n in ("dalkovan encampment",): return 5
            return 6
        return min(lands, key=score)

    # ------------------------------------------------------------------
    # Combat trigger simulation
    # ------------------------------------------------------------------

    def _simulate_combat_triggers(self, gs: GameState, num_attackers: int):
        """After combat: Ragavan treasure, Phlage bolt, Ocelot lifelink."""
        from engine.keywords import KWTag

        # Ragavan: each one that attacked creates a Treasure
        ragavans = sum(1 for c in gs.zones.creatures_on_battlefield()
                       if c.name == RAGAVAN
                       and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if ragavans > 0:
            self._treasures += ragavans
            gs._log(f"  Ragavan: +{ragavans} Treasure(s) ({self._treasures} total)")

        # Phlage attack trigger: escaped Phlage deals 3 damage + 3 life on attack
        phlages_attacking = sum(1 for c in gs.zones.creatures_on_battlefield()
                                if c.name == PHLAGE
                                and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if phlages_attacking > 0:
            dmg = 3 * phlages_attacking
            gs.damage_dealt += dmg
            gs.life += dmg
            self._gained_life_this_turn = True
            gs._log(f"  Phlage attack trigger: {dmg} dmg ({gs.damage_dealt} total), +{dmg} life")

        # Ocelot Pride has lifelink — any Ocelot that attacked gained us life
        ocelots_attacked = sum(1 for c in gs.zones.creatures_on_battlefield()
                               if c.name == OCELOT_PRIDE
                               and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if ocelots_attacked > 0:
            self._gained_life_this_turn = True

    def _simulate_guide_attack_trigger(self, gs: GameState):
        """Guide of Souls: when you attack, pay 3E → +2/+2 flying on an attacker."""
        from engine.keywords import KWTag
        guides_attacking = sum(1 for c in gs.zones.creatures_on_battlefield()
                               if c.name == GUIDE_OF_SOULS
                               and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if guides_attacking > 0 and gs.energy >= 3:
            # Find best attacker to pump
            attackers = [c for c in gs.zones.creatures_on_battlefield()
                         if not c.summoning_sickness or KWTag.HASTE in c.tags]
            if attackers:
                best = max(attackers, key=lambda c: c.effective_power())
                gs.energy -= 3
                best.counters += 2  # +2/+2
                gs._log(f"  Guide of Souls: paid 3E → +2/+2 flying on {best.name} "
                        f"(energy: {gs.energy})")

    def _simulate_end_step(self, gs: GameState):
        """End step: Ocelot Pride creates Cat token if we gained life."""
        ocelots = sum(1 for c in gs.zones.creatures_on_battlefield()
                      if c.name == OCELOT_PRIDE)
        if ocelots > 0 and self._gained_life_this_turn:
            for _ in range(ocelots):
                token = gs._make_token("Cat Token", "1", "1", "Creature — Cat")
                self._tokens_entered_this_turn += 1
                # Guide of Souls triggers on token entering: +1 life +1 energy
                guides = sum(1 for c in gs.zones.battlefield
                             if c.name == GUIDE_OF_SOULS)
                if guides:
                    gs.life += guides
                    gs.energy += guides
                    self._gained_life_this_turn = True  # life gain chains more Ocelots? No, already in end step
            gs._log(f"  Ocelot Pride: {ocelots} Cat token(s) (gained life this turn)")

    def _simulate_ajani_etb(self, gs: GameState):
        """Ajani ETB: create a 2/1 Cat Warrior token."""
        token = gs._make_token("Cat Warrior Token", "2", "1", "Creature — Cat Warrior")
        self._tokens_entered_this_turn += 1
        # Guide triggers on token entering
        guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
        if guides:
            gs.life += guides
            gs.energy += guides
            self._gained_life_this_turn = True
        gs._log(f"  Ajani ETB: 2/1 Cat Warrior token")

    def _bombardment_finish(self, gs: GameState):
        """Sacrifice creatures to Goblin Bombardment ONLY if lethal."""
        if not any(c.name == GOBLIN_BOMBARD for c in gs.zones.battlefield):
            return
        remaining = 20 - gs.damage_dealt
        if remaining <= 0: return
        sacrificeable = [c for c in gs.zones.creatures_on_battlefield()]
        # Only sac if we have enough creatures to deal lethal
        if len(sacrificeable) < remaining:
            return
        # Sort: tokens first, lowest power first
        sacrificeable.sort(key=lambda c: (0 if "Token" in c.name else 1, c.effective_power()))
        sacrificed = 0
        for creature in list(sacrificeable):
            if gs.damage_dealt >= 20: break
            if creature in gs.zones.battlefield:
                gs.zones.battlefield.remove(creature)
                gs.zones.graveyard.append(creature)
                gs.damage_dealt += 1
                sacrificed += 1
                # Cat dying may trigger Ajani transform
        if sacrificed:
            gs._log(f"  Bombardment: sac'd {sacrificed} ({gs.damage_dealt} total dmg)")

    # ------------------------------------------------------------------
    # Main phases
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        """Pre-combat: land, haste creatures, Arena of Glory haste, Guide pump."""
        from engine.keywords import KWTag

        # Reset per-turn tracking
        self._gained_life_this_turn = False
        self._tokens_entered_this_turn = 0

        # Treasure mana
        if self._treasures > 0:
            use = min(self._treasures, 3)
            gs.mana_pool.flex += use
            self._treasures -= use
            if use: gs._log(f"  Cracked {use} Treasure(s)")

        # 1. Land
        self._play_land_if_able(gs)

        # 2. Haste creatures pre-combat (attack this turn)
        for name in (RAGAVAN, SCREAMING_NEMESIS):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs._log(f"  [PRE-COMBAT] {card.name} (haste)")
                    gs.cast_spell(card)
                    break

        # 3. Arena of Glory — exert to give haste to a creature cast this turn
        #    Pay {R}, tap, exert: add {R}{R}. If spent on creature → haste.
        #    Perfect player: use Arena mana to cast a non-haste creature pre-combat.
        arena = next((c for c in gs.zones.lands_on_battlefield()
                      if c.name == "Arena of Glory" and not c.tapped), None)
        if arena:
            # Find a non-haste creature we could cast with the extra R
            # Arena gives RR when exerted (net +1R since it costs R to activate)
            castable_with_haste = []
            for card in gs.hand():
                if (card.has(Tag.CREATURE)
                    and KWTag.HASTE not in card.tags
                    and card.name not in (RAGAVAN, SCREAMING_NEMESIS)
                    and card.summoning_sickness != False):  # not already on BF
                    # Can we cast it with current pool + the extra R from Arena?
                    # Arena exert: pay R, get RR (net +1R). But arena is untapped so
                    # its base tap wasn't used yet. Exert = tap for RR instead of R.
                    test_total = gs.mana_pool.total() + 1  # +1 net from exert
                    if card.cmc <= test_total:
                        castable_with_haste.append(card)

            if castable_with_haste:
                # Pick best creature to give haste (highest power)
                best = max(castable_with_haste, key=lambda c: (
                    int(c.power or 0), -c.cmc))
                # Exert Arena: tap it, add RR to pool
                arena.tapped = True
                arena._exerted = True  # won't untap next turn
                gs.mana_pool.add("R", 2)
                # Cast the creature
                if gs.mana_pool.can_cast(best.mana_cost, best.cmc):
                    gs.cast_spell(best)
                    best.summoning_sickness = False  # HASTE from Arena
                    gs._log(f"  [PRE-COMBAT] Arena of Glory exert → {best.name} has HASTE")
                    # Guide triggers on creature entering
                    guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
                    if guides:
                        gs.life += guides
                        gs.energy += guides
                        self._gained_life_this_turn = True

        # 4. Goblin Bombardment (set up sac outlet early)
        for card in list(gs.hand()):
            if card.name == GOBLIN_BOMBARD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

        # 5. Ajani pre-combat — 2/1 token triggers Guide
        for card in list(gs.hand()):
            if card.name == AJANI and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                self._simulate_ajani_etb(gs)
                break

        # 6. Guide of Souls attack trigger — pay 3E for +2/+2 flying
        self._simulate_guide_attack_trigger(gs)

        # 7. Galvanic Discharge — cast for +3 energy
        for card in list(gs.hand()):
            if card.name == GALVANIC and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                creatures = gs.zones.creatures_on_battlefield()
                if creatures:
                    gs.energy += 3
                    gs.cast_spell(card)
                    gs._log(f"  Galvanic: +3 energy ({gs.energy}), 0 dmg to own creature")
                break

    def main_phase2(self, gs: GameState):
        """Post-combat: simulate combat triggers, cast remaining, end step tokens."""
        from engine.keywords import KWTag

        # Count attackers that dealt damage
        attackers = [c for c in gs.zones.creatures_on_battlefield()
                     if not c.summoning_sickness or KWTag.HASTE in c.tags]
        num_attackers = len(attackers)

        # Combat triggers (Ragavan treasure, Ocelot lifelink)
        if num_attackers > 0:
            self._simulate_combat_triggers(gs, num_attackers)

        # Guide of Souls: each creature entering triggers +1 life +1 energy
        # (this happens when we cast creatures post-combat too)

        # Cast remaining creatures
        priority = (OCELOT_PRIDE, GUIDE_OF_SOULS, AJANI, VOICE_OF_VICTORY, RAGAVAN)
        for name in priority:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Ajani ETB
                    if name == AJANI:
                        self._simulate_ajani_etb(gs)
                    # Guide triggers for any creature entering
                    guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
                    if guides and card.has(Tag.CREATURE):
                        gs.life += guides
                        gs.energy += guides
                        self._gained_life_this_turn = True
                        gs._log(f"  Guide trigger: +{guides} life, +{guides} energy")
                    break

        # Seasoned Pyromancer: discard 2, draw 2, tokens per nonland discarded
        for card in list(gs.hand()):
            if card.name == SEASONED_PYRO and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Discard 2: prefer discarding lands/dead cards
                hand = list(gs.zones.hand)
                discardable = sorted(hand, key=lambda c: (
                    0 if c.name in self.DEAD_IN_GOLDFISH else
                    1 if c.is_land() else
                    2 if c.name in self.LOW_VALUE_GOLDFISH else 3
                ))
                discarded_nonlands = 0
                for i, c in enumerate(discardable[:2]):
                    if c in gs.zones.hand:
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        if not c.is_land():
                            discarded_nonlands += 1
                gs.zones.draw(2)
                for _ in range(discarded_nonlands):
                    token = gs._make_token("Elemental Token", "1", "1", "Creature — Elemental")
                    self._tokens_entered_this_turn += 1
                    guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
                    if guides:
                        gs.life += guides
                        gs.energy += guides
                        self._gained_life_this_turn = True
                gs._log(f"  Pyromancer: discard 2, draw 2, {discarded_nonlands} Elemental(s)")
                break

        # Phlage — hardcast {1}{R}{W}: 3 damage + 3 life, then SACRIFICE (didn't escape)
        # Scryfall data is bugged (CMC 0) so we check mana manually
        for card in list(gs.hand()):
            if card.name == PHLAGE and gs.mana_pool.can_pay("{1}{R}{W}", 3):
                gs.mana_pool.pay("{1}{R}{W}", 3)
                gs.zones.remove_from_hand(card)
                gs.zones.battlefield.append(card)
                card.turn_entered = gs.turn
                gs.damage_dealt += 3
                gs.life += 3
                self._gained_life_this_turn = True
                # Sacrifice — didn't escape from hand
                if card in gs.zones.battlefield:
                    gs.zones.battlefield.remove(card)
                    gs.zones.graveyard.append(card)
                gs._log(f"  Phlage hardcast: 3 dmg ({gs.damage_dealt}), +3 life, sacrificed (to GY for escape)")
                break

        # Phlage Escape — check graveyard for Phlage + 5 other cards + {R}{R}{W}{W}
        phlage_in_gy = next((c for c in gs.zones.graveyard if c.name == PHLAGE), None)
        other_gy_cards = [c for c in gs.zones.graveyard if c.name != PHLAGE]
        if (phlage_in_gy and len(other_gy_cards) >= 5
            and gs.mana_pool.can_pay("{R}{R}{W}{W}", 4)):
            gs.mana_pool.pay("{R}{R}{W}{W}", 4)
            # Exile 5 cards from GY
            for c in other_gy_cards[:5]:
                gs.zones.graveyard.remove(c)
                gs.zones.exile.append(c)
            # Move Phlage to battlefield (escaped — stays)
            gs.zones.graveyard.remove(phlage_in_gy)
            gs.zones.battlefield.append(phlage_in_gy)
            phlage_in_gy.turn_entered = gs.turn
            phlage_in_gy.summoning_sickness = True
            phlage_in_gy.power = "6"
            phlage_in_gy.toughness = "6"
            gs.damage_dealt += 3
            gs.life += 3
            self._gained_life_this_turn = True
            gs._log(f"  Phlage ESCAPED: 3 dmg ({gs.damage_dealt}), +3 life, 6/6 stays")

        # Fill curve
        while True:
            creatures = [c for c in gs.hand()
                         if c.has(Tag.CREATURE)
                         and c.name not in self.DEAD_IN_GOLDFISH
                         and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if not creatures: break
            card = min(creatures, key=lambda c: (c.cmc, c.name))
            if not gs.cast_spell(card): break
            guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
            if guides:
                gs.life += guides
                gs.energy += guides
                self._gained_life_this_turn = True

        # Lightning Bolt face
        for card in list(gs.hand()):
            if card.name == LIGHTNING_BOLT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs.damage_dealt += 3
                gs._log(f"  Bolt face: 3 dmg ({gs.damage_dealt} total)")
                break

        # End step: Ocelot Pride tokens if we gained life
        self._simulate_end_step(gs)

        # Bombardment: try to sac for lethal
        self._bombardment_finish(gs)
