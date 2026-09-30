"""
apl/dimir_midrange_modern_match.py -- Dimir Midrange (Modern) match pilot.

Replaces the Izzet Murktide proxy (2026-09-30, spec harness/specs/2026-09-30-proxy-pilots.md).
List: decks/dimir_midrange_modern.txt (real medoid list, Frog / Bowmasters / Tamiyo build).

Game plan (tempo-midrange):
  - T1-2 Thoughtseize the best nonland card (2 life).
  - Cheap threats: Tamiyo, Psychic Frog; Orcish Bowmasters held for the opponent's end
    step (flash); Kaito, Quantum Riddler, Murktide Regent as the top end.
  - Removal on the biggest threat: Fatal Push (MV <= 2), Drown in the Loch (MV <= the
    opponent's graveyard), Sheoldred's Edict (they sacrifice their weakest creature, or
    a planeswalker), Sink into Stupor (bounce).
  - Counters only on the stack (R1 window): Counterspell, Spell Snare, Force of Negation,
    Subtlety, Drown in the Loch (counter mode approximated as MV <= 3: the validity check
    cannot see the graveyard).
"""
from __future__ import annotations

from data.card import Tag
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.deck_pilot import DeckPilotMixin, opp_creatures, opp_nonland_permanents, threat_score

THOUGHTSEIZE = "Thoughtseize"
TAMIYO = "Tamiyo, Inquisitive Student"
FROG = "Psychic Frog"
BOWMASTERS = "Orcish Bowmasters"
KAITO = "Kaito, Bane of Nightmares"
RIDDLER = "Quantum Riddler"
MURKTIDE = "Murktide Regent"
PREORDAIN = "Preordain"
PUSH = "Fatal Push"
DROWN = "Drown in the Loch"
EDICT = "Sheoldred's Edict"
STUPOR = "Sink into Stupor"
CLING = "Cling to Dust"
COUNTERSPELL = "Counterspell"
SNARE = "Spell Snare"
FON = "Force of Negation"
SUBTLETY = "Subtlety"

COUNTERS = {COUNTERSPELL, SNARE, FON, SUBTLETY, DROWN}
REACTIVE = {BOWMASTERS, STUPOR, CLING, PUSH, EDICT, THOUGHTSEIZE} | COUNTERS


class DimirMidrangeModernMatchAPL(DeckPilotMixin, AwareMatchAPL):
    name = "Dimir Midrange"
    ARCHETYPE = "midrange"
    WANTS_PRIORITY_STACK = True
    WANTS_BURN = True
    COUNTER_CARDS = COUNTERS
    COUNTER_COST = 2
    EXTRA_COUNTER_VALIDITY = {DROWN: (lambda s: (getattr(s, "cmc", 0) or 0) <= 3, 2)}
    MATCH_REMOVAL = {}
    win_condition_damage = 20
    max_turns = 15

    # ------------------------------------------------------------ mulligans
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 5:
            return True
        lands = sum(1 for c in hand if c.is_land())
        cheap = sum(1 for c in hand if not c.is_land() and c.cmc <= 2)
        if len(hand) == 7:
            return 2 <= lands <= 4 and cheap >= 2
        return 1 <= lands <= 4 and cheap >= 1

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        spells = sorted((c for c in hand if not c.is_land()), key=lambda c: -c.cmc)
        excess = lands[3:] if len(lands) > 3 else []
        return (excess + spells + lands)[:n]

    def reserve_mana(self, gs, opponent):
        names = {c.name for c in gs.zones.hand}
        if names & {COUNTERSPELL, DROWN, FON} and self._land_count(gs) >= 3:
            gs.mana_reserve = 2
        elif SNARE in names and self._land_count(gs) >= 2:
            gs.mana_reserve = 1
        else:
            gs.mana_reserve = 0

    # ------------------------------------------------------------ main phase
    def main_phase(self, gs):
        self.main_phase_match(gs, getattr(gs, "_match_opp", None))

    def main_phase_match(self, gs, opponent):
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land(gs)
        self.reserve_mana(gs, opponent)
        gs.tap_lands()
        if opponent is not None:
            if gs.turn <= 3:
                self._thoughtseize(gs, opponent)
            self._remove_threat(gs, opponent)
        self._cast_in_order(gs, [TAMIYO, FROG, KAITO, RIDDLER, MURKTIDE], once=False)
        self._cast_in_order(gs, [PREORDAIN], once=True)

    def main_phase2(self, gs):
        return None      # hold counter / flash mana

    def _thoughtseize(self, gs, opponent):
        card = self._in_hand(gs, THOUGHTSEIZE)
        pick = max((c for c in opponent.zones.hand if not c.is_land()), key=lambda c: c.cmc, default=None)
        if card and pick and self._resolve_manual(gs, card, note=f"-> takes {pick.name}"):
            opponent.zones.hand.remove(pick)
            opponent.zones.graveyard.append(pick)
            gs.life -= 2

    def _remove_threat(self, gs, opponent) -> bool:
        for t in sorted(opp_nonland_permanents(opponent), key=threat_score, reverse=True):
            if not (t.has(Tag.PLANESWALKER) or safe_power(t) >= 2 or (t.cmc or 0) >= 3):
                continue
            creature = t.has(Tag.CREATURE)
            if creature and (t.cmc or 0) <= 2:
                p = self._in_hand(gs, PUSH)
                if p and self._resolve_manual(gs, p, note=f"-> {t.name}"):
                    self._remove(opponent, t)
                    return True
            if creature and (t.cmc or 0) <= len(opponent.zones.graveyard):
                d = self._in_hand(gs, DROWN)
                if d and self._resolve_manual(gs, d, note=f"-> {t.name} (destroy mode)"):
                    self._remove(opponent, t)
                    return True
            e = self._in_hand(gs, EDICT)
            if e:
                foes = opp_creatures(opponent)
                if foes and len(foes) <= 2:
                    victim = min(foes, key=threat_score)      # they choose: weakest
                    if self._resolve_manual(gs, e, note=f"-> they sacrifice {victim.name}"):
                        self._remove(opponent, victim)
                        return True
                elif not foes and t.has(Tag.PLANESWALKER) and self._resolve_manual(gs, e, note=f"-> {t.name}"):
                    self._remove(opponent, t)
                    return True
        return False

    # ------------------------------------------------------------ instant speed
    def pre_combat_instant(self, gs, opponent):
        return None

    def post_attackers_instant(self, gs, opponent, attackers=None, *a, **k):
        return None

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        """Opponent's end step: bounce/remove a threat, flash Bowmasters, Cling to Dust."""
        if opponent is None:
            return
        if not self._remove_threat(gs, opponent):
            best = max(opp_nonland_permanents(opponent), key=threat_score, default=None)
            s = self._in_hand(gs, STUPOR)
            if best is not None and threat_score(best) >= 6 and s and self._resolve_manual(gs, s, note=f"-> bounce {best.name}"):
                opponent.zones.battlefield.remove(best)
                opponent.zones.hand.append(best)
        self._cast_in_order(gs, [BOWMASTERS], once=True)
        cling = self._in_hand(gs, CLING)
        if cling and opponent.zones.graveyard and self._resolve_manual(gs, cling, note="(end step)"):
            victim = max(opponent.zones.graveyard, key=lambda c: c.cmc)
            opponent.zones.graveyard.remove(victim)
            opponent.zones.exile.append(victim)
            if victim.has(Tag.CREATURE):
                gs.life += 3
            else:
                gs.zones.draw(1)
