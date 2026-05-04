"""
apl/jeskai_control_standard_match.py -- Jeskai Control (Standard 2026)

Guide sources: UltimateGuard Jun 2025 (Pro Tour Final Fantasy), Draftsim Standard

Key cards:
  Get Lost {1W}:          instant exile (universal answer -- accepts map downside)
  Lightning Helix {RW}:   instant 3 damage + 3 life (removal AND stabilization)
  Temporary Lockdown {2W}: exile all CMC<=2 permanents (sweeper vs aggro/tokens)
  Day of Judgment {2WW}:  destroy all creatures (board wipe vs midrange)
  Three Steps Ahead {U}:  counter mode +{1U}; hold up always
  Shiko, Paragon of the Way: card advantage engine (primary threat)
  Marang River Regent:    recursive finisher

Matchup roles (from UltimateGuard guide):
  vs Izzet Prowess:   control -- hold Lockdown vs early Cori; creatures in SB
  vs Mono Red Aggro:  stabilization -- early removal + Lightning Helix lifegain
  vs UW Omniscience:  graveyard hate gates -- shift to midrange after GY hate
  vs Dimir Midrange:  value grindfest -- Get Lost Kaito before T3 activation

Never tap out except for planeswalkers. Always hold interaction mana.
Kill priority: Cori Steel Cutter before untap, Screaming Nemesis immediately,
               Kaito before T3, Gran-Gran (Monument enabler).
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.jeskai_control_standard import JeskaiControlAPL

GET_LOST      = "Get Lost"
HELIX         = "Lightning Helix"
LOCKDOWN      = "Temporary Lockdown"
DAY_JUDGMENT  = "Day of Judgment"
THREE_STEPS   = "Three Steps Ahead"
NEGATE        = "Negate"
CHANGE_EQ     = "Change the Equation"
DESTROY_EVIL  = "Destroy Evil"
TISHANA       = "Tishana's Tidebinder"
SOUL_GUIDE    = "Soul-Guide Lantern"
SHIKO         = "Shiko, Paragon of the Way"
MARANG        = "Marang River Regent"
OVERLORD      = "Overlord of the Mistmoors"
ABRADE        = "Abrade"

COUNTERSPELLS = {THREE_STEPS, NEGATE, CHANGE_EQ}

KILL_PRIORITY = (
    "Cori, Steel Cutter",        # Prowess engine; answer before untap
    "Screaming Nemesis",         # Mono-red threat; kill immediately
    "Kaito, Bane of Nightmares", # Kill before T3 activation
    "Gran-Gran",                 # Monument to Endurance enabler
    "Mightform Harmonizer",      # Combo kill piece
    "Icetill Explorer",          # Landfall chain engine
    "Badgermole Cub",            # Ramp that must die T1-T2
)


class JeskaiControlStandardMatchAPL(AwareMatchAPL, JeskaiControlAPL):
    name = "Jeskai Control Standard"
    ARCHETYPE = "control"

    COUNTER_COST  = 2
    COUNTER_CARDS = COUNTERSPELLS

    MATCH_REMOVAL = {
        GET_LOST:     ("1W", None),
        HELIX:        ("RW", 3),
        ABRADE:       ("1R", None),
        DESTROY_EVIL: ("1W", None),
    }
    MATCH_EXILE = {GET_LOST}

    SB_PLANS = {
        "aggro": (
            [TISHANA, TISHANA, TISHANA, "Devout Decree", CHANGE_EQ, OVERLORD],
            [NEGATE, SOUL_GUIDE, "Ghost Vacuum", MARANG, DAY_JUDGMENT, DAY_JUDGMENT],
        ),
        "tempo": (
            [TISHANA, TISHANA, TISHANA, ABRADE, CHANGE_EQ, NEGATE],
            [DAY_JUDGMENT, DAY_JUDGMENT, SOUL_GUIDE, "Ghost Vacuum", HELIX, SHIKO],
        ),
        "combo": (
            [TISHANA, TISHANA, TISHANA, OVERLORD, OVERLORD, OVERLORD,
             NEGATE, ABRADE, "Ghost Vacuum", SOUL_GUIDE],
            [LOCKDOWN, LOCKDOWN, LOCKDOWN, LOCKDOWN, DAY_JUDGMENT, DAY_JUDGMENT,
             HELIX, HELIX, MARANG, SHIKO],
        ),
        "control": (
            [OVERLORD, OVERLORD, OVERLORD, TISHANA, TISHANA, TISHANA,
             DESTROY_EVIL, ABRADE, "Ghost Vacuum"],
            [NEGATE, SOUL_GUIDE, LOCKDOWN, LOCKDOWN, DAY_JUDGMENT, DAY_JUDGMENT,
             HELIX, HELIX, MARANG],
        ),
        "ramp": (
            [TISHANA, TISHANA, LOCKDOWN, LOCKDOWN, DESTROY_EVIL, CHANGE_EQ],
            [NEGATE, SOUL_GUIDE, DAY_JUDGMENT, MARANG, OVERLORD, ABRADE],
        ),
    }

    # Never tap out; always hold counter/removal mana
    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_counter = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        has_removal = any(c.name in self.MATCH_REMOVAL for c in gs.zones.hand)
        if has_counter:
            gs.mana_reserve = self.COUNTER_COST
        elif has_removal:
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
                         if not c.is_land() and c.has(Tag.CREATURE)]

        # Temporary Lockdown: exile all CMC<=2 permanents when 3+ present
        small_opp = [c for c in opponent.zones.battlefield
                     if not c.is_land() and getattr(c, 'cmc', 0) <= 2]
        if len(small_opp) >= 3:
            for c in list(gs.zones.hand):
                if c.name == LOCKDOWN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    for victim in list(small_opp):
                        if victim in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(victim)
                            opponent.zones.exile.append(victim)
                    gs._log(f"  Temporary Lockdown: exiled {len(small_opp)} permanents")
                    return

        # Day of Judgment: destroy all creatures when 3+ present
        if len(opp_creatures) >= 3:
            for c in list(gs.zones.hand):
                if c.name == DAY_JUDGMENT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    for victim in list(opp_creatures):
                        if victim in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(victim)
                            opponent.zones.graveyard.append(victim)
                    gs._log(f"  Day of Judgment: destroyed {len(opp_creatures)} creatures")
                    return

        # Kill-priority targets with exile preference
        for name in KILL_PRIORITY:
            target = next((c for c in opp_creatures if c.name == name), None)
            if target:
                if self._kill_with_removal(gs, opponent, target, prefer_exile=True):
                    return

        # General removal on highest threat
        if opp_creatures:
            target = max(opp_creatures, key=lambda c: safe_power(c))
            self._kill_with_removal(gs, opponent, target)

        self._cast_all_castable(gs)

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c, prefer_exile=True):
                        gs._log(f"  [pre-combat] killed {c.name}")
                        return
        super().pre_combat_instant(gs, opponent)

    def declare_blockers(self, gs: GameState, opponent: GameState, attackers: list):
        if not attackers:
            return {}
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        assignments = {}
        for atk, blk in zip(
            sorted(attackers, key=lambda c: -safe_power(c)),
            sorted(my_creatures, key=lambda c: -safe_toughness(c))
        ):
            assignments[id(atk)] = [blk]
        return assignments
