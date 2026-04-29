"""
apl/jeskai_control_match.py — Jeskai Control APL (Modern)

Playbook engines:
A. Teferi Lock — opponents sorcery-speed only; -3 bounce best threat + draw
B. Narset Suppression — prevent opponent drawing extra cards
C. Orim's Chant — prevent attacks (declare_blockers) or cast triggers
D. Supreme Verdict — unconditional board wipe at 4 mana
E. Solitude — free evoke exile (pitch white card); white-pitch filter

Key matchup behaviors:
- vs Aggro: sweep T4+, Solitude key threats, Orim's Chant to buy time
- vs Combo: counter cascade / Goryo's / Living End in respond_to_spell
- vs Midrange: Teferi lock + Narset anti-draw + targeted removal
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TEFERI      = "Teferi, Time Raveler"
NARSET      = "Narset, Parter of Veils"
SOLITUDE    = "Solitude"
VERDICT     = "Supreme Verdict"
ORIM        = "Orim's Chant"
FON         = "Force of Negation"
COUNTER     = "Counterspell"
PRISMATIC   = "Prismatic Ending"
FLAME_OF_ANOR = "Flame of Anor"
WRATHS      = {VERDICT}
COUNTERSPELLS = {FON, COUNTER}
REMOVAL     = {PRISMATIC, FLAME_OF_ANOR}

# High-value combo targets to counter
COMBO_TARGETS = {
    "Primeval Titan", "Goryo's Vengeance", "Griselbrand",
    "Living End", "Violent Outburst", "Ardent Plea",
    "Neoform", "Summoner's Pact", "Goblin Charbelcher",
    "Archon of Cruelty",
}


class JeskaiControlMatchAPL(MatchAPL):
    name = "Jeskai Control"
    win_condition_damage = 20
    max_turns = 16

    def __init__(self):
        self._orim_chanted = False  # Orim's Chant used this turn

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        has_pw = any(c.name in {TEFERI, NARSET} for c in hand)
        has_interaction = any(c.name in COUNTERSPELLS | {SOLITUDE, ORIM, FON} for c in hand)
        if lands == 0:
            return False
        if lands >= 3 and (has_pw or has_interaction):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess_lands[4:]  # keep up to 4 lands
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._orim_chanted = False

        opp_creatures = ([c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE)]
                         if opponent else [])
        opp_nonlands = ([c for c in opponent.zones.battlefield if not c.is_land()]
                        if opponent else [])

        # 1. Supreme Verdict — sweep when opp has 2+ creatures (T4+)
        if opponent and len(opp_creatures) >= 2 and gs.turn >= 4:
            for c in list(gs.zones.hand):
                if c.name == VERDICT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    for cr in list(opp_creatures):
                        if cr in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(cr)
                            opponent.zones.graveyard.append(cr)
                    gs._log(f"  Supreme Verdict: wiped {len(opp_creatures)} creatures")
                    break

        # 2. Solitude EVOKE — free exile of biggest threat (pitch white card)
        if opponent and opp_creatures:
            biggest = max(opp_creatures, key=lambda c: safe_power(c))
            for c in list(gs.zones.hand):
                if c.name == SOLITUDE:
                    # Evoke: exile a white card from hand
                    white_cards = [x for x in gs.zones.hand if x != c and not x.is_land()
                                   and 'W' in (getattr(x, 'colors', []) or [])]
                    if white_cards:
                        pitch = white_cards[0]
                        gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        if biggest in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(biggest)
                            opponent.zones.exile.append(biggest)
                        opponent.life += safe_power(biggest)  # lifelink
                        gs._log(f"  Solitude evoke: exile {biggest.name} (pitched {pitch.name})")
                        break

        # 3. Targeted removal
        if opponent and opp_creatures:
            target = max(opp_creatures, key=lambda c: safe_power(c))
            for c in list(gs.zones.hand):
                if c.name in REMOVAL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  {c.name}: remove {target.name}")
                    break

        # 4. Teferi — lock + -3 bounce best threat or draw
        for c in list(gs.zones.hand):
            if c.name == TEFERI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent and opp_nonlands:
                    bounce = max(opp_nonlands, key=lambda x: safe_power(x))
                    opponent.zones.battlefield.remove(bounce)
                    opponent.zones.hand.append(bounce)
                    gs._log(f"  Teferi -3: bounce {bounce.name}")
                self._draw(gs, 1)
                break

        # 5. Narset — reduces opponent card draw
        for c in list(gs.zones.hand):
            if c.name == NARSET and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Narset: opponent limited to 1 card draw per turn")
                break

        # 6. Fill curve
        self._cast_all_castable(gs)

    def declare_attackers(self, gs, opponent):
        # Control deck attacks with planeswalkers on battlefield (Teferi/Narset)
        # Simplified: attack with any creature we have
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        """Block key threats; use Orim's Chant to prevent attacks if available."""
        if not attackers:
            return {}
        # Orim's Chant: prevent all combat damage from one attacker
        for c in list(gs.zones.hand):
            if c.name == ORIM and gs.mana_pool.total() >= 1:
                biggest = max(attackers, key=lambda a: safe_power(a))
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs._log(f"  Orim's Chant: prevent {biggest.name} from attacking")
                attackers = [a for a in attackers if a is not biggest]
                if not attackers:
                    return {}
                break

        # Assign best blocker to each attacker
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)]
        if not blockers:
            return {}
        assignments = {}
        for atk, blk in zip(
            sorted(attackers, key=lambda c: -safe_power(c)),
            sorted(blockers, key=lambda c: -safe_toughness(c))
        ):
            assignments[id(atk)] = [blk]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Counter combo pieces and high-value threats."""
        if not spell or not opponent:
            return None
        spell_cmc = getattr(spell, 'cmc', 0)
        is_target = (spell.name in COMBO_TARGETS or spell_cmc >= 4)
        if not is_target:
            return None
        # Force of Negation (free on opponent's turn if no mana)
        if gs.mana_pool.total() < 2:
            for c in list(gs.zones.hand):
                if c.name == FON:
                    # Exile a blue card to pay alternative cost
                    blue_cards = [x for x in gs.zones.hand if x != c and not x.is_land()
                                  and 'U' in (getattr(x, 'colors', []) or [])]
                    if blue_cards:
                        pitch = blue_cards[0]
                        gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                        gs.zones.hand.remove(c); gs.zones.exile.append(c)
                        gs._log(f"  Force of Negation: counter {spell.name} (free, pitched {pitch.name})")
                        return c
        # Counterspell / Force with mana
        for c in list(gs.zones.hand):
            if c.name in COUNTERSPELLS and gs.mana_pool.total() >= 2:
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs._log(f"  {c.name}: counter {spell.name}")
                return c
        return None

    def end_step_actions(self, gs, opponent): pass
