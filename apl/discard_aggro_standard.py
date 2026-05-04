"""
apl/discard_aggro_standard.py — Shared goldfish APL for Mardu/Rakdos/Boros Discard (Standard)

Discard-payoff aggro shell. Shared cards across all three color variants:
  Iron-Shield Elf  (1R, triggers on discard)
  Marauding Mako   (2B, grows when you discard)
  Moonshadow       (1B, creates tokens on discard)
  Cool but Rude    (2, discard a card — the engine)
  Bloodghast       (BB, recurs when you play a land)

Game plan: turn 2 payoff creature, turn 2-3 Cool but Rude to trigger it,
Bloodghast provides recurring pressure. Kill around T4-6.
"""
from apl.base_apl import BaseAPL

IRON_SHIELD  = "Iron-Shield Elf"
MAKO         = "Marauding Mako"
MOONSHADOW   = "Moonshadow"
COOL_RUDE    = "Cool but Rude"
BLOODGHAST   = "Bloodghast"
INTI         = "Inti, Seneschal of the Sun"
HIRED_CLAW   = "Hired Claw"
FLAMEWAKE    = "Flamewake Phoenix"
CASEY        = "Casey Jones, Vigilante"
HARDENED_AC  = "Hardened Academic"
PRACTICED    = "Practiced Offense"

PAYOFFS  = (MAKO, MOONSHADOW, INTI)
ENABLERS = (COOL_RUDE, PRACTICED, IRON_SHIELD, HIRED_CLAW)
THREATS  = (IRON_SHIELD, HIRED_CLAW, BLOODGHAST, MAKO, MOONSHADOW,
            FLAMEWAKE, CASEY, INTI, HARDENED_AC)


class DiscardAggroAPL(BaseAPL):
    name = "Discard Aggro"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        payoffs  = sum(1 for c in hand if c.name in set(PAYOFFS))
        enablers = sum(1 for c in hand if c.name in set(ENABLERS))
        return (payoffs >= 1 and enablers >= 1) or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if lands and not gs.land_played:
            gs.play_land(lands[0])
        gs.tap_lands()

        # Play payoff creatures first so enablers trigger them
        for name in PAYOFFS:
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Play enablers to trigger payoffs already on board
        for name in ENABLERS:
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Dump remaining threats
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)


class MarduDiscardAPL(DiscardAggroAPL):
    name = "Mardu Discard"


class RakdosDiscardAPL(DiscardAggroAPL):
    name = "Rakdos Discard"


class BorosDiscardAPL(DiscardAggroAPL):
    name = "Boros Discard"
