"""
apl/goryos_match.py — Oracle-audited Goryo's Vengeance APL (Modern)

Playbook engines:
A. Goryo's + Ephemerate — reanimate legendary, blink to keep permanently
   Key: Goryo's gives haste + exile at end step. Ephemerate BEFORE end step = keeps it.
B. Solitude + Ephemerate — free evoke exile + blink (same as Blink deck)
C. Psychic Frog — alt clock + discard outlet for reanimation targets

Combo line: Atraxa/Griselbrand in GY → Goryo's ({1}{B}) → Ephemerate ({W}) → permanent 7/7
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

ATRAXA    = "Atraxa, Grand Unifier"
GRISELBRAND = "Griselbrand"
ULAMOG_D  = "Ulamog, the Defiler"
PSYCHIC   = "Psychic Frog"
SOLITUDE  = "Solitude"
QUANTUM   = "Quantum Riddler"
GORYOS    = "Goryo's Vengeance"
EPHEMERATE = "Ephemerate"
THOUGHTSEIZE = "Thoughtseize"
PRISMATIC = "Prismatic Ending"
FATAL     = "Fatal Push"

REANIMATE_TARGETS = {ATRAXA, GRISELBRAND, ULAMOG_D}
REMOVAL = {SOLITUDE, PRISMATIC, FATAL}


class GoryosMatchAPL(MatchAPL):
    name = "Goryos Vengeance"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._combo_assembled = False
        self._ephemerate_rebound = False

    def keep(self, hand, mulligans, on_play):
        """Snap keep: Goryo's + Atraxa/Griselbrand + Ephemerate. Or Psychic Frog + discard fuel."""
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_goryos = any(c.name == GORYOS for c in hand)
        has_target = any(c.name in REANIMATE_TARGETS for c in hand)
        has_eph = any(c.name == EPHEMERATE for c in hand)
        has_frog = any(c.name == PSYCHIC for c in hand)
        has_solitude = any(c.name == SOLITUDE for c in hand)
        threats = sum(1 for c in hand if c.name in (PSYCHIC, QUANTUM, SOLITUDE))

        if lands == 0: return False
        if has_goryos and has_target and lands >= 2: return True  # combo hand
        if has_goryos and has_target and has_eph: return True  # full combo
        if has_frog and has_target and lands >= 2: return True  # discard Atraxa, play Frog
        if threats >= 2 and lands >= 2: return True  # fair game
        if has_solitude and has_eph and lands >= 2: return True  # Solitude combo
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        avail = gs.mana_pool.total()

        # Ephemerate Rebound
        if self._ephemerate_rebound:
            self._ephemerate_rebound = False
            self._blink_best_etb(gs, opponent)

        # 1. Thoughtseize ({B}) — take opponent's best card + see hand
        for c in list(gs.zones.hand):
            if c.name == THOUGHTSEIZE and avail >= 1:
                gs.mana_pool.pay("{B}", 1) if gs.mana_pool.can_pay("{B}", 1) else None
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs.life -= 2  # Thoughtseize costs 2 life
                if opponent and opponent.zones.hand:
                    best = max(opponent.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
                    opponent.zones.hand.remove(best)
                    opponent.zones.graveyard.append(best)
                    gs._log(f"  Thoughtseize: take {best.name} (-2 life)")
                avail = gs.mana_pool.total()
                break

        # 2. Solitude EVOKE — free creature exile (pitch white card)
        if opponent:
            opp_threats = [c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 2]
            if opp_threats:
                for c in list(gs.zones.hand):
                    if c.name == SOLITUDE:
                        white_cards = [x for x in gs.zones.hand if x != c and not x.is_land()
                                      and 'W' in (getattr(x, 'colors', []) or [])]
                        if white_cards:
                            pitch = white_cards[0]
                            gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                            gs.zones.hand.remove(c)
                            target = max(opp_threats, key=lambda x: safe_power(x))
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.exile.append(target)
                                opponent.life += safe_power(target)
                            gs._log(f"  Solitude EVOKE: exile {target.name}")
                            # Ephemerate to keep Solitude + double exile
                            eph = next((x for x in gs.zones.hand if x.name == EPHEMERATE), None)
                            if eph and avail >= 1:
                                gs.zones.hand.remove(eph); gs.zones.exile.append(eph)
                                self._ephemerate_rebound = True
                                gs.zones.battlefield.append(c)
                                c.turn_entered = gs.turn; c.summoning_sickness = True
                                opp2 = [x for x in opponent.zones.battlefield
                                       if not x.is_land() and x.has(Tag.CREATURE)]
                                if opp2:
                                    t2 = max(opp2, key=lambda x: safe_power(x))
                                    opponent.zones.battlefield.remove(t2)
                                    opponent.zones.exile.append(t2)
                                    gs._log(f"  Ephemerate Solitude: exile {t2.name} (stays + rebound)")
                            else:
                                gs.zones.graveyard.append(c)
                            break

        # 3. THE COMBO: Goryo's Vengeance ({1}{B}) — reanimate from GY
        gy_targets = [c for c in gs.zones.graveyard if c.name in REANIMATE_TARGETS]
        if gy_targets and avail >= 2:
            for c in list(gs.zones.hand):
                if c.name == GORYOS:
                    gs.mana_pool.pay("{1}{B}", 2) if gs.mana_pool.can_pay("{1}{B}", 2) else None
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    # Reanimate best target
                    target = max(gy_targets, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.graveyard.remove(target)
                    gs.zones.battlefield.append(target)
                    target.turn_entered = gs.turn; target.summoning_sickness = False  # haste!
                    gs._log(f"  GORYO'S VENGEANCE: reanimate {target.name} (haste!)")
                    self._combo_assembled = True
                    # Atraxa ETB: look at top 10, take one of each type (simulate as draw 4)
                    if target.name == ATRAXA:
                        gs.zones.draw(4)
                        gs._log(f"    Atraxa ETB: draw ~4 from top 10")
                    elif target.name == GRISELBRAND:
                        # Pay 7 life: draw 7
                        if gs.life > 7:
                            gs.life -= 7; gs.zones.draw(7)
                            gs._log(f"    Griselbrand: pay 7 life, draw 7")
                    # EPHEMERATE to keep permanently!
                    eph = next((x for x in gs.zones.hand if x.name == EPHEMERATE), None)
                    if eph:
                        gs.zones.hand.remove(eph); gs.zones.exile.append(eph)
                        self._ephemerate_rebound = True
                        gs._log(f"    Ephemerate: {target.name} STAYS permanently (rebound next turn)")
                        # Re-trigger ETB on re-entry
                        if target.name == ATRAXA:
                            gs.zones.draw(4)
                            gs._log(f"    Atraxa ETB #2: draw ~4 more")
                    avail = gs.mana_pool.total()
                    break
        else:
            # No targets in GY — try to discard one via Psychic Frog
            pass

        # 4. Psychic Frog ({U}{B}) — discard outlet + flying clock
        for c in list(gs.zones.hand):
            if c.name == PSYCHIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # Discard a reanimation target to GY for Goryo's
                targets_in_hand = [x for x in gs.zones.hand if x.name in REANIMATE_TARGETS]
                if targets_in_hand:
                    t = targets_in_hand[0]
                    gs.zones.hand.remove(t); gs.zones.graveyard.append(t)
                    gs._log(f"  Psychic Frog: discard {t.name} to GY (Goryo's setup)")
                avail = gs.mana_pool.total()
                break

        # 5. Quantum Riddler ({3}{U}{U}) — 4/6 flying, draw 1
        for c in list(gs.zones.hand):
            if c.name == QUANTUM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c); gs.zones.draw(1)
                gs._log(f"  Quantum Riddler: 4/6 flying, draw 1")
                break

        # 6. Removal
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == FATAL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    opp_cr = [x for x in opponent.zones.battlefield
                             if x.has(Tag.CREATURE) and not x.is_land() and getattr(x,'cmc',0) <= 2]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        opponent.zones.battlefield.remove(t); opponent.zones.graveyard.append(t)
                        gs._log(f"  Fatal Push: kill {t.name}")
                    break

        # 7. Fill curve
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in REANIMATE_TARGETS:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def _blink_best_etb(self, gs, opponent):
        for name in (SOLITUDE, ATRAXA, QUANTUM):
            cr = next((c for c in gs.zones.battlefield if c.name == name), None)
            if cr:
                if name == SOLITUDE and opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                             if x.has(Tag.CREATURE) and not x.is_land()]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t); opponent.zones.exile.append(t)
                        gs._log(f"  Blink Solitude: exile {t.name}")
                elif name == ATRAXA:
                    gs.zones.draw(4)
                    gs._log(f"  Blink Atraxa: draw ~4")
                elif name == QUANTUM:
                    gs.zones.draw(1)
                    gs._log(f"  Blink Quantum: draw 1")
                return

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        return {}

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'delta' in n or 'strand' in n or 'flats' in n: return 0
            if 'grave' in n or 'shrine' in n or 'fountain' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
