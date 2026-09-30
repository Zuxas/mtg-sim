"""
apl/four_color_control_standard_match.py -- Four-Color Control (Standard) match pilot.

Replaces the Jeskai Control proxy (2026-09-30, spec harness/specs/2026-09-30-proxy-pilots.md).
List: decks/four_color_control_standard.txt (W/U/B/R Lute control).

Game plan (draw-go control):
  - Counters only on the stack (R1 priority window): No More Lies (any spell; the
    "unless they pay {3}" clause is approximated as a hard counter), Negate
    (noncreature), Spell Snare (MV 2). Never cast from the main phase.
  - Sweepers vs a developed board: Day of Judgment, Fire Magic (tiered 1/2/3 damage),
    Pest Control (MV <= 1 permanents; otherwise cycled), Ill-Timed Explosion.
  - Spot removal on the biggest threat: Get Lost, Inevitable Defeat (also a 3-point
    drain finisher), Lightning Helix, Traumatic Critique (X damage).
  - Card flow: Stock Up, Consult the Star Charts (opponent's end step), Resonating
    Lute, Flashback on a spent spell, Jeskai Revelation as the top end.
"""
from __future__ import annotations

from data.card import Tag
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.deck_pilot import DeckPilotMixin, opp_creatures, opp_nonland_permanents, threat_score

NO_MORE_LIES = "No More Lies"
NEGATE = "Negate"
SPELL_SNARE = "Spell Snare"
DAY_OF_JUDGMENT = "Day of Judgment"
FIRE_MAGIC = "Fire Magic"
PEST_CONTROL = "Pest Control"
ILL_TIMED = "Ill-Timed Explosion"
GET_LOST = "Get Lost"
INEVITABLE = "Inevitable Defeat"
HELIX = "Lightning Helix"
CRITIQUE = "Traumatic Critique"
STOCK_UP = "Stock Up"
CONSULT = "Consult the Star Charts"
LUTE = "Resonating Lute"
FLASHBACK = "Flashback"
REVELATION = "Jeskai Revelation"

COUNTERS = {NO_MORE_LIES, NEGATE, SPELL_SNARE}


