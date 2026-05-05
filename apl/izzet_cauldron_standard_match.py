"""
apl/izzet_cauldron_standard_match.py — Izzet Cauldron APL (Standard)

Discard-matters UR midrange. Win condition: grow Marauding Mako large via
repeated discard, attack for lethal. Secondary plan: Vivi Ornitier mana
engine + Steamcore Scholar + Winternight Stories card velocity.

Core engine:
1. T2: Vivi Ornitier (0/3, taps for U/R equal to counters = mana engine)
2. T3: Winternight Stories (draw 3 / discard 2 = pump Mako +2)
3. T4: Steamcore Scholar (draw 2 / discard 2 = pump Mako +2 more)
4. Marauding Mako grows +1/+1 per discard, attacks as large threat
5. Fear of Missing Out: cycle to refuel, delirium = attack for +1/+1

Composed from card_specs: final_fantasy.vivi_ornitier,
tarkir_dragonstorm.winternight_stories, duskmourn_creatures.fear_missing_out,
aetherdrift.marauding_mako, multi_set_standard.steamcore_scholar.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

VIVI          = "Vivi Ornitier"
MAKO          = "Marauding Mako"
FEAR          = "Fear of Missing Out"
WINTERNIGHT   = "Winternight Stories"
STEAMCORE     = "Steamcore Scholar"
AGATHA        = "Agatha's Soul Cauldron"
PROFT         = "Proft's Eidetic Memory"
INTO_FLOOD    = "Into the Flood Maw"
FIRE_MAGIC    = "Fire Magic"
QUANTUM       = "Quantum Riddler"
ABRADE        = "Abrade"
TORCH         = "Torch the Tower"

THREATS = {MAKO, FEAR, STEAMCORE, QUANTUM}
DRAW_DISCARD = {WINTERNIGHT, STEAMCORE}


class IzzetCauldronMatchAPL(MatchAPL):
    name = "Izzet Cauldron"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._discards_this_turn = 0
        self._delirium = False

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        has_threat = any(c.name in THREATS for c in hand)
        has_engine = any(c.name in {VIVI, WINTERNIGHT, STEAMCORE} for c in hand)
        has_mako = any(c.name == MAKO for c in hand)
        if lands == 0:
            return False
        if lands >= 2 and (has_threat or has_engine):
            return True
        if has_mako and lands >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        # Bottom excess lands, then low-value non-threats
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess_lands[3:]
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom
                         and c.name not in THREATS and c.name != MAKO],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._discards_this_turn = 0
        avail = gs.mana_pool.total()

        # Update delirium (4+ card types in GY)
        gy_types = set()
        for c in gs.zones.graveyard:
            if c.has(Tag.CREATURE): gy_types.add('creature')
            if c.has(Tag.INSTANT): gy_types.add('instant')
            if c.has(Tag.SORCERY): gy_types.add('sorcery')
            if c.has(Tag.ENCHANTMENT): gy_types.add('enchantment')
            if c.has(Tag.ARTIFACT): gy_types.add('artifact')
            if c.is_land(): gy_types.add('land')
        self._delirium = len(gy_types) >= 4

        # 1. Vivi Ornitier T2 — mana engine
        for c in list(gs.zones.hand):
            if c.name == VIVI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Vivi Ornitier: 0/3, taps for U/R = counters")
                break

        # 2. Marauding Mako — the primary win condition
        for c in list(gs.zones.hand):
            if c.name == MAKO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Marauding Mako: 1/1, grows on discard")
                break

        # 3. Winternight Stories — draw 3 / discard 2 (pump Mako +2)
        for c in list(gs.zones.hand):
            if c.name == WINTERNIGHT and avail >= 3:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    gs.zones.draw(3)
                    # Discard 2 (prefer lands/low-value; each discard pumps Mako)
                    self._discard_n(gs, 2)
                    avail = gs.mana_pool.total()
                    break

        # 4. Steamcore Scholar — ETB draw 2 / discard 2
        for c in list(gs.zones.hand):
            if c.name == STEAMCORE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(2)
                self._discard_n(gs, 2)
                avail = gs.mana_pool.total()
                break

        # 5. Fear of Missing Out — discard/draw cycle
        for c in list(gs.zones.hand):
            if c.name == FEAR and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if gs.zones.hand:
                    worst = min(gs.zones.hand, key=lambda x: getattr(x,'cmc',0))
                    gs.zones.hand.remove(worst)
                    gs.zones.graveyard.append(worst)
                    self._on_discard(gs)
                gs.zones.draw(1)
                break

        # 6. Removal if opponent has threats
        if opponent:
            self._use_removal(gs, opponent)

        # 7. Quantum Riddler — 4/6 flying with draw
        for c in list(gs.zones.hand):
            if c.name == QUANTUM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(1)
                gs._log(f"  Quantum Riddler: 4/6 flying, draw 1")
                break

        # 8. Curve out
        self._cast_all_castable(gs)

    def _discard_n(self, gs, n: int) -> None:
        """Discard n cards, prioritizing low-value. Each discard pumps Mako."""
        for _ in range(n):
            if not gs.zones.hand:
                break
            # Keep threats and high-CMC; discard lands and low CMC
            discardable = sorted(gs.zones.hand,
                key=lambda c: (c.name in THREATS or c.name == MAKO, getattr(c,'cmc',0)))
            discard = discardable[0]
            gs.zones.hand.remove(discard)
            gs.zones.graveyard.append(discard)
            self._on_discard(gs)

    def _on_discard(self, gs) -> None:
        """Pump Marauding Mako on discard."""
        self._discards_this_turn += 1
        for c in gs.zones.battlefield:
            if c.name == MAKO:
                c.counters = getattr(c, 'counters', 0) + 1
                c.power = str(1 + c.counters)
                gs._log(f"  Mako discard trigger: {c.power}/{c.power}")

    def _use_removal(self, gs, opponent) -> bool:
        """Use Abrade or Fire Magic to remove opponent threats."""
        threats = [c for c in opponent.zones.battlefield
                   if c.has(Tag.CREATURE) and not c.is_land() and safe_power(c) >= 3]
        if not threats:
            return False
        target = max(threats, key=lambda c: safe_power(c))
        for c in list(gs.zones.hand):
            if c.name == ABRADE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if safe_toughness(target) <= 3:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Abrade: remove {target.name}")
                return True
            if c.name == TORCH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Torch the Tower: removal")
                return True
        return False

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if not c.has(Tag.CREATURE) or c.is_land(): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            # Delirium: Fear of Missing Out gets +1/+1 when attacking
            if c.name == FEAR and self._delirium:
                c.counters = getattr(c, 'counters', 0) + 1
            attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers:
            return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)
                    and c.name != MAKO]  # don't block with Mako (attacking threat)
        if blockers:
            biggest_attacker = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest_attacker) >= 3:
                best_blocker = max(blockers, key=lambda c: safe_toughness(c))
                assignments[id(biggest_attacker)] = [best_blocker]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Into the Flood Maw: bounce opponent creature on spell trigger."""
        if not spell or not opponent:
            return None
        for c in list(gs.zones.hand):
            if c.name == INTO_FLOOD and gs.mana_pool.total() >= 1:
                targets = [x for x in opponent.zones.battlefield
                           if x.has(Tag.CREATURE) and not x.is_land()]
                if targets:
                    t = max(targets, key=lambda x: safe_power(x))
                    opponent.zones.battlefield.remove(t)
                    opponent.zones.hand.append(t)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs._log(f"  Into the Flood Maw: bounce {t.name}")
                    return c
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = (c.name or '').lower()
            if 'canal' in n or 'vents' in n or 'verge' in n: return 0
            if 'island' in n: return 1
            if 'mountain' in n: return 2
            return 3
        gs.play_land(min(lands, key=score))
