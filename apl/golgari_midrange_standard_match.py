"""
apl/golgari_midrange_standard_match.py — Golgari Midrange (Standard, PT SOS 2026)

Key engine:
- Llanowar Elves: T1 mana acceleration
- Badgermole Cub ({1}{G}): ETB earthbend (animates land temporarily)
- Requiting Hex ({B}): blight own creature → destroy target creature (1-mana removal)
- Maelstrom Pulse ({1}{B}{G}): destroy target nonland + all with same name
- Professor Dellian Fel ({2}{B}{G}): planeswalker — +2 gain 3, 0 draw/-1, -3 destroy creature
- Duress: T1 hand disruption
"""
from data.card import Card, Tag
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

ELVES    = "Llanowar Elves"
BADGER   = "Badgermole Cub"
HEX      = "Requiting Hex"
PULSE    = "Maelstrom Pulse"
PROF     = "Professor Dellian Fel"
DURESS   = "Duress"


class GolgariMidrangeStandardMatchAPL(MatchAPL):
    name = "Golgari Midrange"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_elves = any(c.name == ELVES for c in hand)
        has_removal = any(c.name in (HEX, PULSE) for c in hand)
        threats = sum(1 for c in hand if c.has(Tag.CREATURE) or c.name == PROF)
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and lands >= 2: return True
        if has_elves and lands >= 2: return True
        if has_removal and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # Set _match_opp so removal handlers (Requiting Hex, Maelstrom Pulse, etc.)
        # can find the opponent when fired via cast_spell's ETB/spell hooks.
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Duress T1/T2 — hand disruption
        if opponent and gs.turn <= 2:
            for c in list(gs.zones.hand):
                if c.name == DURESS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    nonlands = [x for x in opponent.zones.hand
                                if not x.is_land() and not x.has(Tag.CREATURE)]
                    if nonlands:
                        target = max(nonlands, key=lambda x: getattr(x, 'cmc', 0))
                        opponent.zones.hand.remove(target)
                        opponent.zones.graveyard.append(target)
                        gs._log(f"  Duress: discard {target.name}")
                    break

        # 2. Requiting Hex — 1-mana removal (blight own creature)
        # Oracle: "As additional cost, blight 1 (put -1/-1 counter on own creature).
        #          Destroy target creature."
        if opponent:
            opp_threats = [c for c in opponent.zones.battlefield
                           if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 3]
            if opp_threats:
                for c in list(gs.zones.hand):
                    if c.name == HEX and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        blight_targets = [x for x in gs.zones.battlefield
                                          if x.has(Tag.CREATURE) and not x.is_land()]
                        if blight_targets:
                            # Blight weakest own creature
                            blight = min(blight_targets, key=lambda x: safe_power(x))
                            try:
                                blight.power = str(max(0, int(blight.power) - 1))
                                blight.toughness = str(max(0, int(blight.toughness) - 1))
                                if int(blight.toughness) <= 0:
                                    gs.zones.battlefield.remove(blight)
                                    gs.zones.graveyard.append(blight)
                            except (ValueError, TypeError):
                                pass
                            gs.cast_spell(c)  # _requiting_hex handler destroys target
                            break

        # 3. Maelstrom Pulse — destroy target + all with same name
        if opponent:
            opp_threats = [c for c in opponent.zones.battlefield
                           if not c.is_land() and safe_power(c) >= 2]
            if opp_threats:
                for c in list(gs.zones.hand):
                    if c.name == PULSE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)  # _maelstrom_pulse_spell handler destroys target + copies
                        break

        # 4. Deploy threats cheapest first
        changed = True
        attempts = 0
        while changed and attempts < 10:
            changed = False; attempts += 1
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if castable:
                spell = min(castable, key=lambda c: getattr(c, 'cmc', 0))
                if gs.cast_spell(spell): changed = True
                else: break

        # 5. Professor Dellian Fel — deploy planeswalker
        for c in list(gs.zones.hand):
            if c.name == PROF and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # Use +2: gain 3 life if we're low, else use 0: draw/-1 life
                if gs.life < 10:
                    gs.life += 3
                    gs._log(f"  Prof. Dellian Fel +2: gain 3 life")
                else:
                    gs.zones.draw(1); gs.life -= 1
                    gs._log(f"  Prof. Dellian Fel 0: draw 1, lose 1 life")
                break

    def declare_attackers(self, gs, opponent):
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
            if 'blooming' in n or 'overgrown' in n or 'passage' in n: return 0
            if 'wastewood' in n or 'annex' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
