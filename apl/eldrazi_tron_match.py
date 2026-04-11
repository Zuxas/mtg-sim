"""
apl/eldrazi_tron_match.py — Oracle-audited Eldrazi Tron APL (Modern)

Playbook engines:
A. Tron Assembly — Expedition Map finds pieces → T3 seven mana
B. Karn Toolbox — Karn fetches silver bullets from SB (Ensnaring Bridge, Trinisphere, etc.)
C. Ugin Exile Cascade — Ugin cast/static: exile colored permanents, +2 draw, 0 add mana

Key cards:
- Tron lands: Tower+Mine+Plant = 7 mana (individually 1 each)
- Expedition Map {1}: sac → search for any land (find Tron piece)
- Karn, the Great Creator {4}: +1 exile artifact, -2 fetch from SB/exile
- Ugin, Eye of the Storms {7}: cast trigger exile, static exile on colorless cast
- Thought-Knot Seer {3}{C}: ETB exile card from opponent's hand, they draw on death
- Sowing Mycospawn {3}{G}: cast trigger → land to battlefield, kicker exile land
- Devourer of Destiny {5}{C}{C}: opening hand scry, cast trigger exile colored permanent
- Ulamog {10}: cast trigger exile 2 permanents, indestructible 10/10
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

KARN       = "Karn, the Great Creator"
UGIN       = "Ugin, Eye of the Storms"
TKS        = "Thought-Knot Seer"
DEVOURER   = "Devourer of Destiny"
ULAMOG     = "Ulamog, the Ceaseless Hunger"
MYCOSPAWN  = "Sowing Mycospawn"
KOZ_CMD    = "Kozilek's Command"
DISMEMBER  = "Dismember"
EXP_MAP    = "Expedition Map"
TALISMAN_R = "Talisman of Resilience"
TALISMAN_I = "Talisman of Impulse"
RELIC      = "Relic of Progenitus"

TRON_PIECES = {"Urza's Tower", "Urza's Mine", "Urza's Power Plant"}
BIG_THREATS = {UGIN, DEVOURER, ULAMOG}


class EldraziTronMatchAPL(MatchAPL):
    name = "Eldrazi Tron"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._tron_online = False
        self._karn_wishes_used = 0

    def _count_tron_pieces(self, gs):
        """Count unique Tron pieces on battlefield."""
        pieces = set()
        for c in gs.zones.battlefield:
            if c.name in TRON_PIECES:
                pieces.add(c.name)
        return len(pieces)

    def _tron_mana_bonus(self, gs):
        """With all 3 Tron pieces, each produces 2 extra mana (total 7 from 3 lands).
        Also count Eldrazi Temple (+1), Ugin's Labyrinth (+1 if imprinted), Talismans (+1 each)."""
        bonus = 0
        pieces = self._count_tron_pieces(gs)
        if pieces == 3:
            self._tron_online = True
            bonus += 4  # 3 lands produce 7 total (normally 3), so +4 extra
        
        for c in gs.zones.battlefield:
            name = c.name or ''
            if 'Eldrazi Temple' in name:
                bonus += 1
            elif "Ugin's Labyrinth" in name:
                has_imprint = any(getattr(x, 'cmc', 0) >= 7 for x in gs.zones.exile)
                if has_imprint: bonus += 1
            elif 'Talisman' in name:
                bonus += 1
        return bonus

    def keep(self, hand, mulligans, on_play):
        """Playbook: Keep hands with Tron assembly potential or early interaction."""
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        tron = len(set(c.name for c in hand if c.name in TRON_PIECES))
        maps = sum(1 for c in hand if c.name == EXP_MAP)
        threats = sum(1 for c in hand if c.name in (KARN, UGIN, DEVOURER, ULAMOG, TKS))
        ramp = sum(1 for c in hand if 'Talisman' in (c.name or ''))
        
        if lands == 0: return False
        if tron >= 2 and (maps >= 1 or tron == 3): return True  # Tron assembly
        if tron >= 2 and threats >= 1: return True
        if lands >= 3 and threats >= 1 and ramp >= 1: return True
        if maps >= 1 and lands >= 2 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        # Keep Tron pieces and threats, bottom excess lands and duplicates
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        gs.mana_pool.flex += self._tron_mana_bonus(gs)
        avail = gs.mana_pool.total()

        # 1. Expedition Map — sacrifice to find Tron piece ({1}, {T}, sac)
        if self._count_tron_pieces(gs) < 3:
            for c in list(gs.zones.hand):
                if c.name == EXP_MAP and avail >= 1:
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    avail -= 1
                    # Simulate finding a Tron piece (draw simulates tutor)
                    gs.zones.draw(1)
                    gs._log(f"  Expedition Map: search for Tron piece ({self._count_tron_pieces(gs)+1}/3)")
                    break
        
        # Deploy Expedition Map for next turn if not searching this turn
        for c in list(gs.zones.hand):
            if c.name == EXP_MAP and avail >= 1:
                gs.cast_spell(c); avail = gs.mana_pool.total()
                break

        # 2. Talismans — ramp
        for c in list(gs.zones.hand):
            if 'Talisman' in (c.name or '') and avail >= 2:
                gs.cast_spell(c); avail = gs.mana_pool.total()
                break

        # 3. Removal — Dismember (pay 4 life for free) or Kozilek's Command
        if opponent:
            opp_cr = [c for c in opponent.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 2]
            if opp_cr:
                target = max(opp_cr, key=lambda x: safe_power(x))
                # Dismember: {1}{B/P}{B/P} = 1 mana + 4 life, deals -5/-5
                for c in list(gs.zones.hand):
                    if c.name == DISMEMBER and avail >= 1:
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.life -= 4  # pay Phyrexian mana
                        avail -= 1
                        if safe_toughness(target) <= 5 and target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                            gs._log(f"  Dismember: kill {target.name} (paid 4 life)")
                        break

        # 4. Thought-Knot Seer ({3}{C}) — ETB: exile card from opponent's hand
        for c in list(gs.zones.hand):
            if c.name == TKS and avail >= 4:
                gs.cast_spell(c)
                if opponent and opponent.zones.hand:
                    # Exile their best card (highest CMC)
                    best = max(opponent.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
                    opponent.zones.hand.remove(best)
                    opponent.zones.exile.append(best)
                    gs._log(f"  TKS: exile {best.name} from opponent's hand")
                avail = gs.mana_pool.total()
                break

        # 5. Karn, the Great Creator ({4}) — fetch silver bullet from SB
        for c in list(gs.zones.hand):
            if c.name == KARN and avail >= 4:
                gs.cast_spell(c)
                # -2: fetch artifact from SB (simulate as draw 1)
                gs.zones.draw(1)
                self._karn_wishes_used += 1
                gs._log(f"  Karn: fetch silver bullet from SB (wish #{self._karn_wishes_used})")
                # +1 passive: opponent's artifacts can't activate abilities (Stony Silence effect)
                avail = gs.mana_pool.total()
                break

        # 6. Sowing Mycospawn ({3}{G}) — cast trigger: land to battlefield
        for c in list(gs.zones.hand):
            if c.name == MYCOSPAWN and avail >= 4:
                gs.cast_spell(c)
                gs.mana_pool.flex += 1  # simulate new land
                gs._log(f"  Mycospawn: 3/3 + land to battlefield")
                avail = gs.mana_pool.total()
                break

        # 7. Ugin PW ({7}) — cast trigger exile, static exile on colorless cast
        for c in list(gs.zones.hand):
            if c.name == UGIN and avail >= 7:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                if opponent:
                    targets = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if targets:
                        t = max(targets, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.exile.append(t)
                        gs._log(f"  Ugin CAST: exile {t.name}")
                avail -= 7
                break

        # 8. Devourer of Destiny ({5}{C}{C}) — cast trigger exile colored permanent
        for c in list(gs.zones.hand):
            if c.name == DEVOURER and avail >= 7:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                if opponent:
                    targets = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if targets:
                        t = max(targets, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.exile.append(t)
                        gs._log(f"  Devourer CAST: exile {t.name}")
                avail -= 7
                break

        # 9. Ulamog ({10}) — cast trigger: exile 2 target permanents, indestructible 10/10
        for c in list(gs.zones.hand):
            if c.name == ULAMOG and avail >= 10:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                if opponent:
                    for _ in range(2):
                        targets = [x for x in opponent.zones.battlefield]
                        if targets:
                            t = max(targets, key=lambda x: safe_power(x) if x.has(Tag.CREATURE) else 0)
                            opponent.zones.battlefield.remove(t)
                            opponent.zones.exile.append(t)
                            gs._log(f"  Ulamog CAST: exile {t.name}")
                break

        # 10. Kozilek's Command ({X}{C}{C}) — flexible: tokens, scry+draw, exile creature
        for c in list(gs.zones.hand):
            if c.name == KOZ_CMD and avail >= 3:
                x_val = avail - 2
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                if opponent:
                    # Mode: exile creature MV <= X
                    opp_cr = [x for x in opponent.zones.battlefield
                             if x.has(Tag.CREATURE) and not x.is_land()
                             and getattr(x, 'cmc', 0) <= x_val]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.exile.append(t)
                        gs._log(f"  Koz Command X={x_val}: exile {t.name} + scry+draw")
                    else:
                        gs._log(f"  Koz Command X={x_val}: {x_val} Spawn tokens + scry+draw")
                gs.zones.draw(1)  # scry + draw mode
                break

        # 11. Fill remaining
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in BIG_THREATS:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                   and not c.is_land() and safe_power(c) >= 4
                   and not getattr(c, 'tapped', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        """Priority: complete Tron > Labyrinth > Temple > other."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        # Find which Tron pieces are missing
        on_board = set(c.name for c in gs.zones.battlefield if c.name in TRON_PIECES)
        missing = TRON_PIECES - on_board
        def score(c):
            if c.name in missing: return 0  # complete Tron first
            if 'labyrinth' in (c.name or '').lower(): return 1
            if 'temple' in (c.name or '').lower(): return 2
            return 5
        best = min(lands, key=score)
        gs.play_land(best)
        # Labyrinth imprint
        if "ugin's labyrinth" in (best.name or '').lower():
            big = [c for c in gs.zones.hand if getattr(c, 'cmc', 0) >= 7 and not c.is_land()]
            if big:
                gs.zones.hand.remove(big[0]); gs.zones.exile.append(big[0])
                gs._log(f"  Labyrinth imprint: exile {big[0].name}")
