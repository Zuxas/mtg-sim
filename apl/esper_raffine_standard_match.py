"""
apl/esper_raffine_standard_match.py — Esper Raffine (Standard)

Pre-Strixhaven baseline. Despite the Esper name, runs as UB midrange/control
with Sheoldred as the primary threat and Faerie Mastermind as the draw engine.
Raffine, Scheming Seer drives card selection via connive on each attack.

Game plan:
T1-2: Early fliers (Faerie Mastermind, Spyglass Siren) to enable Raffine triggers
T3:   Raffine, Scheming Seer — connive X each attack, grows the board
T4:   Sheoldred (opp loses life on every draw) or Preacher of the Schism
T5+:  Kaito, Bane of Nightmares for card advantage + disruption

Removal suite: Cut Down, Go for the Throat, Phantom Interference
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import multi_set_standard, strixhaven_support

RAFFINE          = "Raffine, Scheming Seer"
SHEOLDRED        = "Sheoldred, the Apocalypse"
FAERIE_MM        = "Faerie Mastermind"
PREACHER         = "Preacher of the Schism"
SPYGLASS         = multi_set_standard.SPYGLASS_SIREN
KAITO            = "Kaito, Bane of Nightmares"
FLOODPITS        = "Floodpits Drowner"
ENDURING_CURIO   = "Enduring Curiosity"
CUT_DOWN         = "Cut Down"
GO_FOR_THROAT    = "Go for the Throat"
THREE_STEPS      = multi_set_standard.THREE_STEPS_AHEAD
PHANTOM_INT      = "Phantom Interference"
MALCOLM          = multi_set_standard.MALCOLM

THREATS = {RAFFINE, SHEOLDRED, FAERIE_MM, PREACHER, KAITO, FLOODPITS}
REMOVAL = {CUT_DOWN, GO_FOR_THROAT}
INTERACTION = {THREE_STEPS, PHANTOM_INT}


class EsperRaffineMatchAPL(MatchAPL):
    name = "Esper Raffine"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in THREATS)
        interaction = sum(1 for c in hand if c.name in REMOVAL | INTERACTION)
        if lands < 2 or lands > 5: return False
        if threats >= 1 and (lands >= 2 or interaction >= 1): return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[4:]
        filler = [c for c in hand if not c.is_land()
                  and c not in to_bottom and c.name not in THREATS]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Removal first when behind
        if opponent:
            self._use_removal(gs, opponent)

        # T1: Spyglass Siren (1/1 flier + Map token)
        for c in list(gs.zones.hand):
            if c.name == SPYGLASS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                multi_set_standard._on_resolve(gs, multi_set_standard.SPYGLASS_SIREN, c, opponent)
                break

        # T2: Faerie Mastermind (flash 1/1 flier, draws when opp draws)
        for c in list(gs.zones.hand):
            if c.name == FAERIE_MM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Faerie Mastermind: draw trigger on opp draws")
                break

        # T2: Malcolm (flash flier, chorus counters on damage)
        for c in list(gs.zones.hand):
            if c.name == MALCOLM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # T3: Raffine (connive X on each attack = major card selection)
        for c in list(gs.zones.hand):
            if c.name == RAFFINE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Raffine, Scheming Seer: connive X on attacks (X = attackers)")
                break

        # T3: Enduring Curiosity (draw on combat damage)
        for c in list(gs.zones.hand):
            if c.name == ENDURING_CURIO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # T3: Floodpits Drowner (tempo body)
        for c in list(gs.zones.hand):
            if c.name == FLOODPITS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # T4: Sheoldred (opp -2 per draw, +2 life per our draw)
        for c in list(gs.zones.hand):
            if c.name == SHEOLDRED and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Sheoldred: opp -2 per draw, +2 life per our draw")
                break

        # T4: Preacher of the Schism (3/3 lifelink, opp loses 2 on ETB)
        for c in list(gs.zones.hand):
            if c.name == PREACHER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # T5: Kaito (card advantage + disruption)
        for c in list(gs.zones.hand):
            if c.name == KAITO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Kaito, Bane of Nightmares: PW draw/discard engine")
                break

        self._cast_all_castable(gs)

        # Connive trigger: if Raffine on board and we attacked this turn,
        # approximate card selection as draw 1 per creature we have
        raffine_bf = next((c for c in gs.zones.battlefield if c.name == RAFFINE), None)
        if raffine_bf:
            attackers = [c for c in gs.zones.battlefield
                         if c.has(Tag.CREATURE) and not getattr(c, 'summoning_sickness', False)]
            if attackers:
                gs.zones.draw(1)
                gs._log(f"  Raffine connive: drew 1 (approx)")

    def _use_removal(self, gs, opponent):
        opp_threats = [c for c in opponent.zones.battlefield
                       if c.has(Tag.CREATURE) and not c.is_land()]
        if not opp_threats: return
        target = max(opp_threats, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return
        for c in list(gs.zones.hand):
            if c.name not in REMOVAL: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            gs.cast_spell(c)
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            gs._log(f"  {c.name}: kill {target.name}")
            return

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
        if not blockers: return assignments
        biggest = max(attackers, key=lambda c: safe_power(c))
        if safe_power(biggest) >= 3:
            best = max(blockers, key=lambda c: safe_toughness(c))
            assignments[id(biggest)] = [best]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        # Three Steps Ahead / Phantom Interference as interaction
        for c in list(gs.zones.hand):
            if c.name in INTERACTION and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  {c.name}: counter/interaction")
                return c
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'darkslick' in n or 'underground' in n or 'gloomlake' in n: return 0
            if 'shattered' in n or 'raffine' in n: return 1
            return 2
        gs.play_land(min(lands, key=score))
