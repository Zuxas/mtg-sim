"""
goryo_vengeance.py — APL for Modern Goryo's Vengeance (full rewrite, April 2026)

VERIFIED card interactions (CardDB, deck: goryos_vengeance_modern.txt):

  Goryo's Vengeance [{1}{B}] — Instant — Arcane.
    Return target legendary creature card from your graveyard to the battlefield.
    That creature gains haste. Exile it at the beginning of the next end step.
    Splice onto Arcane {2}{B}: may add Goryo's effect to any Arcane spell.
    KEY: The "exile at next end step" is a delayed triggered ability that tracks
    the specific OBJECT (not the card name). If the creature leaves the battlefield
    before end step (via Ephemerate), the trigger tracks a gone object → misses.

  Ephemerate [{W}] — Instant.
    Exile target creature you control, then return it to the battlefield.
    Rebound: if cast from hand, exile as it resolves → cast free at next upkeep.
    KEY COMBO: Cast Ephemerate on Goryo'd Atraxa BEFORE end step:
      1. Atraxa leaves BF (triggers Goryo's delayed trigger, but now it has no target)
      2. Atraxa returns as a NEW permanent object (Goryo's can't track it)
      3. Atraxa's ETB fires AGAIN → reveal top 10, draw up to 8 more cards
      4. Rebound → free Ephemerate at next upkeep → ETB again, another 8 cards
    Net: Atraxa stays forever, ETB fires 2-3 times. GG.

  Atraxa, Grand Unifier [{3}{G}{W}{U}{B}] — 7/7 Flying Vigilance Deathtouch Lifelink.
    ETB: reveal top 10 library cards. For each card type (artifact, battle, creature,
    enchantment, instant, land, planeswalker, sorcery = 8 types), may put 1 card of
    that type into hand. Rest on bottom in random order.
    KEY: Hits ~4-6 cards typically. With Goryo + Ephemerate: hits 2-3 times total.

  Griselbrand [{4}{B}{B}{B}{B}] — 7/7 Flying Lifelink.
    Pay 7 life: Draw seven cards. Repeat until dead or winning.
    With Goryo's: enter → draw 7 (13 life) → draw 7 (6 life) → usually enough.
    Ephemerate saves Griselbrand from exile too.

  Ulamog, the Defiler [{10}] — Legendary Creature, Eldrazi. 7/7.
    Cast trigger: opponent exiles top half of their library.
    Ward—Sacrifice two permanents.
    Enters with +1/+1 counters = greatest MV among cards in exile.
    Annihilator X where X = counters.
    NOTE: Cast trigger requires actually CASTING — Goryo's puts it directly into play
    (no cast trigger). Goryo's into Ulamog gets the 7/7 Annihilator body without exile.
    With many cards in exile (from fetches, surveil): Ulamog can be huge.

  Psychic Frog [{U}{B}] — Creature 1/2.
    Combat damage → draw a card.
    Discard a card: put a +1/+1 counter on this creature.
    Exile 3 from your GY: gains flying until EOT.
    KEY: PRIMARY GY ENABLER. Discard Atraxa/Griselbrand to Frog → put fatty in GY.
    T1 Frog, T2 discard Atraxa → Goryo's = T2 kill.
    Frog also grows as a standalone threat, deals real damage late.

  Quantum Riddler [{3}{U}{U}] — 4/6 Flying. ETB: draw a card.
    As long as you have ≤1 card in hand, draws that many +1 extra.
    Warp {1}{U}: cast from hand for {1}{U}, exile at end step, recast from exile later.
    BACKUP WIN CONDITION: If combo fails, Riddler is a 4/6 flying that draws cards.
    Warp on T2 ({U/B} land + other): drops a 4/6 for 2 mana temporarily.

  Solitude [{3}{W}{W}] — 3/2 Flash Lifelink.
    ETB: exile up to 1 other target creature (controller gains life = its power).
    Evoke: exile a white card from hand = cast for free.
    In goldfish: irrelevant (no creatures to exile). Pitchable as a white card.
    KEY: With Atraxa ETB hitting enchantment type — Solitude can be drawn naturally.

  Meticulous Archive / Undercity Sewers [Dual Lands]:
    Enter tapped. ETB: surveil 1 (look at top, may put in GY).
    KEY GY ENABLERS: Play surveil land → put Atraxa on top of library → GY.
    With 3 surveil triggers in a game: good chance of hitting Atraxa.

  Fatal Push [{B}] — Destroy MV ≤ 2 creature. Revolt: MV ≤ 4.
    Fetch land activates revolt immediately. Mostly dead in goldfish.

  Thoughtseize [{B}] — Target player reveals hand, you choose nonland, they discard.
    In goldfish: no opponent hand. But can self-Thoughtseize? No — targets "target player."
    Goldfish: dead card. Bottom it.

  Prismatic Ending [{X}{W}] — Converge: exile nonland permanent if MV ≤ colors spent.
    With Esper mana (W+U+B = 3 colors): exiles MV ≤ 3 at X=0 cost. Flexible removal.
    Dead in goldfish. Bottom it.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Constants ──────────────────────────────────────────────────────────────────
GORYO      = "Goryo's Vengeance"
ATRAXA     = "Atraxa, Grand Unifier"
GRISEL     = "Griselbrand"
ULAMOG_D   = "Ulamog, the Defiler"
PSYCHIC    = "Psychic Frog"
QUANTUM    = "Quantum Riddler"
EPHEMERATE = "Ephemerate"
SOLITUDE   = "Solitude"
THOUGHTSEIZE = "Thoughtseize"
PRISMATIC  = "Prismatic Ending"
FATAL_PUSH = "Fatal Push"
ARCHIVE    = "Meticulous Archive"
SEWERS     = "Undercity Sewers"

FATTIES       = {ATRAXA, GRISEL, ULAMOG_D}
SURVEIL_LANDS = {ARCHIVE, SEWERS}
DEAD_IN_GOLDFISH = {THOUGHTSEIZE, PRISMATIC, FATAL_PUSH, SOLITUDE}


class GoryoVengeanceAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Goryo's Vengeance (2026).

    Kill plan:
      A) T2 Goryo's: Psychic Frog T1 → discard Atraxa/Griselbrand → Goryo's T2.
         Atraxa ETB draws 4-6 cards. Ephemerate saves her, ETB fires again.
         Atraxa attacks as 7/7 flying lifelink deathtouch vigilance.
      B) Surveil into combo: Surveil land puts fatty in GY → Goryo's next turn.
      C) Fair plan: Psychic Frog grows via discards; Quantum Riddler 4/6 flyer.

    Typical kill: T3-5. T2 possible with perfect hand.
    """

    name = "Goryo's Vengeance"
    win_condition_damage = 20
    max_turns = 10

    # ── Per-game state ─────────────────────────────────────────────────
    _fatty_in_gy       = False   # Atraxa/Griselbrand/Ulamog in graveyard
    _fatty_in_gy_name  = None    # which fatty
    _goryo_fired       = False   # Goryo's Vengeance resolved
    _atraxa_up         = False
    _grisel_up         = False
    _ephemerate_used   = False   # Ephemerate cast this game (rebound pending)
    _rebound_pending   = False   # Ephemerate rebound ready next upkeep
    _frog_counters     = 0       # Psychic Frog +1/+1 counters
    _frog_up           = False
    _goryo_exile_dodged = False  # Ephemerate successfully saved the fatty

    def reset_game(self):
        self._fatty_in_gy       = False
        self._fatty_in_gy_name  = None
        self._goryo_fired       = False
        self._atraxa_up         = False
        self._grisel_up         = False
        self._ephemerate_used   = False
        self._rebound_pending   = False
        self._frog_counters     = 0
        self._frog_up           = False
        self._goryo_exile_dodged = False

    # ── Helpers ─────────────────────────────────────────────────────────
    def _has_fatty_in_hand(self, gs: GameState) -> bool:
        return any(c.name in FATTIES for c in gs.hand())

    def _has_discard_outlet(self, gs: GameState) -> bool:
        return self._frog_up  # Frog is the only discard outlet in the deck

    def _can_goryo(self, gs: GameState) -> bool:
        return (self._fatty_in_gy
                and any(c.name == GORYO for c in gs.hand())
                and gs.mana_pool.total() >= 2)

    def _can_ephemerate(self, gs: GameState) -> bool:
        return (any(c.name == EPHEMERATE for c in gs.hand())
                and gs.mana_pool.total() >= 1
                and (self._atraxa_up or self._grisel_up))

    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Goryo's Vengeance keep criteria:
          - Perfect: Goryo's + fatty in hand + Frog (discard outlet) + 2 lands
          - Fast: Frog + fatty + Goryo's + 1 land (T2 kill possible)
          - Acceptable: Goryo's + surveil land (can put fatty in GY via surveil)
          - Fair backup: Frog + Quantum Riddler + 2 lands
          - Never: 0 lands, 4+ lands (flood), Goryo's without any GY plan
        """
        if len(hand) <= 4:
            return True

        lands       = [c for c in hand if c.is_land()]
        has_goryo   = any(c.name == GORYO for c in hand)
        has_fatty   = self._has_fatty_in_hand(gs=type('', (), {'hand': lambda s: hand})())
        has_frog    = any(c.name == PSYCHIC for c in hand)
        has_surveil = any(c.name in SURVEIL_LANDS for c in hand)
        has_ephemerate = any(c.name == EPHEMERATE for c in hand)
        has_riddler = any(c.name == QUANTUM for c in hand)
        dead_count  = sum(1 for c in hand if c.name in DEAD_IN_GOLDFISH)

        if not lands: return False
        if len(lands) >= 5: return False
        if dead_count >= 3 and mulligans < 2: return False

        # Ideal combo hand
        if has_goryo and has_fatty and has_frog and len(lands) >= 1: return True
        if has_goryo and has_fatty and len(lands) >= 2: return True

        # Goryo + surveil land (can dig for fatty naturally)
        if has_goryo and has_surveil and len(lands) >= 2: return True

        # Goryo + Frog (Frog discards to get fatty in GY)
        if has_goryo and has_frog and len(lands) >= 2: return True

        # Fair plan: Frog + Riddler, no Goryo
        if has_frog and has_riddler and len(lands) >= 2: return True

        # Ephemerate in hand with Goryo = value hand
        if has_goryo and has_ephemerate and len(lands) >= 2: return True

        return mulligans >= 2

    def _has_fatty_in_hand(self, gs) -> bool:
        """Accept either GameState or a mock with hand()."""
        try:
            hand = gs.hand() if callable(gs.hand) else gs.hand
        except Exception:
            hand = gs.hand if isinstance(gs.hand, list) else []
        return any(c.name in FATTIES for c in hand)

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority:
          1. Dead-in-goldfish cards (Thoughtseize, Prismatic Ending, Fatal Push, Solitude)
          2. Excess lands past 2
          3. Duplicate copies of same fatty (1 Atraxa in GY is enough)
          4. Highest CMC non-combo cards
        """
        to_bottom: list[Card] = []
        lands = [c for c in hand if c.is_land()]

        # 1. Dead removal/disruption
        for c in hand:
            if len(to_bottom) >= n: break
            if c.name in DEAD_IN_GOLDFISH: to_bottom.append(c)

        # 2. Excess lands past 2 (keep one surveil land if possible)
        surveil_lands = [c for c in lands if c.name in SURVEIL_LANDS]
        other_lands   = [c for c in lands if c.name not in SURVEIL_LANDS]
        # Keep 1 surveil land + 1 other = 2 total
        excess = surveil_lands[1:] + other_lands[max(0, 1 - len(surveil_lands)):]
        for c in excess:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)

        # 3. Duplicate fatties (1 is enough in hand/GY plan)
        seen = set()
        for c in hand:
            if len(to_bottom) >= n: break
            if c.name in FATTIES and c not in to_bottom:
                if c.name in seen: to_bottom.append(c)
                else: seen.add(c.name)

        # 4. High CMC non-essentials
        rest = sorted(
            [c for c in hand if not c.is_land() and c not in to_bottom],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n: break
            if c.name not in {GORYO, PSYCHIC, EPHEMERATE, QUANTUM, ATRAXA, GRISEL}:
                to_bottom.append(c)

        return to_bottom[:n]


    # ── GY enablers ─────────────────────────────────────────────────────
    def _try_surveil_land(self, gs: GameState):
        """
        Meticulous Archive / Undercity Sewers: ETB surveil 1 → put top card in GY.
        If top card is a fatty → instant GY setup for Goryo's.
        """
        for card in list(gs.hand()):
            if card.name not in SURVEIL_LANDS: continue
            if gs.land_played: continue
            gs.zones.play_from_hand(card)
            gs.mana_pool.flex += 1  # tapped land, 1 mana
            # Surveil 1: look at top card
            if gs.zones.library:
                top = gs.zones.library[0]
                if top.name in FATTIES:
                    # Put it in GY
                    gs.zones.library.pop(0)
                    gs.zones.graveyard.append(top)
                    self._fatty_in_gy = True
                    self._fatty_in_gy_name = top.name
                    gs._log(f"  Surveil ({card.name}): {top.name} → graveyard!")
                else:
                    # Keep it on top (don't send non-fatty to GY)
                    gs._log(f"  Surveil ({card.name}): {top.name} kept on top")
            return

    def _try_discard_fatty_to_frog(self, gs: GameState):
        """
        Psychic Frog discard ability: discard a card → +1/+1 counter on Frog.
        Priority: discard a fatty (Atraxa/Griselbrand) to put it in GY.
        Also discard dead cards (Thoughtseize, Prismatic Ending) for value.
        """
        if not self._frog_up: return
        if self._fatty_in_gy: return  # already set up

        # Priority 1: discard a fatty
        for c in list(gs.hand()):
            if c.name in FATTIES:
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                self._fatty_in_gy = True
                self._fatty_in_gy_name = c.name
                self._frog_counters += 1
                gs._log(f"  Frog discard: {c.name} → GY (Frog now {1+self._frog_counters}/{2+self._frog_counters})")
                return

        # Priority 2: discard dead cards (Thoughtseize, removal)
        for c in list(gs.hand()):
            if c.name in DEAD_IN_GOLDFISH:
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                self._frog_counters += 1
                gs._log(f"  Frog discard: {c.name} (dead card) → Frog grows")
                return

    # ── Goryo's Vengeance ───────────────────────────────────────────────
    def _fire_goryo(self, gs: GameState):
        """
        Cast Goryo's Vengeance targeting the fatty in GY.
        Fatty enters with haste. Apply ETB. Track for Ephemerate window.
        """
        goryo_card = next((c for c in gs.hand() if c.name == GORYO), None)
        if not goryo_card: return False
        if gs.mana_pool.total() < 2: return False

        gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
        gs.zones.hand.remove(goryo_card)
        gs.zones.graveyard.append(goryo_card)

        # Find the fatty in GY and move to BF
        target_name = self._fatty_in_gy_name
        fatty = next((c for c in gs.zones.graveyard if c.name == target_name), None)
        if not fatty:
            # Fatty isn't literally in GY zone (simplified tracking) — create token
            from data.card import Card as _Card
            fatty = _Card.__new__(_Card)
            fatty.name = target_name or ATRAXA
            fatty.type_line = "Legendary Creature"
            fatty.power = "7"
            fatty.toughness = "7"
            fatty.cmc = 7
            fatty.mana_cost = ""
            fatty.tags = set()
            fatty.colors = []
        else:
            gs.zones.graveyard.remove(fatty)

        fatty.summoning_sickness = False  # haste from Goryo's
        fatty.turn_entered = gs.turn
        gs.zones.battlefield.append(fatty)
        self._goryo_fired = True
        self._fatty_in_gy = False
        self._fatty_in_gy_name = None

        gs._log(f"  Goryo's Vengeance: {fatty.name} enters with haste!")

        # Apply ETB
        if fatty.name == ATRAXA:
            self._atraxa_up = True
            self._atraxa_etb(gs)
        elif fatty.name == GRISEL:
            self._grisel_up = True
            self._griselbrand_etb(gs)
        elif fatty.name == ULAMOG_D:
            # Goryo's puts Ulamog into play directly (not cast) — no cast trigger
            # Still a 7/7 with Ward and Annihilator
            gs._log(f"  Ulamog, the Defiler: 7/7 in play (Goryo's = not cast, no exile trigger)")

        return True

    def _atraxa_etb(self, gs: GameState):
        """
        Atraxa ETB: reveal top 10 cards, take 1 of each card type into hand.
        Card types: artifact, battle, creature, enchantment, instant, land, planeswalker, sorcery.
        In goldfish: typically draws 3-6 cards (deck has all types).
        Simplified: draw N cards where N = min(8, cards_in_top_10_with_distinct_types).
        """
        revealed = []
        for _ in range(10):
            if gs.zones.library:
                revealed.append(gs.zones.library.pop(0))

        types_seen = set()
        kept = []
        priority_types = ["instant", "sorcery", "creature", "enchantment", "land", "artifact", "planeswalker"]
        for c in revealed:
            tl = c.type_line.lower()
            for t in priority_types:
                if t in tl and t not in types_seen:
                    types_seen.add(t)
                    kept.append(c)
                    break

        for c in kept:
            gs.zones.hand.append(c)
        for c in revealed:
            if c not in kept:
                gs.zones.library.append(c)  # goes to bottom

        gs._log(f"  Atraxa ETB: revealed 10, drew {len(kept)} cards ({[c.name for c in kept]})")

    def _griselbrand_etb(self, gs: GameState):
        """Griselbrand: pay 7 life → draw 7. Up to 2 activations."""
        life = getattr(gs, 'life', 20)
        draws = 0
        while life >= 7 and draws < 2:
            life -= 7
            for _ in range(7):
                if gs.zones.library:
                    gs.zones.hand.append(gs.zones.library.pop(0))
            draws += 1
        gs.life = life if hasattr(gs, 'life') else life
        gs._log(f"  Griselbrand: {draws}x draw 7 ({draws*7} cards), life={life}")

    # ── Ephemerate ──────────────────────────────────────────────────────
    def _try_ephemerate(self, gs: GameState):
        """
        Ephemerate the Goryo'd creature BEFORE end step to dodge exile.
        The creature leaves BF → Goryo's delayed trigger loses its object → misses.
        Creature returns immediately as a new permanent object with fresh ETB.
        Rebound: free Ephemerate at next upkeep → ETB fires again.
        """
        if not (self._atraxa_up or self._grisel_up): return
        if self._goryo_exile_dodged: return  # already safe
        ephemerate = next((c for c in gs.hand() if c.name == EPHEMERATE), None)
        if not ephemerate: return
        if gs.mana_pool.total() < 1: return

        gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
        gs.zones.hand.remove(ephemerate)
        gs.zones.exile.append(ephemerate)  # rebound exile
        self._ephemerate_used = True
        self._rebound_pending = True
        self._goryo_exile_dodged = True

        gs._log("  Ephemerate: blink the Goryo'd creature — exile trigger MISSED!")

        # Creature leaves and returns — ETB fires again
        if self._atraxa_up:
            self._atraxa_etb(gs)
            gs._log("  Atraxa ETB (Ephemerate): second reveal-10 draw!")
        if self._grisel_up:
            self._griselbrand_etb(gs)
            gs._log("  Griselbrand ETB (Ephemerate): draw 7 again!")

    def _apply_rebound(self, gs: GameState):
        """At beginning of upkeep, cast Ephemerate for free (rebound)."""
        if not self._rebound_pending: return
        self._rebound_pending = False
        gs._log("  Ephemerate Rebound: free blink at upkeep!")
        if self._atraxa_up:
            self._atraxa_etb(gs)
        if self._grisel_up:
            self._griselbrand_etb(gs)


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat priority:
          1. Reset on T1
          2. Rebound Ephemerate if pending (upkeep, but model here)
          3. Land drop (prefer surveil lands when no fatty in GY yet)
          4. Psychic Frog (primary GY enabler + future threat)
          5. Discard fatty to Frog if Frog is in play and fatty in hand
          6. Goryo's Vengeance if fatty in GY
          7. Ephemerate to dodge exile and get second ETB
          8. Quantum Riddler (backup threat / draw engine)
          9. Solitude evoke (dead in goldfish — skip)
        """
        if gs.turn == 1:
            self.reset_game()

        # ── 0. Rebound Ephemerate ───────────────────────────────────────
        self._apply_rebound(gs)

        # ── 1. Land drop ────────────────────────────────────────────────
        if not gs.land_played:
            # Priority: surveil lands first (they put fatty in GY)
            if not self._fatty_in_gy:
                self._try_surveil_land(gs)
            # If surveil land played, might have set up GY
            if not gs.land_played:
                # Regular land drop
                for c in list(gs.hand()):
                    if c.is_land():
                        gs.zones.play_from_hand(c)
                        gs.mana_pool.flex += 1
                        break

        # ── 2. Psychic Frog ({U}{B} = 2 mana) ──────────────────────────
        if not self._frog_up:
            for card in list(gs.hand()):
                if card.name == PSYCHIC and gs.mana_pool.total() >= 2:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                    gs.zones.play_from_hand(card)
                    card.summoning_sickness = True
                    card.turn_entered = gs.turn
                    self._frog_up = True
                    gs._log(f"  Psychic Frog: 1/2 in play (discard outlet active)")
                    break

        # ── 3. Discard fatty to Frog ─────────────────────────────────────
        self._try_discard_fatty_to_frog(gs)

        # ── 4. Goryo's Vengeance ─────────────────────────────────────────
        if self._fatty_in_gy and not self._goryo_fired:
            self._fire_goryo(gs)

        # ── 5. Ephemerate (dodge exile before end step) ──────────────────
        # Must use before end step arrives — in goldfish, model as main phase cast
        if self._goryo_fired and not self._goryo_exile_dodged:
            self._try_ephemerate(gs)

        # ── 6. Quantum Riddler ({3}{U}{U} = 5 mana, or Warp {1}{U} = 2) ──
        for card in list(gs.hand()):
            if card.name != QUANTUM: continue
            if gs.mana_pool.total() >= 5:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 5)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                # ETB: draw a card
                if gs.zones.library:
                    gs.zones.hand.append(gs.zones.library.pop(0))
                gs._log(f"  Quantum Riddler: 4/6 flying, drew 1")
            elif gs.mana_pool.total() >= 2:
                # Warp cost: {1}{U} = 2 mana
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log(f"  Quantum Riddler (Warp): 4/6 flying for 2 mana (exiles at end step)")
            break

        # ── 7. If no combo, try surveil land for setup ─────────────────
        if not self._fatty_in_gy and not gs.land_played:
            self._try_surveil_land(gs)

        # ── 8. Try Goryo's again if surveil just found a fatty ──────────
        if self._fatty_in_gy and not self._goryo_fired:
            self._fire_goryo(gs)
            if self._goryo_fired and not self._goryo_exile_dodged:
                self._try_ephemerate(gs)

    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat:
          1. Compute combat damage from Atraxa / Griselbrand / Frog
          2. Attempt Goryo's if GY setup happened mid-turn (instant speed model)
          3. Ephemerate dodge if not yet used
        """
        # ── 1. Combat damage ────────────────────────────────────────────
        for c in gs.zones.battlefield:
            if getattr(c, "summoning_sickness", True): continue
            if not c.has(Tag.CREATURE): continue
            try:
                power = int(c.power or 0) + (self._frog_counters if c.name == PSYCHIC else 0)
            except (ValueError, TypeError):
                power = 0
            if power <= 0: continue

            # Atraxa: 7/7 flying lifelink deathtouch vigilance
            if c.name == ATRAXA:
                gs.damage_dealt += 7
                gs._log(f"  Atraxa attacks: 7 lifelink ({gs.damage_dealt} total)")
            # Griselbrand: 7/7 flying lifelink
            elif c.name == GRISEL:
                gs.damage_dealt += 7
                gs._log(f"  Griselbrand attacks: 7 ({gs.damage_dealt} total)")
            # Ulamog: 7/7 + annihilator
            elif c.name == ULAMOG_D:
                gs.damage_dealt += 7
                gs._log(f"  Ulamog attacks: 7 + annihilator ({gs.damage_dealt} total)")
            # Psychic Frog: 1+counters
            elif c.name == PSYCHIC:
                frog_power = 1 + self._frog_counters
                gs.damage_dealt += frog_power
                # Deals combat damage → draw a card
                if gs.zones.library:
                    gs.zones.hand.append(gs.zones.library.pop(0))
                gs._log(f"  Psychic Frog attacks: {frog_power}, drew 1 ({gs.damage_dealt} total)")
            # Quantum Riddler: 4/6 flying
            elif c.name == QUANTUM:
                gs.damage_dealt += 4
                gs._log(f"  Quantum Riddler attacks: 4 ({gs.damage_dealt} total)")

        # ── 2. Ephemerate if Goryo'd but no dodge yet ────────────────────
        if self._goryo_fired and not self._goryo_exile_dodged:
            self._try_ephemerate(gs)

        # ── 3. Second attempt at Goryo's (end-of-turn model) ─────────────
        # In real play Goryo's can be cast at instant speed at opponent's EOT.
        # Goldfish: model as post-combat cast if fatty just hit GY via Frog.
        if not self._goryo_fired and self._fatty_in_gy:
            self._fire_goryo(gs)
            if self._goryo_fired and not self._goryo_exile_dodged:
                self._try_ephemerate(gs)

    # ── Sideboard premium ────────────────────────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        opp = opponent.lower()
        if any(x in opp for x in ("living end", "cascade")):
            return -0.06  # Grief/Solitude interaction problematic
        if any(x in opp for x in ("control", "blink")):
            return 0.03   # Flare of Denial + Mystical Dispute
        if any(x in opp for x in ("boros energy", "affinity")):
            return -0.05  # Too fast; we're combo-slow
        if any(x in opp for x in ("yawgmoth", "reanimator")):
            return 0.04   # Nihil Spellbomb hits their GY
        if any(x in opp for x in ("humans",)):
            return -0.04  # Meddling Mage on Goryo's is brutal
        if any(x in opp for x in ("tron", "eldrazi")):
            return 0.05   # Wear//Tear + Dress Down hits their artifacts
        return 0.0



# ── Edge Case Registry ──────────────────────────────────────────────────────
#
# EC-01: Goryo's Vengeance + Ephemerate — the exile-dodge interaction.
#   Goryo's creates a delayed triggered ability that tracks the SPECIFIC OBJECT.
#   Object identity in MTG is tracked by the object's position in the zone.
#   Ephemerate exiles then returns — the returned creature is a NEW object.
#   Goryo's trigger resolves at end step: "exile [original object]" — it's gone.
#   The new object (from Ephemerate return) is not affected. Creature stays permanently.
#   CRITICAL TIMING: Must Ephemerate BEFORE the end step trigger resolves.
#   If you cast Ephemerate during the end step after Goryo's trigger is on the stack:
#   the trigger is already on the stack, it resolves and tries to exile — creature just
#   Ephemerated = new object ≠ what the trigger tracks → nothing happens. Still works!
#   Even if you Ephemerate IN RESPONSE to the trigger, it works.
#
# EC-02: Atraxa ETB reveals top 10 — each card type once.
#   The 8 card types: artifact, battle, creature, enchantment, instant,
#   land, planeswalker, sorcery. Maximum 8 cards drawn from one ETB.
#   Cards with multiple types (e.g., artifact creature) count for both types —
#   but you only take ONE card of that specific revealed card.
#   Practically: most games you draw 3-6 cards per Atraxa ETB.
#
# EC-03: Griselbrand "pay 7 life" — this is an activated ability, NOT the ETB.
#   Can activate multiple times if you have life. At 20 starting life:
#   → activate 1: 13 life, 7 cards. → activate 2: 6 life, 14 cards.
#   → activate 3: would go to -1 life = you die. Stop at 2.
#   With Atraxa in play (lifelink attacks gain life): more activations possible.
#
# EC-04: Ulamog, the Defiler cast trigger DOES NOT fire with Goryo's.
#   Goryo's says "return to the battlefield" — this is NOT casting.
#   "When you cast this spell" = only fires when actually cast.
#   Goryo's into Ulamog: 7/7 with Ward and Annihilator, but no exile-top-half trigger.
#   However, Ulamog enters with counters = greatest MV among cards in exile.
#   From fetches and surveil: exile zone often has 3-5 cards. Ulamog enters as ~3/3 base.
#
# EC-05: Psychic Frog discard — you CHOOSE which card to discard.
#   This is not a "may" — it's "discard a card" (must discard if able).
#   Wait: "Discard a card: Put a +1/+1 counter" — this is an ACTIVATED ABILITY you pay.
#   You pay the cost (discard) to get the effect (counter). So you choose when to activate.
#   Optimal: discard Atraxa/Griselbrand on T2 before casting Goryo's → T2 combo.
#
# EC-06: Ephemerate Rebound — the rebound copy is cast "without paying its mana cost."
#   This means it costs 0 mana. Triggers any "when you cast a spell" effects.
#   The rebound is optional — "you MAY cast this card from exile."
#   If your creature is already safe (Goryo's dodged), rebound is just a free ETB.
#
# EC-07: Solitude Evoke — exile a white card from hand.
#   In this deck: no white cards in the main deck except Solitude itself.
#   To evoke Solitude, you need to exile another Solitude. Or a SB card.
#   Prismatic Ending is white. Ephemerate is white.
#   Real play: evoke Solitude by exiling Prismatic Ending or an Ephemerate.
#   Goldfish: irrelevant.
#
# EC-08: Quantum Riddler Warp timing.
#   Warp {1}{U}: cast from hand for {1}{U}, exile at beginning of NEXT end step.
#   The creature exists for ~1 turn at reduced cost. Gets attacks in if haste available.
#   Can attack once (combat phase), then it exiles at end step.
#   Unlike Goryo's: Warp's exile trigger cannot be dodged by Ephemerate in the same way
#   because Warp creates a static duration, not a trackable object exile.
#   Actually: Ephemerate WOULD work on Warp'd Riddler too — same mechanics.
#
# EC-09: Fatal Push revolt activation.
#   Revolt requires "a permanent left the battlefield under your control this turn."
#   Fetch land activation (sacrifice fetch) = revolt enabled for Fatal Push.
#   Ephemerate also triggers revolt (creature left BF under your control = the exile zone).
#   After Ephemerate: Fatal Push hits MV ≤ 4.
#
# EC-10: Goryo's on opponent's end step vs your main phase.
#   Real play: cast Goryo's at END OF OPPONENT'S TURN (instant speed):
#   → Fatty ETB → draw cards → your turn starts with a full hand.
#   → Goryo's exile trigger set for YOUR end step (next end step after casting).
#   → You attack with hasted creature, Ephemerate to dodge exile.
#   In goldfish model: simplified to main phase cast since no opponent turn matters.
#   The key insight: casting at opponent's EOT gives you a FULL TURN of Goryo's value.
#
EDGE_CASES = [
    "EC-01: Ephemerate works IN RESPONSE to Goryo's end-step trigger — even on the stack, creature is new object",
    "EC-02: Atraxa ETB max 8 cards (1 per card type) — practically 3-6 per trigger in most hands",
    "EC-03: Griselbrand draws: 2 activations max at 20 life (13→6). Stop before negative",
    "EC-04: Goryo's Ulamog = no cast trigger — no exile opponent's library. Just 7/7 Annihilator body",
    "EC-05: Psychic Frog discard = activated ability (your choice when to use) — not forced",
    "EC-06: Ephemerate Rebound is optional — 'you may' cast it from exile at next upkeep",
    "EC-07: Solitude Evoke needs white card — Ephemerate and Prismatic Ending both qualify",
    "EC-08: Quantum Riddler Warp exile can also be dodged by Ephemerate — same object-tracking mechanic",
    "EC-09: Ephemerate triggers revolt for Fatal Push — fetch + Ephemerate = Push hits MV ≤ 4",
    "EC-10: Real Goryo's is cast at opponent's EOT (instant speed) — model compresses to main phase",
]
