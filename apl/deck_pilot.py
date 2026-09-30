"""
apl/deck_pilot.py -- shared helpers for deck-specific match pilots (2026-09-30).

Spec harness/specs/2026-09-30-proxy-pilots.md. Used by the pilots that replaced the
proxy match APLs (Four-Color Control, Dimir Midrange Modern, Boros Dragons):
  - every manual spell (removal with an explicit target, discard, drain) goes through
    `_resolve_manual`, which pays, moves the card and logs "Cast: <name>" like
    GameState.cast_spell, so instrumentation counts it;
  - `_cast_in_order` casts named cards through gs.cast_spell (handlers + the R1
    priority window) and never casts a counterspell proactively (Codex #4);
  - no per-game state is kept on the pilot instance (instances are reused across
    games, Codex A9); per-game flags live on `gs`.
Life changes use `.life` directly: engine.match_engine ends games on life, and a
bare `damage_dealt` increment never reaches the opponent there (Codex A3).
"""
from __future__ import annotations

from data.card import Tag
from engine.match_state import safe_power, safe_toughness


def opp_creatures(opponent):
    if opponent is None:
        return []
    return [c for c in opponent.zones.battlefield if c.has(Tag.CREATURE) and not c.is_land()]


def opp_nonland_permanents(opponent):
    if opponent is None:
        return []
    return [c for c in opponent.zones.battlefield if not c.is_land()]


def threat_score(c) -> float:
    """Bigger = answer first. Power dominates; planeswalkers and engines rank high."""
    s = safe_power(c) * 2 + safe_toughness(c) * 0.5 + (getattr(c, "cmc", 0) or 0) * 0.3
    if c.has(Tag.PLANESWALKER):
        s += 6
    return s


class DeckPilotMixin:
    COUNTER_CARDS: set = set()

    # ------------------------------------------------------------ casting
    def _castable(self, gs, card) -> bool:
        return gs.mana_pool.can_cast(card.mana_cost, card.cmc)

    def _in_hand(self, gs, name):
        return next((c for c in gs.zones.hand if c.name == name), None)

    def _resolve_manual(self, gs, card, dest: str = "graveyard", note: str = "") -> bool:
        """Pay for `card`, move it hand -> dest, log a uniform Cast line."""
        if card not in gs.zones.hand or not self._castable(gs, card):
            return False
        gs.mana_pool.pay(card.mana_cost, card.cmc)
        gs.zones.hand.remove(card)
        getattr(gs.zones, dest).append(card)
        if not card.has(Tag.CREATURE):
            gs.noncreature_spells_this_turn += 1
        gs.spells_cast_this_turn = getattr(gs, "spells_cast_this_turn", 0) + 1
        gs._log(f"  Cast: {card.name} (CMC {card.cmc:.0f}, manual){' ' + note if note else ''}")
        return True

    def _face(self, gs, opponent, n: int):
        """Direct damage / life loss to the opponent that lands on BOTH engines:
        match_engine reads `.life`; match_runner syncs main-phase `damage_dealt` for
        WANTS_BURN pilots (views are rebuilt per phase, so no double count)."""
        if n <= 0 or opponent is None:
            return
        opponent.life -= n
        gs.damage_dealt += n

    def main_phase2(self, gs):
        """match_runner's post-combat hook: leftovers, never counters (BaseAPL's
        default casts everything castable, counters included)."""
        self._cast_rest_noncounter(gs)

    def _remove(self, opponent, target, exile: bool = False):
        if target in opponent.zones.battlefield:
            opponent.zones.battlefield.remove(target)
            (opponent.zones.exile if exile else opponent.zones.graveyard).append(target)

    def _cast_in_order(self, gs, names, once: bool = False) -> int:
        """Cast named cards via gs.cast_spell in priority order; never counters."""
        n = 0
        for name in names:
            if name in self.COUNTER_CARDS:
                continue
            while True:
                card = next((c for c in gs.zones.hand
                             if c.name == name and self._castable(gs, c)), None)
                if card is None:
                    break
                if not gs.cast_spell(card):
                    break
                n += 1
                if once:
                    break
        return n

    def _cast_rest_noncounter(self, gs, skip: set = frozenset()):
        """Cheapest-first leftovers, excluding counters and anything in `skip`."""
        while True:
            cands = sorted((c for c in gs.zones.hand
                            if not c.is_land() and c.name not in self.COUNTER_CARDS
                            and c.name not in skip and self._castable(gs, c)),
                           key=lambda c: c.cmc)
            if not cands or not gs.cast_spell(cands[0]):
                break

    # ------------------------------------------------------------ lands
    def _play_land(self, gs, prefer=()):
        if gs.land_played:
            return
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands:
            return
        for name in prefer:
            for c in lands:
                if c.name == name:
                    gs.play_land(c)
                    return
        gs.play_land(lands[0])

    @staticmethod
    def _land_count(gs) -> int:
        return len(gs.zones.lands_on_battlefield())
