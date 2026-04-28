"""
apl/gruul_aggro_standard_match.py — Gruul Overlord Ramp (Standard)

Current-meta Gruul "Aggro" is actually Gruul Overlord Ramp — fudgems
2026-03-28 list. Post-ban, post-rotation shell.

Plan:
  T1  Llanowar Elves (mana dork for T2 ramp)
  T2  Badgermole Cub (landfall grower) or Esper Origins (scry+ramp?)
  T3  Overlord of the Hauntwoods (impending = Saga chapters, or hard
      cast = 6/6 flying) or Vibrance (anthem)
  T4  Overlord of the Boilerbilges (4/5 trample, impending damage)
  T5+ Calamity, Galloping Inferno (5/5 haste trample, copy spells)
      Vaultborn Tyrant (7/7 flying — reanimator-ish, life gain)
      Summon: Bahamut (big spell/creature — FF crossover set)

Removal: Fire Magic (2 dmg to creature/player tiered), Smuggler's
Surprise (protection / disruption).

This is NOT classic Gruul Aggro — it's a midrange/ramp deck with
big creature finishers. ARCHETYPE updated to "ramp" so opponent
sideboard plans pull the vs-ramp tuple, not vs-aggro.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness


# Ramp / early play
LLANOWAR_ELVES      = "Llanowar Elves"
BADGERMOLE_CUB      = "Badgermole Cub"
ESPER_ORIGINS       = "Esper Origins"
VIBRANCE            = "Vibrance"

# Removal
FIRE_MAGIC          = "Fire Magic"
SMUGGLERS_SURPRISE  = "Smuggler's Surprise"

# Overlord finishers (Duskmourn cycle — impending sagas that flip
# to big creatures)
OVERLORD_HAUNTWOODS = "Overlord of the Hauntwoods"
OVERLORD_BOILER     = "Overlord of the Boilerbilges"

# Top-end bombs
CALAMITY            = "Calamity, Galloping Inferno"
VAULTBORN_TYRANT    = "Vaultborn Tyrant"
BAHAMUT             = "Summon: Bahamut"


CREATURES = {
    LLANOWAR_ELVES, BADGERMOLE_CUB,
    OVERLORD_HAUNTWOODS, OVERLORD_BOILER,
    CALAMITY, VAULTBORN_TYRANT, BAHAMUT,
}
REMOVAL_SPELLS = {FIRE_MAGIC}


class GruulAggroStandardMatchAPL(MatchAPL):
    ARCHETYPE = "ramp"
    name = "Gruul Overlord Ramp (Standard)"
    win_condition_damage = 20
    max_turns = 12

    # Sideboard: 1 Fire Magic, 2 Ghost Vacuum, 3 Heritage Reclamation,
    # 1 Leatherhead, 3 Sear, 1 Soul-Guide Lantern, 2 Surrak, 2 Ureni.
    # All sb_out cards must be in MAINBOARD.
    SB_PLANS = {
        "aggro": (
            ["1 Fire Magic", "3 Sear", "1 Soul-Guide Lantern",
             "2 Surrak, Elusive Hunter"],
            ["2 Vaultborn Tyrant", "2 Summon: Bahamut",
             "3 Smuggler's Surprise"],
        ),
        "control": (
            ["2 Ghost Vacuum", "3 Heritage Reclamation",
             "2 Ureni, the Song Unending"],
            ["2 Fire Magic", "4 Smuggler's Surprise",
             "1 Restless Ridgeline"],
        ),
        "combo": (
            ["3 Heritage Reclamation", "1 Soul-Guide Lantern",
             "2 Ghost Vacuum"],
            ["2 Fire Magic", "4 Smuggler's Surprise"],
        ),
        "ramp": (
            ["2 Ureni, the Song Unending", "2 Surrak, Elusive Hunter",
             "1 Soul-Guide Lantern"],
            ["2 Fire Magic", "3 Smuggler's Surprise"],
        ),
        "tempo": (
            ["1 Fire Magic", "3 Sear", "2 Surrak, Elusive Hunter"],
            ["2 Vaultborn Tyrant", "3 Smuggler's Surprise",
             "1 Restless Ridgeline"],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name == LLANOWAR_ELVES)
        has_payoff = any(c.name in {OVERLORD_HAUNTWOODS, OVERLORD_BOILER,
                                     CALAMITY, VAULTBORN_TYRANT, BAHAMUT}
                          for c in hand)
        if lands < 2 or lands > 5:
            return False
        if ramp >= 1 and (has_payoff or lands >= 3):
            return True
        if lands >= 3 and has_payoff:
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
        """Ramp → impending Overlord → big bomb."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Spot removal on opp's biggest creature
        if opponent:
            self._use_removal(gs, opponent)

        # 2. T1 Llanowar Elves
        for c in list(gs.zones.hand):
            if c.name == LLANOWAR_ELVES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 3. T2 Badgermole Cub (landfall grower — gets +1/+1 every
        # subsequent land drop via on_landfall hook)
        for c in list(gs.zones.hand):
            if c.name == BADGERMOLE_CUB and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Esper Origins / Vibrance (enchantment anthem / draw)
        for name in (ESPER_ORIGINS, VIBRANCE):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 5-6. Overlord cycle — prefer impending cast (cheaper) when
        # we can't afford hard-cast. ETB fires either way. Hauntwoods
        # impending = 3 mana (vs 5 hard), Boilerbilges = 4 (vs 6).
        for name in (OVERLORD_HAUNTWOODS, OVERLORD_BOILER):
            for c in list(gs.zones.hand):
                if c.name != name:
                    continue
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                else:
                    # Try impending cast as fallback
                    gs.cast_spell_impending(c)
                break

        # 7. Calamity — 5/5 haste trample, copies spells
        for c in list(gs.zones.hand):
            if c.name == CALAMITY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 8. Vaultborn Tyrant / Summon: Bahamut — top-end
        for name in (VAULTBORN_TYRANT, BAHAMUT):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 9. Any remaining creature
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _use_removal(self, gs, opponent):
        opp_creatures = [c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        # Fire Magic: 2 dmg to creature/PW. Kills toughness <= 2.
        if safe_toughness(target) > 2:
            return
        for c in list(gs.zones.hand):
            if c.name != FIRE_MAGIC:
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
            gs._log(f"  Fire Magic: kill {target.name}")
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
            if not c.has(Tag.CREATURE):
                continue
            # Llanowar Elves stays home as mana source
            if c.name == LLANOWAR_ELVES:
                continue
            attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers:
            return assignments
        blockers = [c for c in gs.zones.battlefield
                     if c.has(Tag.CREATURE) and not c.is_land()
                     and not getattr(c, 'tapped', False)
                     and c.name != LLANOWAR_ELVES]
        if not blockers:
            return assignments
        biggest_att = max(attackers, key=lambda c: safe_power(c))
        if safe_power(biggest_att) >= 3:
            best_blocker = max(blockers, key=lambda c: safe_toughness(c))
            if safe_toughness(best_blocker) > safe_power(biggest_att):
                assignments[id(biggest_att)] = [best_blocker]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        """Prefer untapped duals and dual lands for quick development."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = (c.name or '').lower()
            if 'cavern of souls' in n:
                return 0
            if 'stomping ground' in n or 'thornspire' in n or 'commercial' in n:
                return 1
            if 'forest' in n or 'mountain' in n:
                return 2
            return 3
        gs.play_land(min(lands, key=score))
