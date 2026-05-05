"""
apl/sultai_reanimator_standard_match.py — Sultai Reanimator (Standard)

Current-meta Sultai Reanimator from yukiro 2026-03-31 (2nd place).
Plan:
  T1-2 Self-mill / cycle (Deceit, Dredger's Insight) to fill the
       graveyard with big creatures.
  T3-4 Cast Bringer of the Last Gift — {3}{B}{B} ETB reanimates a
       creature from your graveyard. Works great with Overlord of the
       Balemurk (impending, comes back bigger), Kavaero, Formidable
       Speaker.
  T5+  Overlord of the Balemurk (impending — cast for cheap at some
       cost, or hard-cast as a 6/6 flying finisher).
  Support: Awaken the Honored Dead as a backup reanimate spell,
  Requiting Hex for mill-removal, Bitter Triumph as unconditional kill.

Engine approximation: we don't fully model reanimate triggers, but
we DO model the plan by treating discard spells as draw+1 (card
selection) and Bringer as a "return biggest creature from GY" ETB.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness


# Discard / looting engine
DECEIT           = "Deceit"
DREDGERS_INSIGHT = "Dredger's Insight"
REQUITING_HEX    = "Requiting Hex"

# Reanimator core
BRINGER          = "Bringer of the Last Gift"
BALEMURK         = "Overlord of the Balemurk"
AWAKEN_DEAD      = "Awaken the Honored Dead"
SPIDERMAN        = "Superior Spider-Man"   # enters as copy of target GY creature

# Removal
BITTER_TRIUMPH   = "Bitter Triumph"

# Threats / value creatures
KAVAERO          = "Kavaero, Mind-Bitten"
FORMIDABLE       = "Formidable Speaker"
ARDYN            = "Ardyn, the Usurper"
WISTFULNESS      = "Wistfulness"
BOOKWORM         = "Oblivious Bookworm"    # ETB mill 3
HARVESTER        = "Harvester of Misery"
ARMAGGON         = "Armaggon, Future Shark"


CREATURES = {BRINGER, BALEMURK, KAVAERO, FORMIDABLE, ARDYN, BOOKWORM, HARVESTER, ARMAGGON}
LOOT_SPELLS = {DECEIT, DREDGERS_INSIGHT, WISTFULNESS}
REMOVAL_SPELLS = {BITTER_TRIUMPH, REQUITING_HEX}


class SultaiReanimatorStandardMatchAPL(MatchAPL):
    ARCHETYPE = "combo"
    name = "Sultai Reanimator (Standard)"
    win_condition_damage = 20
    max_turns = 14

    # Sideboard from Ishii Hiroyuki PT Lorwyn Eclipsed list
    SB_PLANS = {
        "aggro": (
            # vs Aggro/Red: Glarb lifegain; Nowhere to Run removal; Urgent Necropsy exile
            ["Glarb, Calamity's Augur", "Glarb, Calamity's Augur",
             "Nowhere to Run", "Nowhere to Run", "Urgent Necropsy"],
            [ARMAGGON, HARVESTER, WISTFULNESS, "Disruptive Stormbrood",
             "Disruptive Stormbrood"],
        ),
        "control": (
            # vs Control: Disdainful Stroke for big spells; Spider-Sense for interaction
            ["Disdainful Stroke", "Disdainful Stroke",
             "Glarb, Calamity's Augur", "Glarb, Calamity's Augur", "Spider-Sense"],
            [BITTER_TRIUMPH, BITTER_TRIUMPH, BITTER_TRIUMPH,
             BALEMURK, "Disruptive Stormbrood"],
        ),
        "ramp": (
            # vs Rhythm: Nowhere to Run removes Craterhoof; Insidious Fungus disrupts
            ["Nowhere to Run", "Nowhere to Run",
             "Insidious Fungus", "Insidious Fungus", "Urgent Necropsy"],
            [ARMAGGON, HARVESTER, WISTFULNESS,
             "Disruptive Stormbrood", "Disruptive Stormbrood"],
        ),
        "combo": (
            # vs Izzet Lessons: Disdainful Stroke; Glarb for grinding
            ["Disdainful Stroke", "Disdainful Stroke",
             "Glarb, Calamity's Augur", "Glarb, Calamity's Augur",
             "Zero Point Ballad", "Zero Point Ballad"],
            [BITTER_TRIUMPH, BITTER_TRIUMPH, BITTER_TRIUMPH,
             ARMAGGON, "Disruptive Stormbrood", "Disruptive Stormbrood"],
        ),
        "tempo": (
            # vs Prowess/Spellementals: Disdainful; Nowhere to Run
            ["Disdainful Stroke", "Disdainful Stroke",
             "Nowhere to Run", "Nowhere to Run", "Glarb, Calamity's Augur"],
            [BALEMURK, WISTFULNESS, ARMAGGON,
             "Disruptive Stormbrood", "Disruptive Stormbrood"],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        loot = sum(1 for c in hand if c.name in LOOT_SPELLS)
        reanim = sum(1 for c in hand if c.name in {BRINGER, BALEMURK, AWAKEN_DEAD})
        if lands < 2 or lands > 5:
            return False
        if loot + reanim >= 2:
            return True
        if lands >= 3 and reanim >= 1:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                         key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Reanimator: loot → big creature in GY → reanimate."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Removal on opp's biggest creature
        if opponent:
            self._use_removal(gs, opponent)

        # 2. GY fill: Oblivious Bookworm draws then discards at end step (approximated here)
        # Oracle: "At beginning of your end step, you may draw a card. If you do, discard a card
        # unless a face-down permanent entered this turn." Since we don't model end steps fully,
        # approximate: when Bookworm is on battlefield, discard worst creature to GY each turn.
        for c in gs.zones.battlefield:
            if c.name == BOOKWORM and not c.is_land():
                # End-step draw: draw 1
                if gs.zones.library:
                    gs.zones.draw(1)
                # Discard worst non-Bringer creature to fill GY
                discard_targets = [x for x in gs.zones.hand
                                   if x.name not in {BRINGER, SPIDERMAN, AWAKEN_DEAD}
                                   and x.has(Tag.CREATURE)]
                if discard_targets:
                    worst = min(discard_targets, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.hand.remove(worst)
                    gs.zones.graveyard.append(worst)
                    gs._log(f"  Oblivious Bookworm: draw 1, discard {worst.name} to GY")
                break

        # Deceit / Dredger's Insight as additional GY fill
        for name in (DECEIT, DREDGERS_INSIGHT):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    creatures_in_hand = [x for x in gs.zones.hand if x.has(Tag.CREATURE)]
                    if creatures_in_hand:
                        victim = max(creatures_in_hand, key=lambda x: getattr(x, 'cmc', 0))
                        gs.zones.hand.remove(victim)
                        gs.zones.graveyard.append(victim)
                        gs._log(f"  {name}: discard {victim.name} to GY")
                    break

        # 3a. Superior Spider-Man — enters as copy of Bringer in GY
        # Cast when Bringer is in GY and we have the mana
        bringer_in_gy = any(c.name == BRINGER for c in gs.zones.graveyard if c.has(Tag.CREATURE))
        if bringer_in_gy:
            for c in list(gs.zones.hand):
                if c.name == SPIDERMAN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    # Spider-Man ETB: copy Bringer in GY → treat as another Bringer entering
                    gy_bringer = next((x for x in gs.zones.graveyard if x.name == BRINGER), None)
                    if gy_bringer:
                        gs.zones.graveyard.remove(gy_bringer)
                        gs.zones.battlefield.append(gy_bringer)
                        gy_bringer.summoning_sickness = True
                        gs._log("  Superior Spider-Man: enters as Bringer of the Last Gift")
                    break

        # 3b. Bringer of the Last Gift — ETB reanimate is now wired
        # via engine ETB_EFFECTS registry (pulls biggest creature
        # with CMC ≤ 5 from GY to battlefield).
        for c in list(gs.zones.hand):
            if c.name == BRINGER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Overlord of the Balemurk — prefer impending (2 mana) over
        # hard-cast (5 mana). ETB mill-4-return-to-hand fires either way;
        # impending gets us a Saga-like permanent early and the creature
        # body (5/5) after 5 end steps.
        for c in list(gs.zones.hand):
            if c.name != BALEMURK:
                continue
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
            else:
                gs.cast_spell_impending(c)
            break

        # 5. Awaken the Honored Dead — reanimate spell
        for c in list(gs.zones.hand):
            if c.name == AWAKEN_DEAD and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gy_creatures = [x for x in gs.zones.graveyard
                                 if x.has(Tag.CREATURE)]
                if gy_creatures:
                    target = max(gy_creatures,
                                  key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.graveyard.remove(target)
                    gs.zones.battlefield.append(target)
                    target.turn_entered = gs.turn
                    target.summoning_sickness = True
                    target.tapped = False
                    gs._log(f"  Awaken: reanimate {target.name}")
                break

        # 6. Formidable Speaker ({2G}): ETB discard a card, search library for a creature card
        # Best use: discard a duplicate/bad card, tutor Bringer of the Last Gift to hand
        for c in list(gs.zones.hand):
            if c.name == FORMIDABLE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # ETB: discard worst card to GY, tutor Bringer (or best creature) to hand
                discard_targets = [x for x in gs.zones.hand
                                   if x.name not in {BRINGER, SPIDERMAN, AWAKEN_DEAD}]
                if discard_targets:
                    worst = min(discard_targets, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.hand.remove(worst)
                    gs.zones.graveyard.append(worst)
                    # Tutor: find Bringer in library if not in hand/battlefield
                    bringer_in_hand = any(x.name == BRINGER for x in gs.zones.hand)
                    if not bringer_in_hand:
                        target = next((x for x in gs.zones.library if x.name == BRINGER), None)
                        if target:
                            gs.zones.library.remove(target)
                            gs.zones.hand.append(target)
                            gs._log(f"  Formidable Speaker: discarded {worst.name}, tutored {BRINGER}")
                break

        # 7. Value creatures
        for name in (KAVAERO, ARDYN):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 7. Any remaining castable creature
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _use_removal(self, gs, opponent):
        opp_creatures = [c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2:
            return
        for c in list(gs.zones.hand):
            if c.name not in REMOVAL_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            gs._log(f"  {c.name}: kill {target.name}")
            return

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers:
            return assignments
        blockers = [c for c in gs.zones.battlefield
                     if c.has(Tag.CREATURE) and not c.is_land()
                     and not getattr(c, 'tapped', False)]
        if not blockers:
            return assignments
        biggest_att = max(attackers, key=lambda c: safe_power(c))
        if safe_power(biggest_att) >= 4:
            best_blocker = max(blockers, key=lambda c: safe_toughness(c))
            if safe_toughness(best_blocker) > safe_power(biggest_att):
                assignments[id(biggest_att)] = [best_blocker]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
