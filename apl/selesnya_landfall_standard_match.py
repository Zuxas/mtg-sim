"""
apl/selesnya_landfall_standard_match.py — Selesnya Landfall (Standard, PT SOS 2026)

Key engine:
- Tifa Lockhart ({1}{G}): 2/2 trample, landfall doubles power until EoT
- Sazh's Chocobo ({G}): 1/1, landfall puts +1/+1 counter
- Mossborn Hydra ({2}{G}): trample, grows from counters
- Earthbender Ascension ({2}{G}): ETB earthbend 2 + tutor basic land (free landfall trigger)
- Llanowar Elves: T1 mana acceleration
- Fabled Passage: fetchland for double landfall trigger
"""
from data.card import Card, Tag
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TIFA       = "Tifa Lockhart"
CHOCOBO    = "Sazh's Chocobo"
HYDRA      = "Mossborn Hydra"
ASCENSION  = "Earthbender Ascension"
ELVES      = "Llanowar Elves"
BADGERMOLE = "Badgermole Cub"


class SelesnyaLandfallStandardMatchAPL(MatchAPL):
    name = "Selesnya Landfall"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in (TIFA, CHOCOBO, HYDRA, ELVES))
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and lands >= 2: return True
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

        # Deploy threats cheapest first — Chocobo/Elves T1, Tifa T2, Hydra/Ascension T3
        changed = True
        attempts = 0
        while changed and attempts < 10:
            changed = False; attempts += 1
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if castable:
                spell = min(castable, key=lambda c: getattr(c, 'cmc', 0))
                if gs.cast_spell(spell):
                    # Earthbender Ascension ETB: earthbend + tutor basic = extra land drop
                    if spell.name == ASCENSION:
                        basics = [x for x in gs.zones.library if x.is_land()]
                        if basics:
                            land = basics[0]
                            gs.zones.library.remove(land)
                            gs.zones.battlefield.append(land)
                            land.turn_entered = gs.turn
                            self._trigger_landfall(gs)
                            gs._log(f"  Earthbender Ascension: earthbend + tutor {land.name}")
                    changed = True
                else:
                    break

        # Cast enchantments/other spells
        for c in list(gs.zones.hand):
            if not c.is_land() and not c.has(Tag.CREATURE):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def _trigger_landfall(self, gs):
        """Apply landfall triggers when a land enters."""
        for c in gs.zones.battlefield:
            if c.name == TIFA:
                # Tifa doubles power until EoT (simulate as +power each land)
                try:
                    c.power = str(int(c.power) * 2)
                except (ValueError, TypeError):
                    pass
            elif c.name == CHOCOBO:
                # +1/+1 counter
                try:
                    c.power = str(int(c.power) + 1)
                    c.toughness = str(int(c.toughness) + 1)
                except (ValueError, TypeError):
                    pass

    def declare_attackers(self, gs, opponent):
        # Trigger Tifa doubling on the land we played this turn
        self._trigger_landfall(gs)
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and safe_toughness(c) >= 3]
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
            if 'passage' in n or 'tunnel' in n: return 0
            if 'forest' in n or 'plains' in n: return 1
            return 3
        land = min(lands, key=score)
        gs.play_land(land)
        self._trigger_landfall(gs)
