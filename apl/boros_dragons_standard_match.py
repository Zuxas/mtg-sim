"""
apl/boros_dragons_standard_match.py -- Boros Dragons (Standard) match pilot.

Replaces the Azorius Momo proxy (2026-09-30, spec harness/specs/2026-09-30-proxy-pilots.md),
which never cast a Dragon (its deployment logic only knew the Momo deck's cards).
List: decks/boros_dragons_standard.txt.

Game plan (Dragon aggro-midrange, no counters):
  - Curve: Momo (1) -> Sarkhan / Voice of Victory (2) -> Clarion Conqueror (3) ->
    Magmatic Hellkite (4) -> Nova Hellkite / Dragonhawk / Lorehold (5) -> Twinmaw (6).
    Each turn the biggest castable threat goes first, then cheaper ones fill the mana.
  - Removal: Burst Lightning (2, kicked 4) on a blocker it kills, Get Lost on the biggest
    threat, Spectacular Tactics on a power >= 4 creature. Burst goes face when lethal.
"""
from __future__ import annotations

from data.card import Tag
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.deck_pilot import DeckPilotMixin, opp_creatures, opp_nonland_permanents, threat_score

MOMO = "Momo, Friendly Flier"
SARKHAN = "Sarkhan, Dragon Ascendant"
VOICE = "Voice of Victory"
CLARION = "Clarion Conqueror"
MAGMATIC = "Magmatic Hellkite"
NOVA = "Nova Hellkite"
DRAGONHAWK = "Dragonhawk, Fate's Tempest"
LOREHOLD = "Lorehold, the Historian"
TWINMAW = "Twinmaw Stormbrood"
BURST = "Burst Lightning"
GET_LOST = "Get Lost"
TACTICS = "Spectacular Tactics"

THREATS_TOP_DOWN = [TWINMAW, LOREHOLD, DRAGONHAWK, NOVA, MAGMATIC, CLARION, SARKHAN, VOICE, MOMO]


class BorosDragonsStandardMatchAPL(DeckPilotMixin, AwareMatchAPL):
    name = "Boros Dragons"
    ARCHETYPE = "aggro"
    WANTS_BURN = True
    MATCH_REMOVAL = {}
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 5:
            return True
        lands = sum(1 for c in hand if c.is_land())
        early = sum(1 for c in hand if not c.is_land() and c.cmc <= 3)
        if len(hand) == 7:
            return 2 <= lands <= 4 and early >= 1
        return 2 <= lands <= 5

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        spells = sorted((c for c in hand if not c.is_land()), key=lambda c: -c.cmc)
        excess = lands[4:] if len(lands) > 4 else []
        return (excess + spells + lands)[:n]

    def reserve_mana(self, gs, opponent):
        gs.mana_reserve = 0

    def main_phase(self, gs):
        self.main_phase_match(gs, getattr(gs, "_match_opp", None))

    def main_phase_match(self, gs, opponent):
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land(gs)
        gs.tap_lands()
        if opponent is not None:
            self._removal_pass(gs, opponent)
        for name in THREATS_TOP_DOWN:          # biggest first, cheaper ones fill the rest
            self._cast_in_order(gs, [name], once=False)
        if opponent is not None:
            self._burn_face_if_lethal(gs, opponent)

    # ------------------------------------------------------------ removal
    def _burst(self, gs, opponent, target) -> bool:
        card = self._in_hand(gs, BURST)
        if card is None:
            return False
        kicked = gs.mana_pool.can_cast("{4}{R}", 5)
        dmg = 4 if kicked else 2
        if target is not None and safe_toughness(target) > dmg:
            return False
        cost, cmc = ("{4}{R}", 5) if (kicked and (target is None or safe_toughness(target) > 2)) else ("{R}", 1)
        if not gs.mana_pool.can_cast(cost, cmc):
            return False
        gs.mana_pool.pay(cost, cmc)
        gs.zones.hand.remove(card)
        gs.zones.graveyard.append(card)
        gs.noncreature_spells_this_turn += 1
        dealt = 4 if cmc == 5 else 2
        gs._log(f"  Cast: {BURST} (CMC {cmc}, manual) {dealt} -> {target.name if target else 'face'}")
        if target is not None:
            self._remove(opponent, target)
        else:
            self._face(gs, opponent, dealt)
        return True

    def _removal_pass(self, gs, opponent):
        """Main-phase removal: Tactics on power >= 4, Get Lost on power >= 3 / PW, Burst."""
        foes = sorted(opp_creatures(opponent), key=threat_score, reverse=True)
        for t in foes:
            if safe_power(t) >= 4:
                tac = self._in_hand(gs, TACTICS)
                if tac and self._resolve_manual(gs, tac, note=f"-> {t.name}"):
                    self._remove(opponent, t)
                    continue
            if safe_power(t) >= 3 or t.has(Tag.PLANESWALKER):
                g = self._in_hand(gs, GET_LOST)
                if g and self._resolve_manual(gs, g, note=f"-> {t.name}"):
                    self._remove(opponent, t)
                    continue
            if safe_power(t) >= 1 and self._burst(gs, opponent, t):
                continue
        for pw in [p for p in opp_nonland_permanents(opponent) if p.has(Tag.PLANESWALKER)]:
            g = self._in_hand(gs, GET_LOST)
            if g and self._resolve_manual(gs, g, note=f"-> {pw.name}"):
                self._remove(opponent, pw)

    def _burn_face_if_lethal(self, gs, opponent):
        bursts = [c for c in gs.zones.hand if c.name == BURST]
        if not bursts:
            return
        possible = sum(4 if gs.mana_pool.total() >= 5 else 2 for _ in bursts)
        if opponent.life <= possible:
            while self._in_hand(gs, BURST) and opponent.life > 0 and self._burst(gs, opponent, None):
                pass

    def pre_combat_instant(self, gs, opponent):
        return None

    def post_attackers_instant(self, gs, opponent, attackers=None, *a, **k):
        return None

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        if opponent is not None:
            self._burn_face_if_lethal(gs, opponent)
