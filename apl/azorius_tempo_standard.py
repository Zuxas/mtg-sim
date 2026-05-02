"""
apl/azorius_tempo_standard.py -- Azorius Tempo goldfish APL (Standard)

Game plan:
  T1: Momo, Friendly Flier (1/1 flying, next flying spell costs {1} less)
      OR Gran-Gran (1/2, tap to loot, makes noncreature spells cost {1} less)
  T2: Voice of Victory (1/3 mobilize 2 = 3 attackers), Elusive Otter, Sage of Skies
  T3: Haliya (3/3, gains life on ETBs), Cosmogrand Zenith
  Counterspells (Annul, Essence Scatter, No More Lies) held up through main1,
  deployed post-combat or at EOT in match. Goldfish: cast whenever affordable.

Key: Momo reduces cost of flying spells. Sage copies itself if another
spell was cast first. Gran-Gran makes noncreature spells cheaper at 3+ lessons in GY.
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

MOMO       = "Momo, Friendly Flier"
GRAN       = "Gran-Gran"
OTTER      = "Elusive Otter"
VOICE      = "Voice of Victory"
HALIYA     = "Haliya, Guided by Light"
SAGE       = "Sage of the Skies"
COSMO      = "Cosmogrand Zenith"
GET_LOST   = "Get Lost"
ANNUL      = "Annul"
SCATTER    = "Essence Scatter"
NO_MORE    = "No More Lies"
SEAM       = "Seam Rip"
FLOW       = "Flow State"
OPT        = "Opt"

# Cast before Sage to trigger its copy condition
SAGE_ENABLERS = {MOMO, GRAN, OTTER, VOICE, OPT, SEAM, FLOW}

# Creature threats in priority order (cheapest first)
THREATS = (MOMO, GRAN, OTTER, VOICE, HALIYA, COSMO)

# Reactive spells — in goldfish, just cast them to clear hand/mana
REACT = {ANNUL, SCATTER, NO_MORE, GET_LOST, SEAM, FLOW, OPT}


class AzoriusTempoAPL(BaseAPL):
    name = "Azorius Tempo"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = [c for c in hand if c.is_land()]
        if len(lands) == 0:
            return False
        if len(lands) > 5:
            return False
        threats = [c for c in hand if c.name in {MOMO, GRAN, OTTER, VOICE, SAGE}]
        return len(threats) >= 1 or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        excess = lands[4:]
        return (excess + spells)[:n]

    def main_phase(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if lands and not gs.land_played:
            gs.play_land(lands[0])
        gs.tap_lands()

        # Apply Momo and Gran-Gran cost reductions
        momo_on_board = any(c.name == MOMO for c in gs.zones.battlefield
                            if not c.is_land())
        gran_on_board = any(c.name == GRAN for c in gs.zones.battlefield
                            if not c.is_land())
        lessons_in_gy = sum(1 for c in gs.zones.graveyard
                            if 'Lesson' in (getattr(c, 'type_line', '') or ''))
        if momo_on_board:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)
        if gran_on_board and lessons_in_gy >= 3:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)

        # Cast an enabler before Sage to trigger its copy
        sage_in_hand = any(c.name == SAGE for c in gs.zones.hand)
        if sage_in_hand:
            for card in list(gs.zones.hand):
                if card.name in SAGE_ENABLERS and not card.is_land():
                    if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # Cast threats
        changed = True
        while changed:
            changed = False
            hand_names = {c.name: c for c in gs.zones.hand if not c.is_land()}
            for name in THREATS:
                card = hand_names.get(name)
                if card and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    if gs.cast_spell(card):
                        changed = True
                        break

        # Cast Sage of the Skies (copies if another spell was cast this turn)
        for card in list(gs.zones.hand):
            if card.name == SAGE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

        # Dump remaining spells (reactive spells, etc.)
        for card in sorted(list(gs.zones.hand),
                           key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in list(gs.zones.hand):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
