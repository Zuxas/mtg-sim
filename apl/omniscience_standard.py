"""
apl/omniscience_standard.py -- Omniscience combo shell (Standard / PT SOS 2026)

Shared engine: Formidable Speaker cheats Omniscience into play (or tutors it),
then casts Uthros, Titanic Godcore / Kona, Rescue Beastie / Roiling Dragonstorm
for free. Wins T4-6 when the combo assembles.

Simic (G/U): Kona + Uthros + Evendo
Bant  (W/G/U): adds Adagia, Marang River Regent, Roiling Dragonstorm
Temur (G/U/R): adds Ashling, Rekindled + Kavaron, Memorial World
"""
from apl.base_apl import BaseAPL

OMNISCIENCE = "Omniscience"
SPEAKER     = "Formidable Speaker"
UTHROS      = "Uthros, Titanic Godcore"
KONA        = "Kona, Rescue Beastie"
EVENDO      = "Evendo, Waking Haven"
STOCK_UP    = "Stock Up"
BOUNCE_OFF  = "Bounce Off"
MARANG      = "Marang River Regent"
ADAGIA      = "Adagia, Windswept Bastion"
DRAGONSTORM = "Roiling Dragonstorm"
ASHLING     = "Ashling, Rekindled"
KAVARON     = "Kavaron, Memorial World"

COMBO_PIECES = (SPEAKER, OMNISCIENCE)
PAYOFFS      = (UTHROS, KONA, EVENDO, MARANG, ADAGIA, DRAGONSTORM, ASHLING, KAVARON)
CANTRIPS     = (STOCK_UP, BOUNCE_OFF)


class OmniscienceAPL(BaseAPL):
    name = "Omniscience"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        has_combo = any(c.name in {SPEAKER, OMNISCIENCE} for c in hand)
        return has_combo or mulligans >= 2

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

        # Priority: combo pieces first, then payoffs, then cantrips
        for name in (*COMBO_PIECES, *PAYOFFS, *CANTRIPS):
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)


class SimicOmniscienceAPL(OmniscienceAPL):
    name = "Simic Omniscience"


class BantOmniscienceAPL(OmniscienceAPL):
    name = "Bant Omniscience"


class TemurOmniscienceAPL(OmniscienceAPL):
    name = "Temur Omniscience"
