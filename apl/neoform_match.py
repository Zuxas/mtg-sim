"""
apl/neoform_match.py — Auto-generated Neoform APL (Modern)
Generated from website playbook decklist. Needs manual audit for oracle accuracy.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

ALLOSAURUS_RIDER = "Allosaurus Rider"
NEOFORM = "Neoform"
ELDRITCH_EVOLUTION = "Eldritch Evolution"
SUMMONERS_PACT = "Summoner's Pact"
PACT_OF_NEGATION = "Pact of Negation"
CONSIGN_TO_MEMORY = "Consign to Memory"
PLANAR_GENESIS = "Planar Genesis"
VEIL_OF_SUMMER = "Veil of Summer"
NOURISHING_SHOAL = "Nourishing Shoal"
GENEROUS_ENT = "Generous Ent"

class NeoformMatchAPL(MatchAPL):
    name = "Neoform"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if not c.is_land() and c.has(Tag.CREATURE))
        interaction = sum(1 for c in hand if not c.is_land() and not c.has(Tag.CREATURE))
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and lands >= 2: return True
        if interaction >= 2 and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        avail = gs.mana_pool.total()

        # Removal on opponent creatures
        if opponent:
            opp_cr = [c for c in opponent.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 2]
            if opp_cr:
                target = max(opp_cr, key=lambda x: safe_power(x))
                for c in list(gs.zones.hand):
                    if not c.is_land() and not c.has(Tag.CREATURE):
                        if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                            dmg = 3  # approximate
                            if safe_toughness(target) <= dmg:
                                gs.mana_pool.pay(c.mana_cost, c.cmc)
                                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                                if target in opponent.zones.battlefield:
                                    opponent.zones.battlefield.remove(target)
                                    opponent.zones.graveyard.append(target)
                                gs._log(f"  Remove: {target.name}")
                                break

        # Deploy creatures by CMC (cheapest first for tempo)
        deployed = False
        for _ in range(5):
            castable = [c for c in gs.zones.hand
                       if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if not castable: break
            spell = min(castable, key=lambda c: getattr(c, 'cmc', 0))
            if gs.cast_spell(spell):
                deployed = True
            else:
                break

        # Cast noncreature spells
        for c in list(gs.zones.hand):
            if not c.is_land() and not c.has(Tag.CREATURE):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    # Burn face if no creatures to target
                    if not opponent or not any(not x.is_land() and x.has(Tag.CREATURE) 
                                               for x in opponent.zones.battlefield):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.damage_dealt += 2  # approximate spell damage
                        gs._log(f"  Cast {c.name} (2 face)")

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                   and not c.is_land() and safe_power(c) >= 3
                   and not getattr(c, 'tapped', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'mesa' in n or 'strand' in n or 'delta' in n or 'tarn' in n or 'foothills' in n or 'flats' in n or 'rainforest' in n or 'catacombs' in n or 'heath' in n or 'mire' in n: return 0
            if 'foundry' in n or 'vents' in n or 'garden' in n or 'grave' in n or 'shrine' in n or 'fountain' in n or 'crypt' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