class FourColorControlStandardMatchAPL(DeckPilotMixin, AwareMatchAPL):
    name = "Four-Color Control"
    ARCHETYPE = "control"
    WANTS_PRIORITY_STACK = True
    COUNTER_CARDS = COUNTERS
    COUNTER_COST = 2
    EXTRA_COUNTER_VALIDITY = {NO_MORE_LIES: (lambda s: True, 2)}
    MATCH_REMOVAL = {}            # removal is handled explicitly below
    WANTS_BURN = True             # face damage/drain synced on match_runner too
    win_condition_damage = 20
    max_turns = 15

    # ------------------------------------------------------------ mulligans
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 5:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if len(hand) == 7:
            return 3 <= lands <= 5 or (lands == 2 and any(c.name in (CONSULT, STOCK_UP) for c in hand))
        return 2 <= lands <= 5

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        spells = sorted((c for c in hand if not c.is_land()), key=lambda c: -c.cmc)
        excess = lands[4:] if len(lands) > 4 else []
        return (excess + spells + lands)[:n]

    # ------------------------------------------------------------ mana
    def reserve_mana(self, gs, opponent):
        has_counter = any(c.name in COUNTERS for c in gs.zones.hand)
        gs.mana_reserve = 2 if has_counter and self._land_count(gs) >= 3 else 0

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
            if not self._sweep(gs, opponent):
                self._spot_remove(gs, opponent)
            self._finish_with_defeat(gs, opponent)

        # Card flow + top end (all through cast_spell: handlers + priority window).
        if self._land_count(gs) >= 4:
            self._cast_in_order(gs, [LUTE], once=True)
        self._cast_in_order(gs, [REVELATION, STOCK_UP, ILL_TIMED], once=True)
        self._flashback(gs)
        self._cycle_pest_control(gs, opponent)

    # ------------------------------------------------------------ removal
    def _sweep(self, gs, opponent) -> bool:
        foes = opp_creatures(opponent)
        mine = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)]
        power = sum(safe_power(c) for c in foes)
        if len(foes) >= 3 or (len(foes) >= 2 and power >= 5) or power >= max(6, gs.life // 2):
            dj = self._in_hand(gs, DAY_OF_JUDGMENT)
            if dj and len(mine) < len(foes) and self._resolve_manual(gs, dj, note="(sweep)"):
                for c in foes:
                    self._remove(opponent, c)
                for c in mine:
                    if c in gs.zones.battlefield:
                        gs.zones.battlefield.remove(c)
                        gs.zones.graveyard.append(c)
                return True
        fm = self._in_hand(gs, FIRE_MAGIC)
        if fm and foes:
            avail = gs.mana_pool.total()
            for dmg, extra in ((3, 5), (2, 2), (1, 0)):
                if avail < 1 + extra:
                    continue
                killed = [c for c in foes if safe_toughness(c) <= dmg]
                top = max(foes, key=threat_score)
                if len(killed) >= 2 or (top in killed and safe_power(top) >= 3):
                    cost = "{%d}{R}" % extra if extra else "{R}"
                    if gs.mana_pool.can_cast(cost, 1 + extra):
                        gs.mana_pool.pay(cost, 1 + extra)
                        gs.zones.hand.remove(fm)
                        gs.zones.graveyard.append(fm)
                        gs.noncreature_spells_this_turn += 1
                        gs._log(f"  Cast: {FIRE_MAGIC} (CMC {1 + extra}, manual) tier {dmg}")
                        for c in killed:
                            self._remove(opponent, c)
                        for c in [c for c in gs.zones.battlefield if c.has(Tag.CREATURE) and safe_toughness(c) <= dmg]:
                            gs.zones.battlefield.remove(c)
                            gs.zones.graveyard.append(c)
                        return True
                    break
        pc = self._in_hand(gs, PEST_CONTROL)
        small = [c for c in opp_nonland_permanents(opponent) if (c.cmc or 0) <= 1]
        if pc and len(small) >= 2 and self._resolve_manual(gs, pc, note="(MV<=1 sweep)"):
            for c in small:
                self._remove(opponent, c)
            return True
        return False

    def _spot_remove(self, gs, opponent) -> bool:
        targets = sorted(opp_nonland_permanents(opponent), key=threat_score, reverse=True)
        for t in targets:
            if not (t.has(Tag.PLANESWALKER) or safe_power(t) >= 2):
                continue
            is_creature = t.has(Tag.CREATURE)
            # Cheapest adequate answer first.
            if is_creature and safe_toughness(t) <= 3:
                h = self._in_hand(gs, HELIX)
                if h and self._resolve_manual(gs, h, note=f"-> {t.name}"):
                    self._remove(opponent, t)
                    gs.life += 3
                    return True
            if is_creature or t.has(Tag.PLANESWALKER) or t.has(Tag.ENCHANTMENT):
                g = self._in_hand(gs, GET_LOST)
                if g and self._resolve_manual(gs, g, note=f"-> {t.name}"):
                    self._remove(opponent, t)
                    return True
            d = self._in_hand(gs, INEVITABLE)
            if d and self._resolve_manual(gs, d, note=f"-> {t.name}"):
                self._remove(opponent, t, exile=True)
                self._face(gs, opponent, 3)
                gs.life += 3
                return True
            if is_creature and self._critique(gs, opponent, t):
                return True
        return False

    def _critique(self, gs, opponent, target=None) -> bool:
        card = self._in_hand(gs, CRITIQUE)
        if card is None:
            return False
        x = gs.mana_pool.total() - 2
        need = safe_toughness(target) if target is not None else 1
        if x < max(1, need):
            return False
        cost = "{%d}{U}{R}" % x
        if not gs.mana_pool.can_cast(cost, x + 2):
            return False
        gs.mana_pool.pay(cost, x + 2)
        gs.zones.hand.remove(card)
        gs.zones.graveyard.append(card)
        gs.noncreature_spells_this_turn += 1
        gs._log(f"  Cast: {CRITIQUE} (CMC {x + 2}, manual) X={x} -> {target.name if target else 'face'}")
        if target is not None:
            self._remove(opponent, target)
        else:
            self._face(gs, opponent, x)
        gs.zones.draw(2)
        spare = sorted(gs.zones.hand, key=lambda c: (not c.is_land(), -c.cmc))
        if spare:
            gs.zones.hand.remove(spare[0])
            gs.zones.graveyard.append(spare[0])
        return True

    def _finish_with_defeat(self, gs, opponent):
        """Inevitable Defeat drains 3: fire it at any permanent when that is lethal."""
        if opponent.life > 3:
            return
        perms = opp_nonland_permanents(opponent)
        d = self._in_hand(gs, INEVITABLE)
        if d and perms and self._resolve_manual(gs, d, note="(lethal drain)"):
            self._remove(opponent, max(perms, key=threat_score), exile=True)
            self._face(gs, opponent, 3)
            gs.life += 3

    # ------------------------------------------------------------ card flow
    def _flashback(self, gs):
        fb = self._in_hand(gs, FLASHBACK)
        if fb is None:
            return
        spent = [c for c in gs.zones.graveyard
                 if (c.has(Tag.INSTANT) or c.has(Tag.SORCERY)) and c.name not in COUNTERS
                 and c.name != FLASHBACK and c.name in (STOCK_UP, REVELATION, CONSULT, ILL_TIMED)]
        if not spent:
            return
        best = max(spent, key=lambda c: c.cmc)
        if gs.mana_pool.total() >= 1 + int(best.cmc) and self._resolve_manual(gs, fb, note=f"-> {best.name}"):
            if gs.mana_pool.can_cast(best.mana_cost, best.cmc):
                gs.zones.graveyard.remove(best)
                gs.zones.hand.append(best)
                if gs.cast_spell(best) and best in gs.zones.graveyard:
                    gs.zones.graveyard.remove(best)
                    gs.zones.exile.append(best)

    def _cycle_pest_control(self, gs, opponent):
        pc = self._in_hand(gs, PEST_CONTROL)
        small = [c for c in opp_nonland_permanents(opponent) if (c.cmc or 0) <= 1] if opponent else []
        if pc and len(small) < 2 and gs.mana_pool.can_cast("{2}", 2):
            gs.mana_pool.pay("{2}", 2)
            gs.zones.hand.remove(pc)
            gs.zones.graveyard.append(pc)
            gs.zones.draw(1)
            gs._log(f"  Cast: {PEST_CONTROL} (cycling)")

    def main_phase2(self, gs):
        return None      # draw-go: keep mana up for counters after combat

    # ------------------------------------------------------------ instant speed
    def pre_combat_instant(self, gs, opponent):
        return None

    def post_attackers_instant(self, gs, opponent, attackers=None, *a, **k):
        return None

    def respond_to_spell(self, gs, opponent, spell):
        return None      # counters go through priority_action; no blind casts

    def end_step_actions(self, gs, opponent):
        """Opponent's end step: remove a threat that landed, then dig."""
        if opponent is not None:
            self._spot_remove(gs, opponent)
        self._cast_in_order(gs, [CONSULT], once=True)
        if opponent is not None and gs.mana_pool.total() >= 5:
            self._critique(gs, opponent, None)
