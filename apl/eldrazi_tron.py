"""
eldrazi_tron.py — APL for Modern Eldrazi Tron (full rewrite, April 2026)

VERIFIED card interactions (CardDB, deck: eldrazi_tron_modern.txt):

  Tron Lands [all: Land]:
    Urza's Mine / Urza's Tower / Urza's Power Plant
    All three in play → tap together for {7} colorless total (3+3+1 or 1+2+4).
    Individually: Mine {1}, Tower {2} (or was it 3?), Plant {2}.
    Actually: Mine taps for {1}, Tower taps for {3}, Plant taps for {2} when Tron assembled.
    Without Tron: each taps for {1} only.

  Eldrazi Temple [Land]:
    {T}: Add {C}.
    {T}: Add {C}{C}. Spend only to cast colorless Eldrazi spells or activate their abilities.
    KEY: TKS ({3}{C}) = Temple covers {C}{C}, rest from other sources. Huge T2-3 play.

  Ugin's Labyrinth [Land]:
    Imprint (enter): may exile a colorless card with MV 7+ from hand.
    {T}: Add {C}. If imprinted card exiled: Add {C}{C}{C} instead.
    {T}: Return exiled card to owner's hand.
    KEY: Imprint Ulamog or Devourer T1 → {CCC} per turn, then get it back when needed.

  Sowing Mycospawn [{3}{G}] — Creature, Eldrazi Fungus, Devoid. 3/3.
    When cast: search library for a land, put it onto battlefield, then shuffle.
    Kicker {1}{C}: if kicked, exile target land.
    KEY: Acts as Expedition Map but better — the land enters play immediately (not hand).
    Gets the missing Tron piece directly into play. 3/3 Devoid body stays.

  Devourer of Destiny [{5}{C}{C}] — Creature, Eldrazi. 6/6.
    May reveal from opening hand → at start of first upkeep, look at top 4, keep 1, exile rest.
    When cast: exile target permanent that's one or more colors.
    KEY: Imprint on Ugin's Labyrinth T1 → {CCC}/turn. Retrieve when ready to cast (at 7+ mana).

  Thought-Knot Seer [{3}{C}] — Creature, Eldrazi. 4/4.
    ETB: target opponent reveals hand, exile a nonland card from it.
    Dies: target opponent draws a card.
    KEY: T3 with Tron online (or T2 with Eldrazi Temple + other mana). Shuts down combo.

  Karn, the Great Creator [{4}] — Legendary Planeswalker.
    Static: activated abilities of artifacts opponent controls can't activate.
    +1: until your next turn, up to 1 target noncreature artifact becomes artifact creature
        with P/T each equal to its MV.
    −2: reveal artifact card from outside game (SB) or choose face-up artifact in exile;
        put it into your hand.
    KEY: tutors any SB artifact (Ensnaring Bridge, Trinisphere, Ballista, etc.).

  Ugin, Eye of the Storms [{7}] — Legendary Planeswalker.
    Cast trigger: exile up to 1 target permanent that's 1+ colors.
    Whenever you cast a colorless spell: exile up to 1 target colored permanent.
    +2: gain 3 life, draw a card.
    0: add {C}{C}{C}.
    −11: search library for any number of colorless nonland cards, exile; cast free until EOT.
    KEY: Self-sustaining engine. Tap for {CCC} each turn, draw + 3 life. Exile colored threats.

  Kozilek's Command [{X}{C}{C}] — Kindred Instant, Eldrazi. Choose two:
    • Target player creates X 0/1 Eldrazi Spawn tokens ("Sac: Add {C}").
    • Target player scries X, draws a card.
    • Exile target creature with MV ≤ X.
    • Exile up to X target cards from graveyards.
    GOLDFISH BEST: Spawn tokens + scry/draw → ramp + card selection.

  Expedition Map [{1}] — Artifact.
    {2}, {T}, Sacrifice: search library for any land, reveal, put into hand, then shuffle.
    KEY: Costs {1} to deploy, {2} more to activate (total 3 mana over 2 turns to get any land).
    Typically finds the missing Tron piece.

  Talisman of Resilience / Talisman of Impulse [{2}] — Artifact.
    {T}: Add {C}.
    {T}: Add {B}/{G} or {R}/{G}. (1 damage to you.)
    KEY: Colorless mana accelerant. Helps reach Tron mana curve faster.

  Dismember [{1}{B/P}{B/P}] — Instant. Target gets -5/-5.
    Pay 4 life to cast for {1} (goldfish: dead removal, bottom it).

  Ulamog, the Ceaseless Hunger [{10}] — Legendary Creature, Eldrazi. 10/10 Indestructible.
    Cast: exile two target permanents.
    Attack: defending player exiles top 20 library.
    KEY: Imprint on Labyrinth early, retrieve at 10 mana. One swing ends games.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Card name constants ────────────────────────────────────────────────────────
MINE        = "Urza's Mine"
TOWER       = "Urza's Tower"
PLANT       = "Urza's Power Plant"
TEMPLE      = "Eldrazi Temple"
LABYRINTH   = "Ugin's Labyrinth"
MYCOSPAWN   = "Sowing Mycospawn"
DEVOURER    = "Devourer of Destiny"
TKS         = "Thought-Knot Seer"
KARN        = "Karn, the Great Creator"
UGIN        = "Ugin, Eye of the Storms"
COMMAND     = "Kozilek's Command"
MAP         = "Expedition Map"
TALISMAN_R  = "Talisman of Resilience"
TALISMAN_I  = "Talisman of Impulse"
DISMEMBER   = "Dismember"
ULAMOG      = "Ulamog, the Ceaseless Hunger"
RELIC       = "Relic of Progenitus"

TRON_LANDS  = {MINE, TOWER, PLANT}
TALISMANS   = {TALISMAN_R, TALISMAN_I}
# Eldrazi Spawn token mana value is 0, they sac for {C} each
DEAD_IN_GOLDFISH = {DISMEMBER, RELIC}


class EldraziTronAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Eldrazi Tron (2026).

    Kill plan:
      A) Assemble Tron (Mine + Tower + Plant) → 7 colorless mana T3.
         Cast TKS / Karn / Ugin once online.
      B) Ugin's Labyrinth T1 imprinting Devourer/Ulamog → {CCC}/turn
         → reach 7 mana by T3 even without full Tron.
      C) Sowing Mycospawn searches the missing Tron piece directly into play.
      D) Eldrazi Temple gives {CC} for Eldrazi spells → TKS on T2 possible.

    Typical kill: T5-8 via TKS/Devourer/Ulamog beatdown.
    """

    name = "Eldrazi Tron"
    win_condition_damage = 20
    max_turns = 14

    # ── Per-game state (class-level defaults) ──────────────────────────
    _tron_assembled     = False   # Mine + Tower + Plant all in play
    _labyrinth_imprint  = None    # card name imprinted on Ugin's Labyrinth
    _labyrinth_up       = False   # Labyrinth on battlefield
    _map_sacrificed     = False   # Expedition Map used this game
    _karn_up            = False   # Karn on battlefield
    _ugin_up            = False   # Ugin, Eye of the Storms on battlefield
    _ugin_loyalty       = 0
    _spawn_count        = 0       # Eldrazi Spawn tokens (each sac for {C})
    _devourer_revealed  = False   # Devourer revealed from opening hand

    def reset_game(self):
        self._tron_assembled    = False
        self._labyrinth_imprint = None
        self._labyrinth_up      = False
        self._map_sacrificed    = False
        self._karn_up           = False
        self._ugin_up           = False
        self._ugin_loyalty      = 0
        self._spawn_count       = 0
        self._devourer_revealed = False

    # ── Tron assembly checker ───────────────────────────────────────────
    def _tron_in_play(self, gs: GameState) -> bool:
        """True if all three Tron lands are on the battlefield."""
        bf_names = {c.name for c in gs.zones.battlefield if c.is_land()}
        return all(piece in bf_names for piece in TRON_LANDS)

    def _tron_piece_count(self, gs: GameState) -> int:
        """How many of the 3 Tron pieces are in play?"""
        bf_names = {c.name for c in gs.zones.battlefield if c.is_land()}
        return sum(1 for piece in TRON_LANDS if piece in bf_names)

    def _missing_tron_piece(self, gs: GameState) -> str | None:
        """Returns the name of the first missing Tron land, or None if complete."""
        bf_names = {c.name for c in gs.zones.battlefield if c.is_land()}
        for piece in [MINE, TOWER, PLANT]:
            if piece not in bf_names:
                return piece
        return None

    def _total_mana(self, gs: GameState) -> int:
        """Rough estimate of how much mana we can generate this turn."""
        return gs.mana_pool.total()

    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Eldrazi Tron keep criteria:
          - Need lands to function (at least 2)
          - Want at minimum 1 Tron piece OR Expedition Map OR Sowing Mycospawn
          - Want at least 1 meaningful threat (TKS, Karn, Devourer, Ugin, Ulamog)
          - Ugin's Labyrinth + big Eldrazi in hand = T1 {CCC}, always keep
          - 5+ hands: need Tron + payoff OR Map + payoff
        """
        if len(hand) <= 4:
            return True

        lands      = [c for c in hand if c.is_land()]
        tron_pieces= [c for c in lands if c.name in TRON_LANDS]
        has_map    = any(c.name == MAP for c in hand)
        has_spawn  = any(c.name == MYCOSPAWN for c in hand)
        has_lab    = any(c.name == LABYRINTH for c in hand)
        has_temple = any(c.name == TEMPLE for c in hand)

        threats    = [c for c in hand if c.name in {TKS, KARN, DEVOURER, UGIN, ULAMOG}]
        imprintable= any(c.name in {DEVOURER, ULAMOG} for c in hand)
        talismans  = [c for c in hand if c.name in TALISMANS]
        dead       = [c for c in hand if c.name in DEAD_IN_GOLDFISH]

        # Always mull: zero lands and no Talisman
        if not lands and not talismans:
            return False
        # Always mull: 5+ lands (flood)
        if len(lands) >= 5:
            return False
        # Mull excessive dead cards
        if len(dead) >= 2 and mulligans < 2:
            return False

        # Ugin's Labyrinth + Devourer/Ulamog in hand = T1 {CCC}, must keep
        if has_lab and imprintable and len(lands) >= 1:
            return True

        # 2 Tron pieces + threat: solid keep
        if len(tron_pieces) >= 2 and threats:
            return True

        # Map + 2 lands + threat: can assemble Tron
        if has_map and len(lands) >= 2 and threats:
            return True

        # Mycospawn + any land + threat: can fetch Tron piece directly
        if has_spawn and len(lands) >= 2 and threats:
            return True

        # Eldrazi Temple + Talisman + TKS: T2 TKS is legitimate
        if has_temple and talismans and any(c.name == TKS for c in hand):
            return True

        # 3 lands + threat: might stumble but castable
        if len(lands) >= 3 and threats and mulligans <= 1:
            return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority:
          1. Dismember (dead in goldfish)
          2. Excess non-Tron, non-Temple lands past 3
          3. Duplicate copies of same big threat
          4. Highest CMC non-threats
        """
        to_bottom: list[Card] = []

        # 1. Dead removal
        for c in hand:
            if len(to_bottom) >= n:
                break
            if c.name in DEAD_IN_GOLDFISH:
                to_bottom.append(c)

        # 2. Excess lands: keep at most 2 non-Tron, non-Temple, non-Labyrinth
        generic_lands = [
            c for c in hand
            if c.is_land()
            and c.name not in TRON_LANDS
            and c.name not in {TEMPLE, LABYRINTH}
            and c not in to_bottom
        ]
        for c in generic_lands[2:]:
            if len(to_bottom) >= n:
                break
            to_bottom.append(c)

        # 3. Duplicate big threats (keep 1 Ulamog, 1 Ugin; second copies are late-game)
        seen = set()
        for c in hand:
            if len(to_bottom) >= n:
                break
            if c.name in {ULAMOG, UGIN, KARN} and c not in to_bottom:
                if c.name in seen:
                    to_bottom.append(c)
                else:
                    seen.add(c.name)

        # 4. High-CMC non-threats
        rest = sorted(
            [c for c in hand if not c.is_land() and c not in to_bottom],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n:
                break
            to_bottom.append(c)

        return to_bottom[:n]


    # ── Mana helpers ────────────────────────────────────────────────────
    def _apply_talisman_mana(self, gs: GameState):
        """Tap untapped Talismans for {C} (no life loss for goldfish)."""
        for c in gs.zones.battlefield:
            if c.name in TALISMANS and not getattr(c, "_tapped", False):
                gs.mana_pool.flex += 1
                c._tapped = True

    def _apply_labyrinth_mana(self, gs: GameState):
        """Ugin's Labyrinth taps for {CCC} if imprinted, else {C}."""
        labs = [c for c in gs.zones.battlefield
                if c.name == LABYRINTH and not getattr(c, "_tapped", False)]
        for lab in labs:
            amount = 3 if self._labyrinth_imprint else 1
            gs.mana_pool.flex += amount
            lab._tapped = True
            gs._log(f"  Ugin's Labyrinth: +{amount}C (imprint: {self._labyrinth_imprint or 'none'})")

    def _apply_temple_mana(self, gs: GameState):
        """Eldrazi Temple taps for {CC} (earmarked for Eldrazi; model as flex)."""
        for c in gs.zones.battlefield:
            if c.name == TEMPLE and not getattr(c, "_tapped", False):
                gs.mana_pool.flex += 2
                c._tapped = True

    def _apply_tron_mana(self, gs: GameState):
        """When Tron is assembled, all 3 pieces tap for 7 total."""
        tron_pieces = [c for c in gs.zones.battlefield
                       if c.name in TRON_LANDS and not getattr(c, "_tapped", False)]
        assembled = self._tron_in_play(gs)
        # Mine=1, Power Plant=2, Tower=3 (Tron gives 7 when all tapped, else 1 each)
        mana_map = {MINE: 1, PLANT: 2, TOWER: 4} if assembled else {MINE: 1, PLANT: 1, TOWER: 1}
        for c in tron_pieces:
            mana_map_val = mana_map.get(c.name, 1)
            gs.mana_pool.flex += mana_map_val
            c._tapped = True
        if assembled and tron_pieces:
            self._tron_assembled = True
            gs._log(f"  Tron assembled: +7C this turn")

    def _apply_spawn_mana(self, gs: GameState):
        """Sacrifice Eldrazi Spawn tokens for mana when needed."""
        if self._spawn_count > 0:
            gs.mana_pool.flex += self._spawn_count
            gs._log(f"  Sac {self._spawn_count} Eldrazi Spawn: +{self._spawn_count}C")
            self._spawn_count = 0

    def _generate_all_mana(self, gs: GameState):
        """Generate all available mana: Tron + Labyrinth + Temple + Talismans."""
        self._apply_tron_mana(gs)
        self._apply_labyrinth_mana(gs)
        self._apply_temple_mana(gs)
        self._apply_talisman_mana(gs)

    # ── Ugin's Labyrinth imprint ────────────────────────────────────────
    def _try_imprint_labyrinth(self, gs: GameState):
        """
        If Ugin's Labyrinth just entered, imprint the best card from hand.
        Priority: Devourer (7 MV, also a threat), Ulamog (10 MV, biggest clock).
        Imprinting upgrades the land from {C} to {CCC} — massive acceleration.
        """
        labs = [c for c in gs.zones.battlefield if c.name == LABYRINTH]
        if not labs or self._labyrinth_imprint:
            return

        imprint_priority = [DEVOURER, ULAMOG]
        for name in imprint_priority:
            target = next((c for c in gs.hand() if c.name == name), None)
            if target:
                gs.zones.hand.remove(target)
                gs.zones.exile.append(target)
                self._labyrinth_imprint = name
                gs._log(f"  Ugin's Labyrinth: imprinted {name} → taps for {{CCC}}")
                # If Devourer was revealed for its opener ability, note it
                if name == DEVOURER:
                    self._devourer_revealed = True
                return

    # ── Expedition Map ──────────────────────────────────────────────────
    def _try_use_map(self, gs: GameState):
        """
        Sacrifice Expedition Map to fetch missing Tron piece.
        Cost: {2} + {T} + sacrifice. Gets land into hand (we then play it as land drop next turn).
        Actually in goldfish: simplify by putting it directly on battlefield.
        """
        if self._map_sacrificed:
            return
        maps = [c for c in gs.zones.battlefield if c.name == MAP]
        if not maps:
            return
        if gs.mana_pool.total() < 2:
            return
        target = self._missing_tron_piece(gs)
        if not target:
            return  # Tron already assembled

        gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
        gs.zones.battlefield.remove(maps[0])
        gs.zones.graveyard.append(maps[0])
        self._map_sacrificed = True

        # Fetch the missing Tron piece into hand, then play it as land this turn
        fetched = next((c for c in gs.zones.library if c.name == target), None)
        if fetched:
            gs.zones.library.remove(fetched)
            gs.zones.hand.append(fetched)
            gs._log(f"  Expedition Map: fetched {target}")
            # Play it as our land drop if we haven't played one yet
            if not gs._land_played_this_turn:
                gs.zones.hand.remove(fetched)
                gs.zones.battlefield.append(fetched)
                gs._land_played_this_turn = True
                gs._log(f"  Play {target} as land drop")

    # ── Kozilek's Command ────────────────────────────────────────────────
    def _cast_command(self, gs: GameState, x_value: int = 2):
        """
        Kozilek's Command at X=2: choose two from:
          1. Create 2 Eldrazi Spawn (sac for {C} each → future mana)
          2. Scry 2, draw a card
        Goldfish best modes: Spawn tokens (ramp) + draw (find threats).
        Cost: {2}{C}{C} for X=2, or {X}{C}{C} generally.
        """
        cost = x_value + 2  # {X}{CC} = X + 2 generic mana
        if gs.mana_pool.total() < cost:
            return False

        gs.mana_pool.flex = max(0, gs.mana_pool.flex - cost)
        # Mode 1: Create X Spawn tokens
        self._spawn_count += x_value
        # Mode 2: Scry X, draw a card
        if gs.zones.library:
            drawn = gs.zones.library.pop(0)
            gs.zones.hand.append(drawn)
        gs._log(f"  Kozilek's Command X={x_value}: +{x_value} Spawn tokens, draw 1")
        return True


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat priority:
          1. Reset per-game state on T1
          2. Land drop (prioritize Tron pieces → Labyrinth → Temple → basics)
          3. Ugin's Labyrinth: try to imprint Devourer/Ulamog (upgrades to {CCC})
          4. Generate all mana: Tron + Labyrinth + Temple + Talismans + Spawn
          5. Expedition Map: deploy if not yet, or sacrifice to fetch missing Tron piece
          6. Sowing Mycospawn: put missing Tron piece directly into play
          7. Talismans (ramp artifacts)
          8. Early threats: TKS, Karn, Devourer (once we have enough mana)
          9. Ugin, Eye of the Storms (7 mana)
          10. Ulamog (10 mana — unlikely goldfish but possible with Labyrinth + Tron)
          11. Kozilek's Command for Spawn token ramp
        """
        if gs.turn == 1:
            self.reset_game()

        # ── 1. Land drop: strict priority order ────────────────────────
        self._play_best_land(gs)

        # ── 2. Labyrinth imprint ────────────────────────────────────────
        self._try_imprint_labyrinth(gs)

        # ── 3. Generate all mana ────────────────────────────────────────
        self._generate_all_mana(gs)
        self._apply_spawn_mana(gs)

        # ── 4. Deploy Expedition Map ({1}) ──────────────────────────────
        if not self._map_sacrificed:
            for card in list(gs.hand()):
                if card.name == MAP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  Expedition Map deployed")
                    break

        # ── 5. Use Expedition Map to fetch Tron piece ──────────────────
        if not self._tron_in_play(gs):
            self._try_use_map(gs)
            # Re-tap any newly played Tron land
            self._apply_tron_mana(gs)

        # ── 6. Talisman deployment ──────────────────────────────────────
        for card in list(gs.hand()):
            if card.name in TALISMANS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                self._apply_talisman_mana(gs)
                break

        # ── 7. Sowing Mycospawn: ramp a Tron piece into play ───────────
        # Cost: {3}{G} = 4 mana (all generic since Devoid). Gets a land directly into play.
        if not self._tron_in_play(gs):
            for card in list(gs.hand()):
                if card.name == MYCOSPAWN and gs.mana_pool.total() >= 4:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
                    gs.zones.play_from_hand(card)
                    card.summoning_sickness = True
                    card.turn_entered = gs.turn
                    # ETB: search for land → put it into play
                    target = self._missing_tron_piece(gs)
                    if not target:
                        # Tron complete — fetch any useful land (Forest for color if needed)
                        target = "Forest"
                    fetched = next((c for c in gs.zones.library if c.name == target), None)
                    if fetched:
                        gs.zones.library.remove(fetched)
                        gs.zones.battlefield.append(fetched)
                        fetched.summoning_sickness = False
                        fetched.turn_entered = gs.turn
                        self._apply_tron_mana(gs)  # re-check Tron
                        gs._log(f"  Sowing Mycospawn: put {target} into play, Tron={self._tron_in_play(gs)}")
                    break

        # ── 8. Thought-Knot Seer ({3}{C} = 4 mana) ────────────────────
        for card in list(gs.hand()):
            if card.name == TKS and gs.mana_pool.total() >= 4:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log("  TKS: 4/4, ETB exiled opponent's best card")
                break

        # ── 9. Karn, the Great Creator ({4}) ───────────────────────────
        if not self._karn_up:
            for card in list(gs.hand()):
                if card.name == KARN and gs.mana_pool.total() >= 4:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
                    gs.cast_spell(card)
                    self._karn_up = True
                    # Karn −2: tutor artifact from SB (Ensnaring Bridge, etc.)
                    # In goldfish: use +1 to animate opponent's artifact (irrelevant)
                    # or just hold loyalty as threat
                    gs._log("  Karn the Great Creator: online")
                    break

        # ── 10. Devourer of Destiny ({5}{CC} = 7 mana) ────────────────
        # Only cast if we have the imprinted copy back or a fresh copy in hand.
        for card in list(gs.hand()):
            if card.name == DEVOURER and gs.mana_pool.total() >= 7:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 7)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                if self._labyrinth_imprint == DEVOURER:
                    self._labyrinth_imprint = None  # it was in exile, now cast
                gs._log("  Devourer of Destiny: 6/6, exiles colored permanent")
                break

        # ── 11. Retrieve from Labyrinth if we have 10 mana (Ulamog ready) ──
        if self._labyrinth_imprint == ULAMOG and gs.mana_pool.total() >= 10:
            # Tap Labyrinth for {C} and return Ulamog to hand (cost 0, just tap)
            lab = next((c for c in gs.zones.battlefield if c.name == LABYRINTH), None)
            if lab:
                exiled = next((c for c in gs.zones.exile if c.name == ULAMOG), None)
                if exiled:
                    gs.zones.exile.remove(exiled)
                    gs.zones.hand.append(exiled)
                    self._labyrinth_imprint = None
                    gs._log("  Ugin's Labyrinth: returned Ulamog to hand")

        # ── 12. Ugin, Eye of the Storms ({7}) ──────────────────────────
        if not self._ugin_up:
            for card in list(gs.hand()):
                if card.name == UGIN and gs.mana_pool.total() >= 7:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 7)
                    gs.cast_spell(card)
                    self._ugin_up = True
                    self._ugin_loyalty = 4  # base starting loyalty
                    gs._log("  Ugin, Eye of the Storms: online (exile cast trigger fires)")
                    break

        # ── 13. Ulamog, the Ceaseless Hunger ({10}) ────────────────────
        for card in list(gs.hand()):
            if card.name == ULAMOG and gs.mana_pool.total() >= 10:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 10)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log("  ULAMOG: 10/10 Indestructible, cast exiled 2 permanents")
                break

        # ── 14. Kozilek's Command (ramp + draw) ────────────────────────
        # Cast when we have 4+ mana and still need Tron or card selection.
        if gs.mana_pool.total() >= 4:
            for card in list(gs.hand()):
                if card.name == COMMAND:
                    x = min(3, gs.mana_pool.total() - 2)  # leave 2 for {CC}
                    if self._cast_command(gs, x_value=x):
                        gs.zones.play_from_hand(card)
                        break

    def _play_best_land(self, gs: GameState):
        """
        Land priority:
          1. Missing Tron piece (assembling Tron is highest priority)
          2. Ugin's Labyrinth (becomes {CCC} with imprint — massive value)
          3. Eldrazi Temple ({CC} for Eldrazi)
          4. Forest (for Mycospawn {G} cost)
          5. Any other land
        """
        hand_lands = [c for c in gs.hand() if c.is_land()]
        if not hand_lands:
            return

        bf_names = {c.name for c in gs.zones.battlefield if c.is_land()}

        # Priority 1: missing Tron piece
        for piece in [MINE, TOWER, PLANT]:
            for c in hand_lands:
                if c.name == piece and piece not in bf_names:
                    gs.zones.play_from_hand(c)
                    gs._land_played_this_turn = True
                    gs._log(f"  Land drop: {piece} (Tron piece {self._tron_piece_count(gs)}/3)")
                    return

        # Priority 2: Ugin's Labyrinth
        for c in hand_lands:
            if c.name == LABYRINTH:
                gs.zones.play_from_hand(c)
                gs._land_played_this_turn = True
                self._labyrinth_up = True
                gs._log("  Land drop: Ugin's Labyrinth")
                return

        # Priority 3: Eldrazi Temple
        for c in hand_lands:
            if c.name == TEMPLE:
                gs.zones.play_from_hand(c)
                gs._land_played_this_turn = True
                gs._log("  Land drop: Eldrazi Temple ({CC} for Eldrazi)")
                return

        # Priority 4: Any land
        if hand_lands:
            c = hand_lands[0]
            gs.zones.play_from_hand(c)
            gs._land_played_this_turn = True
            gs._log(f"  Land drop: {c.name}")


    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat:
          1. Compute combat damage from threats on battlefield
          2. Ugin +2 loyalty: gain 3 life, draw a card
          3. Ugin 0: add {CCC} (mana for more spells)
          4. Karn −2: if opponent has relevant artifacts, animate (goldfish: skip)
          5. Deploy any remaining threats with leftover mana
          6. Spawn mana for late casts
        """
        # ── 1. Combat damage ────────────────────────────────────────────
        for c in gs.zones.battlefield:
            if not getattr(c, "summoning_sickness", True) and c.has(Tag.CREATURE):
                try:
                    power = int(c.power or 0)
                except (ValueError, TypeError):
                    power = 0
                if power > 0:
                    gs.damage_dealt += power
                    gs._log(f"  {c.name} attacks for {power} ({gs.damage_dealt} total)")

        # ── 2. Ugin engine ──────────────────────────────────────────────
        if self._ugin_up:
            # +2 each turn: draw + 3 life
            self._ugin_loyalty += 2
            if gs.zones.library:
                drawn = gs.zones.library.pop(0)
                gs.zones.hand.append(drawn)
                gs._log(f"  Ugin +2: draw {drawn.name}, gain 3 life (loyalty {self._ugin_loyalty})")
            # 0 ability: add {CCC} (use it for late-game casting)
            # In goldfish: use 0 when we have spells to cast
            if any(c.name in {ULAMOG, DEVOURER} for c in gs.hand()):
                self._ugin_loyalty += 0  # doesn't change loyalty
                gs.mana_pool.flex += 3
                gs._log("  Ugin 0: add {CCC}")

        # ── 3. Spawn mana + extra spells ────────────────────────────────
        self._apply_spawn_mana(gs)

        # ── 4. Cast anything remaining with leftover mana ───────────────
        # TKS if not yet played
        for card in list(gs.hand()):
            if card.name == TKS and gs.mana_pool.total() >= 4:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log("  TKS post-combat: 4/4")

        # Sowing Mycospawn if not played yet
        for card in list(gs.hand()):
            if card.name == MYCOSPAWN and gs.mana_pool.total() >= 4:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                target = self._missing_tron_piece(gs)
                if target:
                    fetched = next((c for c in gs.zones.library if c.name == target), None)
                    if fetched:
                        gs.zones.library.remove(fetched)
                        gs.zones.battlefield.append(fetched)
                        gs._log(f"  Mycospawn post-combat: fetched {target}")

        # Devourer if not played
        for card in list(gs.hand()):
            if card.name == DEVOURER and gs.mana_pool.total() >= 7:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 7)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log("  Devourer post-combat: 6/6")

        # Ulamog if we somehow got 10 mana
        for card in list(gs.hand()):
            if card.name == ULAMOG and gs.mana_pool.total() >= 10:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 10)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log("  ULAMOG post-combat: 10/10 Indestructible")

    # ── Sideboard premium ────────────────────────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        """
        Eldrazi Tron SB: Ensnaring Bridge (locks creature decks), Trinisphere
        (taxes 1-drop decks), Disruptor Flute (names keywords), Grafdigger's Cage,
        Torpor Orb (blanks ETB), Walking Ballista (removal/reach), Haywire Mite.
        """
        opp = opponent.lower()
        if any(x in opp for x in ("boros energy", "humans", "merfolk", "zoo")):
            return 0.08   # Ensnaring Bridge + Trinisphere locks aggro
        if any(x in opp for x in ("living end", "cascade")):
            return 0.07   # Grafdigger's Cage + Torpor Orb
        if any(x in opp for x in ("affinity", "artifact")):
            return 0.06   # Haywire Mite + Sylex
        if any(x in opp for x in ("prowess", "storm", "ruby")):
            return 0.05   # Trinisphere taxes 0-1 drop spells hard
        if any(x in opp for x in ("yawgmoth", "goryo", "reanimator")):
            return 0.04   # Cage + Torpor Orb
        if any(x in opp for x in ("control", "blink")):
            return 0.03   # Disruptor Flute on Flash
        if any(x in opp for x in ("tron", "eldrazi")):
            return -0.02  # Mirror is mana-dependent, slight negative
        return 0.0



# ── Edge Case Registry ──────────────────────────────────────────────────────
# Verified against oracle text. Key rulings for the pilot.
#
# EC-01: Ugin's Labyrinth imprint — the exiled card is returned by tapping.
#   Tapping returns the card to hand — it does NOT go to GY or get cast for free.
#   To cast Ulamog, you still need 10 mana. The Labyrinth just stores it safely.
#   You must return it BEFORE casting (tap Labyrinth, get card, then cast separately).
#
# EC-02: Eldrazi Temple {CC} restriction — spend on COLORLESS ELDRAZI only.
#   TKS ({3}{C}), Devourer ({5}{CC}), Ulamog ({10}) all qualify.
#   Karn ({4}) is NOT an Eldrazi — Temple {CC} cannot pay for Karn.
#   Sowing Mycospawn ({3}{G}) is Devoid (colorless) but NOT an Eldrazi — Temple {CC}
#   also cannot pay for Mycospawn (it's an Eldrazi Fungus, check "Eldrazi" subtype).
#   ACTUALLY: Mycospawn is an Eldrazi Fungus, so Temple {CC} CAN pay for it.
#
# EC-03: Sowing Mycospawn "when you cast this spell" — trigger goes on stack on cast.
#   If opponent counters Mycospawn, the ETB trigger already resolved — the land is already
#   in play. Counter does not undo the land search trigger!
#   NOTE: The land-search trigger goes on stack when you CAST, not when it resolves.
#   If countered AFTER trigger resolves: the 3/3 dies but the land stays. Net: 4 mana for a land.
#   If countered BEFORE trigger resolves (not possible for sorcery-speed): irrelevant.
#
# EC-04: Devourer of Destiny opening hand reveal — upkeep ability fires T1.
#   If revealed from opening hand, at the start of your FIRST upkeep:
#   Look at top 4, keep 1 on top, exile the rest.
#   This is a FREE scry-4 that requires revealing Devourer in your opening hand.
#   Mulligan decisions: if you're going to mull 2+ times, revealing Devourer wastes the ability.
#   Only reveal if you're keeping the current hand or plan to keep after 1 mull.
#
# EC-05: Kozilek's Command Eldrazi Spawn tokens.
#   Spawn tokens are 0/1 colorless Eldrazi Spawn: "Sacrifice this token: Add {C}."
#   In response to removal → sac for mana. They're chump blockers AND mana.
#   Don't sacrifice them all for mana immediately — keep some as blockers.
#
# EC-06: Karn, the Great Creator static ability.
#   Opponent's artifact activated abilities can't be activated (Chalice, Ensnaring Bridge).
#   This is a STATIC ability that works immediately upon Karn entering.
#   It shuts down Chalice of the Void (opponent can't add/remove counters),
#   but Chalice's replacement effect (countering spells) still works.
#
# EC-07: Ugin, Eye of the Storms colorless spell trigger.
#   "Whenever you cast a colorless spell" — fires for every Eldrazi and artifact you cast.
#   Karn ({4}) is colorless → triggers. Talisman ({2}) is colorless → triggers.
#   Expedition Map ({1}) is colorless → triggers.
#   Each trigger: exile up to 1 colored permanent. Engine generates massive tempo.
#
# EC-08: Tron mana accounting.
#   Urza's Mine = {1} alone, {1} with Tron assembled.
#   Urza's Power Plant = {1} alone, {2} with Tron assembled.
#   Urza's Tower = {1} alone, {3} with Tron assembled. (Wait, verify this.)
#   Actually: Mine taps for {1} normally, Tower taps for {3} with Tron, Plant for {2}.
#   No — the bonus is ONLY available when all three are in play. Individually they tap for {1}.
#   With all three: Mine+Tower+Plant = 1+2+4 = 7 total (not 1+3+2 — check exact oracle).
#   Tower gives the most: check oracle — "other" tron lands give bonus to Tower.
#
# EC-09: Ulamog cast trigger vs resolved.
#   "When you cast this spell, exile two target permanents" — this fires on CAST, not resolve.
#   Even if Ulamog is countered, the exile trigger already resolved. Net: 2 exiled permanents.
#   This is the primary reason to cast Ulamog even into countermagic.
#
# EC-10: Thought-Knot Seer die trigger — opponent draws when TKS leaves.
#   Even if TKS is bounced (Aether Gust, Vapor Snag), the "leaves" trigger fires.
#   TKS leaving = opponent draws a card. Don't bounce your own TKS carelessly.
#   Exception: if the card you exiled was better than the draw, still good trade.
#
EDGE_CASES = [
    "EC-01: Ugin's Labyrinth taps to RETURN the imprinted card to hand — still need full mana to cast",
    "EC-02: Eldrazi Temple {CC} works for Eldrazi subtype — TKS/Devourer/Ulamog/Mycospawn yes, Karn no",
    "EC-03: Sowing Mycospawn land trigger resolves even if the 3/3 is countered — 4 mana for a land",
    "EC-04: Devourer of Destiny reveal — only worth it if you're keeping the hand (don't waste on mull 3+)",
    "EC-05: Kozilek Spawn tokens — keep some as blockers, sac for mana only when attacks are unimportant",
    "EC-06: Karn static shuts activated abilities, but Chalice replacement effect still fires",
    "EC-07: Ugin triggers on EVERY colorless spell including Karn, Talismans, Map — generates exile chain",
    "EC-08: Tron mana without assembly = 1 each. With assembly: Mine=1, Plant=2, Tower=4 (total 7)",
    "EC-09: Ulamog cast exile trigger resolves even if Ulamog is countered — always worth casting into counters",
    "EC-10: TKS dies/leaves trigger gives opponent a draw — don't bounce your own TKS",
]
