"""
apl/azorius_momo_standard.py -- Azorius Momo goldfish APL (Standard)

Game plan:
  T1: Momo, Friendly Flier (1/1 flying, reduces next flying spell by 1)
  T2: Voice of Victory (1/3, mobilize 2 = 3 attackers total with tokens)
       or Springleaf Drum into T2 4-drop via artifact mana
  T3: Haliya (3/3, gains life on each ETB) or Sage of the Skies
       Sage copies itself if another spell was cast this turn — play
       Springleaf Drum or Nurturing Pixie first to trigger the copy.
  T4: Cosmogrand Zenith (tokens or counters on ETB)

Key interaction: Momo reduces first flying spell each turn by {1}.
Sage of the Skies copies itself only if another spell was cast this turn —
APL casts cheapest non-Sage spell first, then Sage.
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

MOMO    = "Momo, Friendly Flier"
VOICE   = "Voice of Victory"
HALIYA  = "Haliya, Guided by Light"
SAGE    = "Sage of the Skies"
COSMO   = "Cosmogrand Zenith"
PIXIE   = "Nurturing Pixie"
DRUM    = "Springleaf Drum"
ANIMALS = "Curious Farm Animals"
SEAM    = "Seam Rip"

# Cast these before Sage to trigger its copy condition
SAGE_ENABLERS = {DRUM, PIXIE, SEAM, ANIMALS, MOMO, VOICE}

# Threats in curve order (without Sage — handled specially)
THREATS = (MOMO, VOICE, PIXIE, HALIYA, COSMO)


class AzoriusMomoAPL(BaseAPL):
    name = "Azorius Momo"
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
        threats = [c for c in hand if c.name in {MOMO, VOICE, HALIYA, SAGE}]
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

        # Apply Momo's cost reduction: if Momo is on board, the first
        # flying spell costs {1} less. Proxy via cost_reduction flag.
        momo_on_board = any(c.name == MOMO for c in gs.zones.battlefield
                            if not c.is_land())
        if momo_on_board:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)

        # Cast a non-Sage enabler first so Sage copies itself
        sage_in_hand = any(c.name == SAGE for c in gs.zones.hand)
        if sage_in_hand:
            for card in list(gs.zones.hand):
                if card.name in SAGE_ENABLERS and not card.is_land():
                    if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # Now cast remaining threats (Sage last so copy condition is met)
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

        # Cast Sage — if another spell was cast this turn it copies itself
        # (handled by Sage's ETB handler in card_effects)
        for card in list(gs.zones.hand):
            if card.name == SAGE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

        # Dump remaining
        for card in sorted(list(gs.zones.hand),
                           key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in list(gs.zones.hand):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
