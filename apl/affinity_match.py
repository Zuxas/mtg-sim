"""
apl/affinity_match.py — Match-aware Izzet Affinity APL (Modern)

Key match mechanics:
1. Cranial Plating: +1/+0 per artifact you control (5+ artifacts = lethal on any flyer)
2. Galvanic Blast: 4 damage with metalcraft (3+ artifacts) — premium removal
3. Arcbound Ravager: sacrifice artifacts for +1/+1 counters, move on death
4. Steel Overseer: tap to +1/+1 counter on each artifact creature
5. Inkmoth Nexus: 1/1 flying infect (10 poison = win) + Cranial Plating = one-shot
6. 0-cost creatures (Ornithopter, Memnite) flood board immediately
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RAVAGER    = "Arcbound Ravager"
PLATING    = "Cranial Plating"
OVERSEER   = "Steel Overseer"
SIGNAL     = "Signal Pest"
ORNITHOPTER= "Ornithopter"
MEMNITE    = "Memnite"
VAULT      = "Vault Skirge"
CHAMPION   = "Etched Champion"
BLAST      = "Galvanic Blast"
MOX_OPAL   = "Mox Opal"
DRUM       = "Springleaf Drum"
SPELLSKITE = "Spellskite"
INKMOTH    = "Inkmoth Nexus"
BLINKMOTH  = "Blinkmoth Nexus"

FREE_CREATURES = {ORNITHOPTER, MEMNITE}
ARTIFACTS_ALL = {RAVAGER, PLATING, OVERSEER, SIGNAL, ORNITHOPTER, MEMNITE,
                 VAULT, CHAMPION, MOX_OPAL, DRUM, SPELLSKITE}


class AffinityMatchAPL(MatchAPL):
    name = "Izzet Affinity"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        free = sum(1 for c in hand if c.name in FREE_CREATURES)
        threats = sum(1 for c in hand if c.name in {RAVAGER, PLATING, OVERSEER, CHAMPION})
        mana_sources = sum(1 for c in hand if c.name in {MOX_OPAL, DRUM} or c.is_land())
        if mana_sources == 0: return False
        if free >= 2 and threats >= 1: return True
        if lands >= 1 and threats >= 1 and free >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[2:] + spells
        return pool[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def _count_artifacts(self, gs: GameState) -> int:
        """Count artifacts on battlefield (for metalcraft + Cranial Plating)."""
        count = 0
        for c in gs.zones.battlefield:
            if c.is_land():
                # Darksteel Citadel is an artifact land
                if 'artifact' in (c.type_line or '').lower():
                    count += 1
                continue
            type_line = (c.type_line or '').lower()
            if 'artifact' in type_line or c.name in ARTIFACTS_ALL:
                count += 1
        return count

    def _has_metalcraft(self, gs: GameState) -> bool:
        return self._count_artifacts(gs) >= 3

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Affinity: dump hand fast, equip Plating, blast creatures."""
        self._play_land_if_able(gs)

        # 1. Free creatures FIRST (Ornithopter, Memnite) — build artifact count
        for c in list(gs.zones.hand):
            if c.name in FREE_CREATURES:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                c.summoning_sickness = True
                gs._log(f"  Free: {c.name}")

        # 2. Mox Opal (free artifact + mana with metalcraft)
        for c in list(gs.zones.hand):
            if c.name == MOX_OPAL:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                if self._has_metalcraft(gs):
                    gs.mana_pool.flex += 1
                gs._log(f"  Mox Opal (metalcraft: {self._has_metalcraft(gs)})")
                break

        # 3. Springleaf Drum
        for c in list(gs.zones.hand):
            if c.name == DRUM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Galvanic Blast on opponent's best creature (4 dmg with metalcraft)
        if opponent:
            self._use_blast(gs, opponent)

        # 5. Key threats: Ravager, Overseer, Plating, Champion
        for name in (RAVAGER, OVERSEER, PLATING, CHAMPION, VAULT, SIGNAL, SPELLSKITE):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 6. Simulate Steel Overseer pump (+1/+1 to all artifact creatures)
        overseers = sum(1 for c in gs.zones.battlefield
                        if c.name == OVERSEER
                        and not getattr(c, 'summoning_sickness', False))
        if overseers:
            for c in gs.zones.battlefield:
                if not c.is_land() and c.name in ARTIFACTS_ALL:
                    c.counters += overseers
            gs._log(f"  Overseer: +{overseers}/+{overseers} to all artifact creatures")

        # 7. Simulate Cranial Plating equip (add artifact count to a flyer's power)
        plating_count = sum(1 for c in gs.zones.battlefield if c.name == PLATING)
        if plating_count:
            artifact_count = self._count_artifacts(gs)
            # Find best equip target: flyer > biggest creature
            flyers = [c for c in gs.zones.battlefield
                      if not c.is_land() and c.has(Tag.CREATURE)
                      and not getattr(c, 'summoning_sickness', False)]
            if flyers:
                # Prefer Vault Skirge (flying lifelink) or Ornithopter (flying)
                target = None
                for name in (VAULT, ORNITHOPTER, BLINKMOTH):
                    target = next((c for c in flyers if c.name == name), None)
                    if target: break
                if not target:
                    target = max(flyers, key=lambda c: safe_power(c))
                # Plating gives +1/+0 per artifact
                target.counters += artifact_count * plating_count
                gs._log(f"  Plating on {target.name}: +{artifact_count * plating_count}/+0 "
                        f"({artifact_count} artifacts)")

        # 8. Remaining creatures
        changed = True
        while changed:
            changed = False
            castable = [c for c in gs.zones.hand
                        if not c.is_land() and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
                        and getattr(c, 'cmc', 0) > 0]
            if castable:
                spell = min(castable, key=lambda c: c.cmc)
                if gs.cast_spell(spell):
                    changed = True
                else:
                    break

        # 9. Galvanic Blast face if no creatures to kill
        if not opponent or not any(not c.is_land() for c in opponent.zones.battlefield):
            for c in list(gs.zones.hand):
                if c.name == BLAST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    dmg = 4 if self._has_metalcraft(gs) else 2
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.damage_dealt += dmg
                    gs._log(f"  Galvanic Blast face: {dmg} ({gs.damage_dealt} total)")
                    break

    def _use_blast(self, gs: GameState, opponent: GameState):
        """Galvanic Blast — 4 damage with metalcraft, premium removal."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return
        
        dmg = 4 if self._has_metalcraft(gs) else 2
        if dmg < safe_toughness(target): return  # won't kill

        for c in list(gs.zones.hand):
            if c.name == BLAST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Galvanic Blast ({dmg} dmg) → kill {target.name}")
                return

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            if c.name == PLATING: continue  # equipment doesn't attack
            if c.name == OVERSEER: continue  # keep for tap ability
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        return {}  # aggro deck, don't block

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = c.name.lower()
            if 'darksteel' in n: return 0  # artifact land, counts for metalcraft
            if 'glimmervoid' in n: return 1
            if 'inkmoth' in n or 'blinkmoth' in n: return 2  # creature lands
            return 4
        gs.play_land(min(lands, key=score))
