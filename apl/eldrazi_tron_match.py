"""
apl/eldrazi_tron_match.py — Match-aware Eldrazi Tron APL (Modern)

Key match mechanics:
1. Tron assembly: Mine+Plant+Tower = 7 colorless mana by T3
2. Thought-Knot Seer: 4/4 ETB exile card from opponent's hand
3. Karn, the Great Creator: tutors artifacts from SB (Chalice, Bridge)
4. Chalice of the Void: on 1 locks out 1-drops (devastating vs Prowess)
5. Dismember: -5/-5 for 1 mana + 4 life (kills anything)
6. All Is Dust: board wipe for colored permanents
7. Expedition Map: tutors Tron pieces
"""
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TKS        = "Thought-Knot Seer"
KARN       = "Karn, the Great Creator"
DEVOURER   = "Devourer of Destiny"
FLESHRAKER = "Glaring Fleshraker"
SIRE       = "Sire of Seven Deaths"
CHALICE    = "Chalice of the Void"
DISMEMBER  = "Dismember"
ALL_IS_DUST = "All Is Dust"
MAP        = "Expedition Map"
MIND_STONE = "Mind Stone"
KOZ_CMD    = "Kozilek's Command"
UGIN_STORM = "Ugin, Eye of the Storms"
TEMPLE     = "Eldrazi Temple"

TRON_PIECES = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}


class EldraziTronMatchAPL(MatchAPL):
    name = "Eldrazi Tron"
    win_condition_damage = 20
    max_turns = 12
    _tron_online = False

    def _check_tron(self, gs):
        land_names = {c.name for c in gs.zones.battlefield if c.is_land()}
        self._tron_online = TRON_PIECES.issubset(land_names)
        return self._tron_online

    def _tron_mana(self, gs):
        """Estimate available mana with Tron + Temple + Mind Stone."""
        lands = [c for c in gs.zones.battlefield if c.is_land()]
        mana = 0
        has_mine = has_plant = has_tower = False
        for l in lands:
            if l.name == "Urza's Mine": has_mine = True
            elif l.name == "Urza's Power Plant": has_plant = True
            elif l.name == "Urza's Tower": has_tower = True
            elif l.name == TEMPLE: mana += 2  # Eldrazi Temple adds 2 for Eldrazi
            elif l.name == "Ugin's Labyrinth": mana += 2
            else: mana += 1
        if has_mine and has_plant and has_tower:
            mana += 7  # Tron = 7 mana
        else:
            mana += sum(1 for x in (has_mine, has_plant, has_tower) if x)
        # Mind Stones on field
        mana += sum(1 for c in gs.zones.battlefield if c.name == MIND_STONE)
        return mana

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        tron_count = sum(1 for c in hand if c.name in TRON_PIECES)
        maps = sum(1 for c in hand if c.name == MAP)
        threats = sum(1 for c in hand if c.name in {TKS, KARN, DEVOURER, FLESHRAKER})
        if lands == 0: return False
        if tron_count >= 2 and (maps >= 1 or tron_count == 3): return True
        if lands >= 2 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # Play land (prioritize Tron pieces)
        self._play_tron_land(gs)
        self._check_tron(gs)
        gs.tap_lands()
        avail = self._tron_mana(gs)

        # 1. Chalice on 1 vs aggro (devastating)
        if opponent and gs.turn <= 2:
            for c in list(gs.zones.hand):
                if c.name == CHALICE and avail >= 2:
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    gs._log(f"  Chalice of the Void on 1 (locks out 1-drops)")
                    break

        # 2. Dismember on big threats (pay 4 life for 1 mana)
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 3]
            if opp_creatures:
                target = max(opp_creatures, key=lambda c: safe_power(c))
                for c in list(gs.zones.hand):
                    if c.name == DISMEMBER:
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        gs.life -= 4  # pay 4 life
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                        gs._log(f"  Dismember (4 life) → kill {target.name}")
                        break

        # 3. Mind Stone for ramp
        for c in list(gs.zones.hand):
            if c.name == MIND_STONE and avail >= 2:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                break

        # 4. Thought-Knot Seer — exile opponent's best card
        avail = self._tron_mana(gs)
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == TKS and avail >= 4:
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    c.summoning_sickness = True
                    opp_nonlands = [x for x in opponent.zones.hand if not x.is_land()]
                    if opp_nonlands:
                        target = max(opp_nonlands, key=lambda x: getattr(x, 'cmc', 0))
                        opponent.zones.hand.remove(target)
                        opponent.zones.exile.append(target)
                        gs._log(f"  TKS → exile {target.name}")
                    avail -= 4
                    break

        # 5. Karn — tutor from SB (we just deploy as a threat)
        for c in list(gs.zones.hand):
            if c.name == KARN and avail >= 4:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                avail -= 4
                break

        # 6. Big threats: Devourer, Fleshraker, Sire, Ugin
        for name in (FLESHRAKER, DEVOURER, SIRE, UGIN_STORM):
            for c in list(gs.zones.hand):
                if c.name == name and avail >= getattr(c, 'cmc', 99):
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    c.summoning_sickness = True
                    avail -= getattr(c, 'cmc', 0)
                    break

        # 7. All Is Dust — board wipe when behind
        if opponent and avail >= 7:
            opp_board = sum(1 for c in opponent.zones.battlefield
                           if not c.is_land() and c.has(Tag.CREATURE))
            our_board = sum(1 for c in gs.zones.battlefield
                           if not c.is_land() and c.has(Tag.CREATURE))
            if opp_board >= our_board + 2:
                for c in list(gs.zones.hand):
                    if c.name == ALL_IS_DUST:
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        # Remove all colored permanents from both sides
                        for p in list(opponent.zones.battlefield):
                            if not p.is_land():
                                opponent.zones.battlefield.remove(p)
                                opponent.zones.graveyard.append(p)
                        gs._log(f"  All Is Dust — wiped {opp_board} opponent creatures")
                        break

        # 8. Remaining creatures
        changed = True
        while changed:
            changed = False
            castable = [c for c in gs.zones.hand if not c.is_land()
                        and c.has(Tag.CREATURE) and getattr(c,'cmc',99) <= avail]
            if castable:
                spell = min(castable, key=lambda c: c.cmc)
                if gs.cast_spell(spell): changed = True; avail -= spell.cmc
                else: break

    def _play_tron_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        bf_names = {c.name for c in gs.zones.battlefield if c.is_land()}
        # Prioritize missing Tron pieces
        for piece in TRON_PIECES:
            if piece not in bf_names:
                for l in lands:
                    if l.name == piece:
                        gs.play_land(l); return
        # Then Temple/Labyrinth for extra mana
        def score(c):
            n = c.name.lower()
            if 'temple' in n: return 0
            if 'labyrinth' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            if c.has(Tag.CREATURE): attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        # Block with TKS (4/4 is a good blocker)
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and safe_power(c) >= 4]
        if blockers:
            biggest_att = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest_att) >= 3:
                assignments[id(biggest_att)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass
