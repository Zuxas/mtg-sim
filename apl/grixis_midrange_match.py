"""
apl/grixis_midrange_match.py -- Grixis Midrange match APL (Modern, UBR tempo-midrange)

Closes IMPERFECTIONS no-apl-grixis_midrange.

Archetype: UBR midrange/tempo built around Ragavan + cheap threats (Dragon's
Rage Channeler, Ledger Shredder), efficient removal (Lightning Bolt, Unholy
Heat), counter suite (Counterspell, Spell Snare, Spell Pierce, Stern Scolding),
cantrips (Preordain, Consider/Bauble, Expressive Iteration), and a Murktide
Regent delve finisher.

Game plan (mirrors murktide_match.py but ported onto AwareMatchAPL so we inherit
the field-aware combat / trade / mana-holdback machinery):
  1. Land a cheap threat early (Ragavan T1, DRC T1-T2, Ledger Shredder T2).
  2. Trade removal 1-for-1 with the opponent's best creature; bolt face only
     when racing.
  3. Hold up counter mana on later turns instead of tapping out -- deploy via
     respond_to_spell / reserved lands.
  4. Cantrip to fill the graveyard for Murktide delve and delirium.
  5. Murktide Regent closes as an evasive delve finisher.

NOTE ON THE DECK: no literal "grixis_midrange" decklist exists in decks/. The
closest existing, faithfully-matching list is decks/dimir_murktide_modern.txt
(Ragavan + Murktide + Bolt/Unholy Heat + counters). It is technically UR
(Izzet) rather than true UBR Grixis -- it has no black cards -- and is tempo
more than midrange, but it is the exact card pool the archetype description
names. Constants below are wired to the REAL cards in that list so the pilot
logic actually fires.
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

# ---- Card name constants (exact oracle names, present in the deck) ----------
RAGAVAN      = "Ragavan, Nimble Pilferer"
DRC          = "Dragon's Rage Channeler"
LEDGER       = "Ledger Shredder"
MURKTIDE     = "Murktide Regent"
TISHANA      = "Tishana's Tidebinder"

BOLT         = "Lightning Bolt"
UNHOLY       = "Unholy Heat"

COUNTERSPELL = "Counterspell"
SPELL_SNARE  = "Spell Snare"
SPELL_PIERCE = "Spell Pierce"
STERN        = "Stern Scolding"

PREORDAIN    = "Preordain"
ITERATION    = "Expressive Iteration"
BAUBLE       = "Mishra's Bauble"
CONSIDER     = "Consider"

THREATS  = {RAGAVAN, DRC, LEDGER, MURKTIDE}
COUNTERS = {COUNTERSPELL, SPELL_SNARE, SPELL_PIERCE, STERN}
REMOVAL  = {BOLT, UNHOLY}
CANTRIPS = {PREORDAIN, ITERATION, BAUBLE, CONSIDER}


class GrixisMidrangeMatchAPL(AwareMatchAPL):
    name = "Grixis Midrange"
    ARCHETYPE = "tempo"

    win_condition_damage = 20
    max_turns = 15

    # Hold up 1 land when we have a cheap counter; capped in reserve_mana below
    # so we never sit on 4 mana doing nothing on a tempo deck.
    COUNTER_COST  = 1
    COUNTER_CARDS = COUNTERS

    # AwareMatchAPL._kill_with_removal reads these. Format: name -> (cost, max_toughness)
    #   Lightning Bolt: 3 damage -> kills toughness <= 3
    #   Unholy Heat: 6 with delirium -> treat as broad (<= 6)
    MATCH_REMOVAL = {
        BOLT:   ("R", 3),
        UNHOLY: ("R", 6),
    }
    MATCH_EXILE  = set()
    MATCH_BOUNCE = set()
    MATCH_WIPES  = set()

    # Per-game Ragavan treasure tracker
    _treasures = 0

    # ---- Mulligan ----------------------------------------------------------
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 4:
            return False
        threats     = sum(1 for c in hand if c.name in THREATS)
        interaction = sum(1 for c in hand if c.name in (COUNTERS | REMOVAL))
        cantrips    = sum(1 for c in hand if c.name in CANTRIPS)
        # Tempo hands want a threat plus something to do, or a cantrip to dig.
        if threats >= 1 and interaction >= 1:
            return True
        if threats >= 1 and cantrips >= 1 and lands >= 2:
            return True
        if lands >= 2 and (threats >= 1 or cantrips >= 1):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[3:] + spells   # keep up to 3 lands, then ditch expensive spells
        return pool[:n]

    # ---- Mana holdback -----------------------------------------------------
    def reserve_mana(self, gs: GameState, opponent: GameState):
        """Hold up cheap counter mana once we have spare lands, but cap the
        reserve at 2 so we keep developing (tempo deck, not draw-go control)."""
        counters = [c for c in gs.zones.hand if c.name in COUNTERS]
        n_lands = sum(1 for c in gs.zones.battlefield
                      if c.is_land() and not getattr(c, 'tapped', False))
        if counters and n_lands >= 3:
            min_cmc = min(int(getattr(c, 'cmc', 1) or 1) for c in counters)
            gs.mana_reserve = min(min_cmc, 2)
        else:
            gs.mana_reserve = 0

    # ---- Main phase --------------------------------------------------------
    def main_phase_match(self, gs: GameState, opponent: GameState):
        if opponent is not None:
            gs._match_opp = opponent
        self._opp_gs = opponent

        # Convert banked Ragavan treasures into flex mana for this turn.
        if self._treasures > 0:
            use = min(self._treasures, 2)
            gs.mana_pool.flex += use
            self._treasures -= use

        self._play_land_if_able(gs)
        gs.tap_lands()   # honors gs.mana_reserve set by reserve_mana()

        # 1. Remove the opponent's best creature (uses inherited removal engine).
        if opponent is not None:
            self._use_removal(gs, opponent)

        # 2. Deploy ONE cheap threat if our board is empty of threats.
        has_threat = any(c.name in THREATS for c in gs.zones.battlefield
                         if not c.is_land())
        if not has_threat:
            for name in (RAGAVAN, DRC, LEDGER):
                if self._cast_by_name(gs, name):
                    has_threat = True
                    break

        # 3. Cantrip to fill the graveyard (Murktide delve + DRC/Unholy delirium).
        self._run_cantrip(gs)

        # 4. Tishana's Tidebinder: flash threat / ability strip; deploy if it
        #    can profitably hit an opposing creature, else as a body.
        self._cast_by_name(gs, TISHANA)

        # 5. Murktide Regent -- delve finisher.
        self._cast_murktide(gs)

        # 6. Deploy any remaining cheap threat we skipped (e.g. second DRC) but
        #    DO NOT dump counters -- reserved lands stay up for respond_to_spell.
        for name in (LEDGER, DRC):
            self._cast_by_name(gs, name)

    def main_phase(self, gs: GameState):
        # Goldfish entry point delegates to the match path with no opponent.
        self.main_phase_match(gs, None)

    # ---- Casting helpers ---------------------------------------------------
    def _cast_by_name(self, gs: GameState, name: str) -> bool:
        for c in list(gs.zones.hand):
            if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                return True
        return False

    def _run_cantrip(self, gs: GameState):
        """Cast one cantrip; Bauble is a free crack-into-draw."""
        for c in list(gs.zones.hand):
            if c.name == BAUBLE:
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.zones.draw(1)
                return
        for c in list(gs.zones.hand):
            if c.name in CANTRIPS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(1)
                return

    def _use_removal(self, gs: GameState, opponent: GameState):
        """Kill the opponent's biggest creature with Unholy Heat / Bolt.

        Uses the inherited AwareMatchAPL._kill_with_removal dispatcher so the
        ward/toughness gating and bookkeeping stay consistent.
        """
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        # Don't spend premium removal on a 1-power dork unless it is all we face.
        if safe_power(target) < 2 and len(opp_creatures) == 1 \
                and safe_toughness(target) > 1:
            return
        self._kill_with_removal(gs, opponent, target, prefer_exile=False)

    def _cast_murktide(self, gs: GameState):
        """Murktide Regent: 3/3 base + a +1/+1 counter per instant/sorcery
        exiled to delve. Effective cost 7 - (cards delved, max 5)."""
        for c in list(gs.zones.hand):
            if c.name != MURKTIDE:
                continue
            gy_size = len(gs.zones.graveyard)
            delve = min(gy_size, 5)
            effective_cost = 7 - delve
            if gs.mana_pool.total() < effective_cost:
                return
            # Pay the reduced cost out of the pool.
            to_pay = effective_cost
            while to_pay > 0 and gs.mana_pool.total() > 0:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                to_pay -= 1
            # Exile delve fuel, counting instants/sorceries for the P/T bonus.
            is_count = 0
            for _ in range(delve):
                if gs.zones.graveyard:
                    exiled = gs.zones.graveyard.pop(0)
                    if exiled.has(Tag.INSTANT) or exiled.has(Tag.SORCERY):
                        is_count += 1
                    gs.zones.exile.append(exiled)
            gs.zones.hand.remove(c)
            gs.zones.battlefield.append(c)
            c.turn_entered = gs.turn
            c.summoning_sickness = True
            c.power = str(3 + is_count)
            c.toughness = str(3 + is_count)
            gs._log(f"  Murktide Regent: {c.power}/{c.toughness} "
                    f"(delved {delve}, {is_count} instant/sorcery)")
            return

    # ---- Reactive interaction ---------------------------------------------
    def respond_to_spell(self, gs: GameState, opponent: GameState, spell):
        """Fire removal on a big threat, otherwise counter with the cheapest
        available counterspell. Affordability checked via can_cast against the
        reserved (untapped) mana the engine taps for responses."""
        if opponent is None:
            return None
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if opp_creatures:
            target = max(opp_creatures, key=lambda c: safe_power(c))
            if safe_power(target) >= 3:
                for c in gs.zones.hand:
                    if c.name in REMOVAL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        if c.name == BOLT and safe_toughness(target) > 3:
                            continue
                        return c
        # Counter -- cheapest first to preserve flexible counters.
        for c in sorted(gs.zones.hand, key=lambda x: getattr(x, 'cmc', 9)):
            if c.name in COUNTERS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                return c
        return None

    # ---- Combat ------------------------------------------------------------
    def declare_attackers(self, gs: GameState, opponent: GameState):
        # Resolve Ragavan's combat-damage trigger (Treasure + exile top card)
        # when it would connect, THEN defer to AwareMatchAPL's lethal/trade math.
        if opponent is not None:
            for c in gs.zones.battlefield:
                if c.is_land() or c.name != RAGAVAN:
                    continue
                if getattr(c, 'summoning_sickness', False) or getattr(c, 'tapped', False):
                    continue
                blockers = [x for x in opponent.zones.battlefield
                            if x.has(Tag.CREATURE) and not x.is_land()
                            and safe_power(x) >= 2 and not getattr(x, 'tapped', False)]
                if not blockers:   # Ragavan (2/1) connects
                    self._treasures += 1
                    if opponent.zones.library:
                        gs.zones.exile.append(opponent.zones.library.pop(0))
                    gs._log("  Ragavan connects: +1 Treasure, exile top card")
        return super().declare_attackers(gs, opponent)

    def declare_blockers(self, gs: GameState, opponent: GameState, attackers):
        # Big Murktide is our best blocker; otherwise inherit the aware logic.
        if not attackers:
            return {}
        murktides = [c for c in gs.zones.battlefield
                     if c.name == MURKTIDE and not getattr(c, 'tapped', False)]
        if murktides:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                return {id(biggest): [murktides[0]]}
        return super().declare_blockers(gs, opponent, attackers)

    # ---- Lands -------------------------------------------------------------
    def _play_land_if_able(self, gs: GameState):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return

        def score(c):
            n = c.name.lower()
            if 'tarn' in n or 'delta' in n or 'strand' in n or 'rainforest' in n:
                return 0   # fetchlands first (fixing + delirium/GY fuel)
            if 'vents' in n or 'canal' in n or 'islet' in n:
                return 1
            return 3

        gs.play_land(min(lands, key=score))
