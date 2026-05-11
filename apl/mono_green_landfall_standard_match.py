"""
apl/mono_green_landfall_standard_match.py — Match-aware Mono Green Landfall APL (Standard)

Mono Green Landfall deck:
1. T1 Llanowar Elves (mana dork) to ramp
2. Landfall creatures grow with each land drop
3. Fabled Passage, Escape Tunnel, Promising Vein = sacrifice for extra landfall triggers
4. Earthbender Ascension generates tokens on landfall
5. Meltstrider's Resolve as pump spell
6. Ba Sing Se as utility land
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
LLANOWAR_ELVES        = "Llanowar Elves"
BADGERMOLE_CUB        = "Badgermole Cub"
ICETILL_EXPLORER      = "Icetill Explorer"
SAZHS_CHOCOBO         = "Sazh's Chocobo"
MIGHTFORM_HARMONIZER  = "Mightform Harmonizer"
EARTHBENDER_ASCENSION = "Earthbender Ascension"
MELTSTRIDERS_RESOLVE  = "Meltstrider's Resolve"
SAPLING_NURSERY       = "Sapling Nursery"
BA_SING_SE            = "Ba Sing Se"
FABLED_PASSAGE        = "Fabled Passage"
ESCAPE_TUNNEL         = "Escape Tunnel"
PROMISING_VEIN        = "Promising Vein"

MANA_DORKS = {LLANOWAR_ELVES}
SACRIFICE_LANDS = {FABLED_PASSAGE, ESCAPE_TUNNEL, PROMISING_VEIN}
LANDFALL_CREATURES = {BADGERMOLE_CUB, ICETILL_EXPLORER, SAZHS_CHOCOBO,
                      MIGHTFORM_HARMONIZER}


class MonoGreenLandfallStandardMatchAPL(MatchAPL):
    ARCHETYPE = "ramp"
    # Sideboard plans from Decktionary in-depth guide (Mar 2026) -- Mono Green specific
    # Icetill Explorer = "essential card in the deck" -- never cut
    # Sapling Nursery = critical vs board-focused matchups; cut vs spell-heavy decks
    # Harmonizer standalone = "not particularly impactful"; only good in combination with Icetill+fetches
    # Key combo: Icetill + fetches + Harmonizer = up to 32 damage; trigger order: Chocobo/Ascension counters FIRST
    SB_PLANS = {
        "combo": (
            # vs Izzet Lessons: Torpor Orb shuts ETBs (Gran-Gran, Monument); cut Badgermole Cub
            ["Torpor Orb", "Torpor Orb", "Torpor Orb",
             "Mossborn Hydra", "Mossborn Hydra",
             "Sandman, Shifting Scoundrel"],
            ["Badgermole Cub", "Badgermole Cub", "Badgermole Cub", "Badgermole Cub",
             "Archdruid's Charm", "Mightform Harmonizer"],
        ),
        "tempo": (
            # vs Spellementals: Meltstrider's Resolve counters removal; Origin of Metalbending
            ["Meltstrider's Resolve", "Meltstrider's Resolve", "Meltstrider's Resolve",
             "Mossborn Hydra", "Mossborn Hydra",
             "Origin of Metalbending", "Origin of Metalbending"],
            ["Sapling Nursery", "Sapling Nursery", "Sapling Nursery", "Sapling Nursery",
             "Fecund Greenshell", "Esper Origins", "Esper Origins"],
        ),
        "midrange": (
            # vs Dimir Midrange: Torpor Orb + Meltstrider + Mossborn; cut slow engines
            ["Torpor Orb", "Torpor Orb", "Torpor Orb",
             "Meltstrider's Resolve", "Meltstrider's Resolve", "Meltstrider's Resolve",
             "Mossborn Hydra", "Mossborn Hydra", "Pawpatch Formation"],
            ["Fecund Greenshell",
             "Sapling Nursery", "Sapling Nursery", "Sapling Nursery", "Sapling Nursery",
             "Archdruid's Charm", "Archdruid's Charm",
             "Esper Origins", "Esper Origins"],
        ),
        "control": (
            # vs Control variants: Surrak (uncounterable) + Sandman; cut Mossborn (bad vs sweepers)
            ["Surrak, Elusive Hunter", "Sandman, Shifting Scoundrel", "Pawpatch Formation"],
            ["Mossborn Hydra", "Mossborn Hydra", "Mightform Harmonizer"],
        ),
        "ramp": (
            # vs Mirror / Mono Green: Mossborn Hydra closes fast; cut slow engines
            ["Mossborn Hydra", "Mossborn Hydra", "Mossborn Hydra", "Mossborn Hydra",
             "Surrak, Elusive Hunter"],
            ["Sapling Nursery", "Sapling Nursery",
             "Mightform Harmonizer", "Mightform Harmonizer", "Archdruid's Charm"],
        ),
    }
    name = "Mono Green Landfall (Standard)"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        has_ascension = any(c.name == EARTHBENDER_ASCENSION for c in hand)
        if lands < 2:
            return False
        if lands > 5:
            return False
        # Need lands for landfall + creatures or Ascension
        if creatures >= 1 or has_ascension:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        # Keep 3-4 lands (we WANT lands for landfall), bottom excess spells first
        pool = spells + lands[4:]
        return pool[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Landfall: deploy creatures, play lands, sacrifice fetch lands."""
        # 1. Play sacrifice lands first for extra landfall triggers later
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 2. Removal on opponent's biggest creature
        if opponent:
            self._try_removal(gs, opponent)

        # 3. Deploy mana dorks T1
        for c in list(gs.zones.hand):
            if c.name == LLANOWAR_ELVES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Earthbender Ascension (generates tokens on landfall)
        for c in list(gs.zones.hand):
            if c.name == EARTHBENDER_ASCENSION and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5. Sapling Nursery — Affinity for Forests ({1} less per Forest you
        # control). At 6 Forests, base {6}{G}{G} costs just {G}{G} = 2 mana.
        # Set cost_reduction = Forest count on the pool, then cast, then reset
        # (per the affinity_match.py pattern).
        forest_count = sum(
            1 for x in gs.zones.battlefield
            if x.is_land() and "forest" in (x.type_line or "").lower()
        )
        prev_cr = gs.mana_pool.cost_reduction
        gs.mana_pool.cost_reduction = max(prev_cr, forest_count)
        for c in list(gs.zones.hand):
            if c.name == SAPLING_NURSERY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break
        gs.mana_pool.cost_reduction = prev_cr

        # 6. Deploy landfall creatures by CMC
        for name in (BADGERMOLE_CUB, ICETILL_EXPLORER, SAZHS_CHOCOBO,
                     MIGHTFORM_HARMONIZER):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 7. Meltstrider's Resolve — Aura "Enchant creature you control.
        # When this Aura enters, enchanted creature fights up to one
        # target creature an opp controls. Enchanted creature gets
        # +0/+2 and can't be blocked by more than one creature."
        # Effect: fight an opp creature (winner is our biggest; if we
        # win the fight, opp creature dies), then our creature gets
        # +0/+2 and evasion.
        my_creatures = [x for x in gs.zones.battlefield
                        if not x.is_land() and x.has(Tag.CREATURE)]
        if my_creatures and opponent:
            opp_creatures = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
            for c in list(gs.zones.hand):
                if c.name == MELTSTRIDERS_RESOLVE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    attacker = max(my_creatures, key=lambda x: safe_power(x))
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    # Put Aura on battlefield attached to attacker
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    # Fight: pick opp creature we can kill
                    target = None
                    for opp_cr in sorted(opp_creatures,
                                          key=lambda x: -safe_power(x)):
                        if safe_power(attacker) >= safe_toughness(opp_cr):
                            target = opp_cr
                            break
                    if target:
                        # Fight — both deal damage equal to power to each other
                        opp_dmg = safe_power(attacker)
                        my_dmg = safe_power(target)
                        if opp_dmg >= safe_toughness(target):
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                            gs._log(f"  Meltstrider's Resolve: {attacker.name}"
                                    f" fights, kills {target.name}")
                        if my_dmg >= safe_toughness(attacker) + 2:  # +0/+2 Aura
                            # Attacker dies too
                            gs.zones.battlefield.remove(attacker)
                            gs.zones.graveyard.append(attacker)
                            gs._log(f"    (attacker {attacker.name} dies)")
                    # +0/+2 + evasion pump applied as +1 counter proxy
                    if attacker in gs.zones.battlefield:
                        attacker.counters = (attacker.counters or 0) + 1
                        gs._log(f"    {attacker.name}: +1 counter (Aura pump)")
                    break

        # 8. Any remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _try_removal(self, gs: GameState, opponent: GameState):
        """Green has limited removal — use Meltstrider's Resolve as combat trick.
        Try to fight/bite if available, otherwise skip."""
        # Green decks rely on combat for removal, not spells
        pass

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
        return {}  # aggro — race, don't block

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        """Prioritize sacrifice lands (Fabled Passage, etc.) for extra landfall."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Prefer sacrifice lands for extra landfall triggers
        sac_lands = [c for c in lands if c.name in SACRIFICE_LANDS]
        if sac_lands:
            gs.play_land(sac_lands[0])
        else:
            gs.play_land(lands[0])
