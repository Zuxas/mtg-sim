"""
apl/grixis_elementals_standard_match.py -- Grixis Elementals match APL (Standard 2026)

Filipe Sousa, European Magic Tour winner. U/B/R control with Elemental synergies.

Key cards:
  Requiting Hex {1B}:          instant exile any creature (primary removal)
  Deceit {2UB}:                bounce permanent + draw (repeatable interaction)
  Not Dead After All {B}:      protection instant -- creature that dies returns to battlefield
                                + Wicked Role token. Keeps Sunderflock alive.
  Superior Spider-Man {2UB}:   Mind Swap: enters as copy of any GY creature
  Sunderflock {7UU-discount}:  ETB bounces ALL non-Elemental permanents (board reset)
  Overlord of the Balemurk {3BB}: Impending 5 counter; becomes 5/5 flying Avatar
  Ashling, Rekindled:          Elemental creature (recursive threat; not in oracle DB)
  Vibrance {3R/G}:             Elemental -- 3 damage to any target (R) OR tutor land (G)
  Wistfulness {3G/U}:          remove artifact/enchantment (G) OR draw 2 (U)

Sideboard:
  Clarion Conqueror {2W}: Dragon flying; shuts ALL activated abilities of permanents
  Intimidation Tactics {B}: reveal hand, exile best artifact/creature card
  Soul-Guide Lantern: GY hate
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

REQUITING_HEX = "Requiting Hex"
DECEIT        = "Deceit"
NOT_DEAD      = "Not Dead After All"
SPIDERMAN     = "Superior Spider-Man"
SUNDERFLOCK   = "Sunderflock"
OVERLORD      = "Overlord of the Balemurk"
ASHLING       = "Ashling, Rekindled"
VIBRANCE      = "Vibrance"
WISTFULNESS   = "Wistfulness"
HARVESTER     = "Harvester of Misery"
BEZA          = "Beza, the Bounding Spring"

CLARION       = "Clarion Conqueror"
INTIM_TACTICS = "Intimidation Tactics"
QUANTUM       = "Quantum Riddler"
SOUL_GUIDE    = "Soul-Guide Lantern"
SPIDER_SENSE  = "Spider-Sense"
DURESS        = "Duress"

KILL_PRIORITY = (
    "Mightform Harmonizer",    # combo kill piece
    "Gran-Gran",               # Monument enabler
    "Icetill Explorer",        # landfall chain
    "Badgermole Cub",          # ramp
    "Stormchaser's Talent",    # Prowess engine
    "Llanowar Elves",          # mana dork
)

# Elementals (not bounced by Sunderflock)
ELEMENTALS = {SUNDERFLOCK, ASHLING, VIBRANCE, WISTFULNESS, HARVESTER,
              "Eddymurk Crab", "Hearth Elemental", "Colorstorm Stallion"}


class GrixisElementalsStandardMatchAPL(AwareMatchAPL):
    name = "Grixis Elementals"
    ARCHETYPE = "control"

    # Hold 4 for Deceit {2UB}; Requiting Hex {1B} = 2 mana
    COUNTER_COST  = 4
    COUNTER_CARDS = set()

    MATCH_REMOVAL = {
        REQUITING_HEX: ("1B", None),  # instant exile, any size
        DECEIT:        ("2UB", None), # bounce + draw
    }
    MATCH_BOUNCE = {DECEIT}
    MATCH_EXILE  = {REQUITING_HEX}

    SB_PLANS = {
        "aggro": (
            # vs Red/Aggro: Clarion shuts activated abilities; Beza lifegain
            [CLARION, CLARION, CLARION, BEZA, SOUL_GUIDE, SOUL_GUIDE],
            [ASHLING, ASHLING, VIBRANCE, VIBRANCE, WISTFULNESS, WISTFULNESS],
        ),
        "ramp": (
            # vs Rhythm: Clarion shuts Gene Pollinator + Formidable Speaker tap abilities
            [CLARION, CLARION, CLARION, SOUL_GUIDE, SOUL_GUIDE, SPIDER_SENSE],
            [ASHLING, ASHLING, VIBRANCE, VIBRANCE, WISTFULNESS, WISTFULNESS],
        ),
        "tempo": (
            # vs Izzet Prowess/Spellementals: Intimidation Tactics exiles their best threat
            [INTIM_TACTICS, QUANTUM, QUANTUM, SOUL_GUIDE, SOUL_GUIDE],
            [ASHLING, ASHLING, VIBRANCE, WISTFULNESS, BEZA],
        ),
        "combo": (
            # vs Izzet Lessons: Soul Guide GY hate; Duress strips counters
            [SOUL_GUIDE, SOUL_GUIDE, DURESS, QUANTUM, QUANTUM, SPIDER_SENSE],
            [ASHLING, ASHLING, VIBRANCE, VIBRANCE, WISTFULNESS, WISTFULNESS],
        ),
        "control": (
            # vs Control mirrors: Quantum Riddler for value; Wistfulness removes enchantments
            [QUANTUM, QUANTUM, WISTFULNESS, DURESS, SPIDER_SENSE],
            [ASHLING, ASHLING, VIBRANCE, NOT_DEAD, NOT_DEAD],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        has_interaction = any(c.name in {REQUITING_HEX, DECEIT, NOT_DEAD} for c in hand)
        return has_interaction or mulligans >= 2

    def bottom(self, hand, n):
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess_lands[4:]
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom
                         and c.name not in {REQUITING_HEX, DECEIT, SPIDERMAN, OVERLORD}],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (to_bottom + filler)[:n]

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_deceit = any(c.name == DECEIT for c in gs.zones.hand)
        has_hex    = any(c.name == REQUITING_HEX for c in gs.zones.hand)
        if has_deceit:
            gs.mana_reserve = 4
        elif has_hex:
            gs.mana_reserve = 2
        else:
            gs.mana_reserve = 0

    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._play_land_if_able(gs)
        if hasattr(self, 'reserve_mana'):
            self.reserve_mana(gs, opponent)
        gs.tap_lands()
        self._opp_gs = opponent

        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]

        # Kill priority targets
        for name in KILL_PRIORITY:
            target = next((c for c in opp_creatures if c.name == name), None)
            if target:
                if self._kill_with_removal(gs, opponent, target, prefer_exile=True):
                    break

        # Check if Bringer-type creature in GY for Spider-Man copy
        opp_gy_threats = [c for c in opponent.zones.graveyard
                          if c.has(Tag.CREATURE) and getattr(c, 'cmc', 0) >= 5]
        my_gy_threats = [c for c in gs.zones.graveyard
                         if c.has(Tag.CREATURE) and getattr(c, 'cmc', 0) >= 4]

        # Overlord of the Balemurk: try impending cast early for value
        for c in list(gs.zones.hand):
            if c.name == OVERLORD and gs.mana_pool.total() >= 2:
                if hasattr(gs, 'cast_spell_impending'):
                    gs.cast_spell_impending(c)
                elif gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                break

        # Sunderflock board reset when opponent has many non-elementals
        opp_non_elem = [c for c in opponent.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and c.name not in ELEMENTALS]
        if len(opp_non_elem) >= 3:
            elementals = [c for c in gs.zones.battlefield
                          if c.has(Tag.CREATURE) and not c.is_land()
                          and c.name in ELEMENTALS]
            max_mv = max((getattr(c, 'cmc', 0) for c in elementals), default=0)
            for card in list(gs.zones.hand):
                if card.name == SUNDERFLOCK:
                    effective = max(2, getattr(card, 'cmc', 9) - max_mv)
                    if gs.mana_pool.total() >= effective:
                        gs.mana_pool.pay(card.mana_cost or "7UU", effective)
                        gs.zones.hand.remove(card)
                        gs.zones.battlefield.append(card)
                        card.summoning_sickness = True
                        for victim in list(opp_non_elem):
                            if victim in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(victim)
                                opponent.zones.hand.append(victim)
                        gs._log(f"  Sunderflock: bounced {len(opp_non_elem)} non-elementals")
                    break

        # Deploy threats
        for name in (ASHLING, VIBRANCE, WISTFULNESS, HARVESTER, SPIDERMAN):
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        self._cast_all_castable(gs)

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c, prefer_exile=True):
                        return
        super().pre_combat_instant(gs, opponent)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opponent, attackers):
        if not attackers:
            return {}
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'tapped', False)
                        and not getattr(c, 'summoning_sickness', False)]
        assignments = {}
        for atk, blk in zip(
            sorted(attackers, key=lambda c: -safe_power(c)),
            sorted(my_creatures, key=lambda c: -safe_toughness(c))
        ):
            assignments[id(atk)] = [blk]
        return assignments

    def _play_land_if_able(self, gs: GameState):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
