"""
apl/jeskai_oculus_standard_match.py — Jeskai Oculus (Standard)

Storm combo using Prismari (storm on all spells) + Rootha (combat token)
+ Veyran (doubles all triggers) + Zaffai (free spell per turn).

Win condition: assemble Prismari + Veyran, then chain spells for storm
copies. Magma Opus with storm = 4 damage × N copies. Mathemagics = draw
2^X × N copies. Rootha combat = massive flying token.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import (prismari, rootha, veyran, zaffai,
                              deekah, lorehold, magma_opus, mathemagics)

PRISMARI  = prismari.NAME
ROOTHA    = rootha.NAME
VEYRAN    = veyran.NAME
ZAFFAI    = zaffai.NAME
DEEKAH    = deekah.NAME
LOREHOLD  = lorehold.NAME
MAGMA_OPS = magma_opus.NAME
MATHEMAGIC= mathemagics.NAME
OPT       = "Opt"
WINTERNIGHT = "Winternight Stories"
INTO_FLOOD  = "Into the Flood Maw"

ENGINE_PIECES = {PRISMARI, ROOTHA, VEYRAN, DEEKAH, ZAFFAI, LOREHOLD}


class JeskaiOculusMatchAPL(MatchAPL):
    name = "Jeskai Oculus"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_engine = any(c.name in ENGINE_PIECES for c in hand)
        has_spells = sum(1 for c in hand
                        if not c.is_land() and not c.has(Tag.CREATURE)) >= 2
        if lands == 0: return False
        if has_engine and lands >= 2: return True
        if has_spells and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[3:]
        filler = [c for c in hand if not c.is_land() and c not in to_bottom
                  and c.name not in ENGINE_PIECES]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Priority: Veyran T3 first (doubles everything that follows)
        veyran.cast(gs, opponent)

        # T4: Lorehold (miracle on all drawn spells = free high-CMC spells)
        lorehold.cast(gs, opponent)

        # T4: Rootha (combat token based on spell MV)
        rootha.cast(gs, opponent)

        # T5: Deekah (Fractal tokens on each spell)
        deekah.cast(gs, opponent)

        # T6: Prismari (storm on all spells — the combo enabler)
        if prismari.cast(gs, opponent):
            spells = prismari.storm_copies(gs)
            gs._log(f"  Prismari online: next spell storm-copies {spells}× "
                    f"(Veyran doubles: {'yes' if veyran.is_active(gs) else 'no'})")

        # T7: Zaffai (free spell per turn)
        zaffai.cast(gs, opponent)

        # Once Prismari is active, chain spells for storm
        if prismari.is_active(gs):
            # Opt / Winternight for storm fodder
            for c in list(gs.zones.hand):
                if c.name in (OPT, WINTERNIGHT) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if c.name == WINTERNIGHT:
                        gs.zones.draw(3)
                        # Discard 2
                        for _ in range(2):
                            if gs.zones.hand:
                                worst = min(gs.zones.hand, key=lambda x: getattr(x,'cmc',0))
                                gs.zones.hand.remove(worst)
                                gs.zones.graveyard.append(worst)
                    else:
                        gs.zones.draw(1)
                    # Trigger Veyran magecraft
                    if veyran.is_active(gs):
                        veyran.apply_magecraft(gs)
                    # Trigger Deekah fractal
                    if deekah.is_active(gs):
                        deekah.create_fractal_token(gs)
                    # Prismari storm: apply damage
                    copies = prismari.storm_copies(gs)
                    if veyran.doubles_triggers(gs):
                        copies *= 2

            # Magma Opus with storm = devastating
            if magma_opus.cast_free(gs, opponent) or magma_opus.cast(gs, opponent):
                copies = prismari.storm_copies(gs)
                gs.damage_dealt += magma_opus.DAMAGE * copies
                gs._log(f"  Magma Opus storm: {magma_opus.DAMAGE}×{copies} = "
                        f"{magma_opus.DAMAGE * copies} total")

        # Rootha combat trigger: create X/X flier
        rootha.fire_combat_trigger(gs, opponent)

        self._cast_all_castable(gs)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            assignments[id(biggest)] = [max(blockers, key=lambda c: safe_toughness(c))]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent):
        zaffai.reset_turn_flag(gs)

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'canal' in n or 'vents' in n or 'fountain' in n: return 0
            return 3
        gs.play_land(min(lands, key=score))
