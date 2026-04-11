"""
neoform_combo.py — APL for Modern Neoform Combo (full rewrite, April 2026)

VERIFIED card interactions (CardDB, deck: neoform_modern.txt):

  Allosaurus Rider [{5}{G}{G}] — Elf Warrior. P/T = (1+lands)/(1+lands).
    Alt cost: exile 2 green cards from hand instead of paying {5}{G}{G}.
    CMC remains 7 regardless of how it was cast.
    In goldfish: always cast for free by pitching 2 green cards.
    Cards that can be pitched: Veil of Summer, Nourishing Shoal, Generous Ent,
    Pact of Negation (green card), Consign to Memory is BLUE — can't pitch.
    Hedge Maze is a land — can't pitch.

  Neoform [{G}{U}] — Sorcery.
    Additional cost: sacrifice a creature.
    Search for creature with MV exactly 1 + sacrificed creature's MV. Put into play with +1/+1 counter.
    Sac Rider (MV 7) → get MV 8 creature → Ghalta ({5}{G}{G}{G} = MV 8). ✓
    Also gets: Ureni (MV 8). Griselbrand (MV 8).

  Eldritch Evolution [{1}{G}{G}] — Sorcery.
    Additional cost: sacrifice a creature.
    Search for creature with MV ≤ X+2 where X = sacrificed creature's MV. Put into play. Exile Evolution.
    Sac Rider (MV 7) → get MV ≤ 9 → Ghalta (8) ✓, Ureni (8) ✓, Griselbrand (8) ✓.
    Sac Hooting Mandrills (MV 6 delve, but CMC is still 6) → get MV ≤ 8 → Ghalta ✓.
    IMPORTANT: Evolution exiles itself — only one use.

  Ghalta, Stampede Tyrant [{5}{G}{G}{G}] — 12/12 Trample.
    ETB: put any number of creature cards from hand onto battlefield.
    KEY: Dump Xenagos from hand → Xenagos gives Ghalta haste + doubles its power in combat.
    Also dumps: Atraxa (draws 10 cards), Griselbrand (draw 7).

  Xenagos, God of Revels [{3}{R}{G}] — Legendary Enchantment Creature, 6/5.
    Indestructible.
    At beginning of combat: target another creature gets haste + +X/+X where X = its power.
    With Ghalta (12 power): Ghalta gets haste + +12/+12 = 24/24 trample → 24 lethal. ✓
    NOTE: Xenagos enters on Ghalta's ETB (during main phase) then combat begins → trigger fires.

  Planar Genesis [{G}{U}] — Instant.
    Look at top 4 cards: may put a land onto battlefield tapped; OR put a card into hand.
    In goldfish: take the best card (Rider, Neoform, Evolution, Xenagos).
    Setup card — digs for missing combo pieces.

  Summoner's Pact [{0}] — Instant.
    Find green creature, put into hand. Next upkeep: pay {2}{G}{G} or lose.
    Gets Allosaurus Rider for free. Only use when winning this turn.

  Pact of Negation [{0}] — Instant.
    Counter target spell. Next upkeep: pay {3}{U}{U} or lose.
    Held as protection for the combo turn. Free counterspell.

  Consign to Memory [{U}] — Instant, Replicate {1}.
    Counter target triggered ability or colorless spell.
    KEY: Can counter opponent's Grief ETB trigger (exiling your Rider from hand).
    Dead in goldfish (no opponent).

  Veil of Summer [{G}] — Instant.
    Spells/abilities target only your stuff → hexproof until EOT.
    Counter the next blue/black spell targeting you this turn.
    Can be PITCHED to Rider as a green card (CMC 1).

  Nourishing Shoal [{X}{G}{G}] — Instant, Arcane.
    Alt cost: exile green card with MV X from hand.
    Gain X life. Dead in goldfish — but can be pitched to Rider for free.

  Generous Ent [{5}{G}] — 5/7 Reach. ETB: Food token.
    Forestcycling {1}: find a Forest card.
    In goldfish: cycle for a land if needed. Also pitchable to Rider.

  Hooting Mandrills [{5}{G}] — 4/4 Trample, Delve.
    With 5 cards in GY: costs {G}. MV still 6.
    Backup attacker if Ghalta plan fails.

  Griselbrand [{4}{B}{B}{B}{B}] — 7/7 Flying Lifelink.
    Pay 7 life → draw 7 cards. Can draw into second Rider/Evolution for a second combo.
    Reachable via Neoform (Rider → MV 8) or Evolution (Rider → MV ≤ 9).
    In some hands: get Griselbrand first → draw 7 → find Neoform + Xenagos → recombo.

  Ureni, the Song Unending [{5}{G}{U}{R}] — 10/10 Flying.
    ETB: deal X damage to creatures/planeswalkers where X = lands you control.
    Alternate finisher to Ghalta when Xenagos isn't needed.

  Hedge Maze [Land — Forest Island]:
    Enters tapped. ETB: surveil 1 (look at top, may put in GY).
    Fixes mana for {G}{U} (Neoform). Also digs for combo.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Constants ──────────────────────────────────────────────────────────────────
RIDER    = "Allosaurus Rider"
NEOFORM  = "Neoform"
EVOLVE   = "Eldritch Evolution"
PACT_G   = "Summoner's Pact"
PACT_NEG = "Pact of Negation"
GENESIS  = "Planar Genesis"
GHALTA   = "Ghalta, Stampede Tyrant"
XENAGOS  = "Xenagos, God of Revels"
ATRAXA   = "Atraxa, Grand Unifier"
GRISEL   = "Griselbrand"
URENI    = "Ureni, the Song Unending"
VEIL     = "Veil of Summer"
SHOAL    = "Nourishing Shoal"
ENT      = "Generous Ent"
MANDRILLS = "Hooting Mandrills"
CONSIGN  = "Consign to Memory"
HEDGE    = "Hedge Maze"

# Cards that can be pitched to Allosaurus Rider (green cards, not lands)
PITCHABLE_TO_RIDER = {VEIL, SHOAL, ENT, PACT_NEG, MANDRILLS, GENESIS}
# Evolution spells (the "sacrifice" step)
EVOLUTION_SPELLS = {NEOFORM, EVOLVE}
# Finishers reachable via Neoform/Evolution off Rider (MV 7 → 8)
FINISHERS_MV8 = {GHALTA, GRISEL, URENI}


class NeoformComboAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Neoform Combo (2026).

    The kill:
      1. Cast Allosaurus Rider for free (exile 2 green cards from hand).
      2. Cast Neoform or Eldritch Evolution, sacrificing Rider (MV 7).
      3. Fetch Ghalta, Stampede Tyrant (MV 8) → ETB dumps Xenagos from hand.
      4. Beginning of combat: Xenagos gives Ghalta haste + +12/+12.
      5. Ghalta attacks as 24/24 trample → 24 damage → win.

    Backup line: Rider → Griselbrand → draw 7 → find Neoform + second Rider → Ghalta.
    Fastest kill: T1 (on play, perfect hand).
    """

    name = "Neoform"
    win_condition_damage = 20
    max_turns = 8

    # ── Per-game state ─────────────────────────────────────────────────
    _combo_fired     = False
    _rider_in_play   = False
    _ghalta_in_play  = False
    _xenagos_in_play = False
    _pact_used       = False   # Summoner's Pact (pay {2}{G}{G} next upkeep)
    _grisel_in_play  = False

    def reset_game(self):
        self._combo_fired     = False
        self._rider_in_play   = False
        self._ghalta_in_play  = False
        self._xenagos_in_play = False
        self._pact_used       = False
        self._grisel_in_play  = False

    # ── Combo readiness checks ──────────────────────────────────────────
    def _has_rider(self, gs: GameState) -> bool:
        return any(c.name == RIDER for c in gs.hand())

    def _has_evolution_spell(self, gs: GameState) -> bool:
        return any(c.name in EVOLUTION_SPELLS for c in gs.hand())

    def _pitchable_cards(self, gs: GameState) -> list[Card]:
        """Green cards in hand that can be exiled to cast Rider for free."""
        return [c for c in gs.hand()
                if c.name in PITCHABLE_TO_RIDER or
                (not c.is_land() and "G" in (c.colors or []) and c.name != RIDER)]

    def _can_cast_rider_free(self, gs: GameState) -> bool:
        """Need 2 green non-land cards to exile for Rider's alt cost."""
        return len(self._pitchable_cards(gs)) >= 2

    def _can_neoform(self, gs: GameState) -> bool:
        """Neoform costs {G}{U} = needs 1 land producing G and 1 producing U."""
        total = gs.mana_pool.total()
        return total >= 2  # Simplified: {G}{U} = 2 mana with dual lands

    def _can_evolve(self, gs: GameState) -> bool:
        """Eldritch Evolution costs {1}{G}{G} = 3 mana."""
        return gs.mana_pool.total() >= 3

    def _has_xenagos(self, gs: GameState) -> bool:
        return any(c.name == XENAGOS for c in gs.hand())

    def _has_finisher_in_library(self, gs: GameState) -> bool:
        return any(c.name in FINISHERS_MV8 for c in gs.zones.library)

    def _has_finisher_in_hand(self, gs: GameState) -> bool:
        return any(c.name in FINISHERS_MV8 for c in gs.hand())

    def _combo_is_assembledable(self, gs: GameState) -> bool:
        """Can we execute the full combo this turn?"""
        has_rider_or_pact = self._has_rider(gs) or any(c.name == PACT_G for c in gs.hand())
        has_evo = self._has_evolution_spell(gs)
        has_pitch = self._can_cast_rider_free(gs)
        has_mana = gs.mana_pool.total() >= 2  # at least {G}{U} for Neoform
        has_finisher = self._has_finisher_in_library(gs) or self._has_finisher_in_hand(gs)
        return has_rider_or_pact and has_evo and has_pitch and has_mana and has_finisher

    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Neoform is a glass cannon. Keep requirements are strict:
          - T1 kill hand: land + Rider + 2 green pitchables + Neoform + Xenagos
          - T2 kill hand: land + Rider/Pact + 2 pitchables + Neoform + 1 protection
          - Marginal: any Rider + Neoform + 2 pitchables + 1 mana source
          - Never keep: 0 mana sources + no combo
        """
        if len(hand) <= 4:
            return True

        lands        = [c for c in hand if c.is_land()]
        has_rider    = any(c.name == RIDER for c in hand)
        has_pact_g   = any(c.name == PACT_G for c in hand)
        has_evo      = any(c.name in EVOLUTION_SPELLS for c in hand)
        pitchables   = [c for c in hand
                        if c.name in PITCHABLE_TO_RIDER or
                        (not c.is_land() and "G" in (c.colors or []) and
                         c.name not in {RIDER, GHALTA, XENAGOS, ATRAXA, GRISEL, URENI})]
        has_finisher = any(c.name in {GHALTA, XENAGOS, GRISEL} for c in hand)
        has_protection = any(c.name in {PACT_NEG, CONSIGN, VEIL} for c in hand)
        mana_sources = len(lands) + sum(1 for c in hand if c.name in PITCHABLE_TO_RIDER)

        # Must have some mana
        if not lands and not any(c.name == HEDGE for c in hand):
            if mana_sources < 2:
                return False

        # Perfect T1 hand
        if (has_rider and has_evo and len(pitchables) >= 2
                and lands and has_finisher):
            return True

        # T1/T2 hand with protection
        if (has_rider or has_pact_g) and has_evo and len(pitchables) >= 2 and lands:
            return True

        # Marginal: Pact for Rider + Neoform + 2 pitchables
        if has_pact_g and has_evo and len(pitchables) >= 2 and lands:
            return True

        # Risky: no Rider or Neoform but have Planar Genesis to dig
        has_genesis = any(c.name == GENESIS for c in hand)
        if has_genesis and (has_rider or has_evo) and lands and len(hand) <= 6:
            return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority:
          1. Extra lands past 1 (Neoform needs only 1 mana source)
          2. Duplicate finishers in hand (1 Xenagos is enough in hand; Ghalta stays in library)
          3. Consign to Memory (protection but can't pitch to Rider)
          4. Extra copies of same evolution spell
        """
        to_bottom: list[Card] = []
        lands = [c for c in hand if c.is_land()]

        # Keep 1 land (preferably dual for {G}{U})
        excess_lands = sorted(lands, key=lambda c: (
            0 if c.name in {HEDGE, "Breeding Pool"} else 1
        ))[1:]
        for c in excess_lands:
            if len(to_bottom) < n:
                to_bottom.append(c)

        # Keep 1 Xenagos in hand (dump to Ghalta ETB), bottom others
        xens = [c for c in hand if c.name == XENAGOS]
        for c in xens[1:]:
            if len(to_bottom) < n and c not in to_bottom:
                to_bottom.append(c)

        # Ghalta itself in hand is fine (Ghalta ETB dumps stuff; having Ghalta in hand means
        # we need Evolution to fetch something else — bottom it if we have no evo)
        ghaltas = [c for c in hand if c.name == GHALTA]
        if ghaltas and not any(c.name in EVOLUTION_SPELLS for c in hand):
            for c in ghaltas:
                if len(to_bottom) < n and c not in to_bottom:
                    to_bottom.append(c)

        # Consign to Memory (can't pitch to Rider, only useful for protection)
        for c in hand:
            if len(to_bottom) >= n:
                break
            if c.name == CONSIGN and c not in to_bottom:
                to_bottom.append(c)

        # High CMC non-combo cards
        rest = sorted(
            [c for c in hand if not c.is_land() and c not in to_bottom],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n:
                break
            if c.name not in {RIDER, NEOFORM, EVOLVE, XENAGOS, GHALTA, PACT_G}:
                to_bottom.append(c)

        return to_bottom[:n]


    # ── Core combo execution ────────────────────────────────────────────
    def _execute_combo(self, gs: GameState) -> bool:
        """
        Attempt to fire the full combo this turn.
        Returns True if combo succeeded (damage dealt ≥ 20).

        Steps:
          1. Get Rider into hand (Summoner's Pact if needed)
          2. Cast Rider for free (exile 2 green cards)
          3. Cast Neoform or Eldritch Evolution, sacrificing Rider
          4. Fetch Ghalta (MV 8) from library
          5. Ghalta ETB: dump Xenagos (and/or other creatures) from hand
          6. Beginning of combat: Xenagos triggers on Ghalta → haste + +12/+12
          7. Ghalta attacks for 24 trample → win
        """
        hand = gs.hand()

        # ── Step 1: Get Rider ──────────────────────────────────────────
        rider_card = next((c for c in hand if c.name == RIDER), None)
        if not rider_card:
            # Try Summoner's Pact (free, but risk upkeep payment)
            pact = next((c for c in hand if c.name == PACT_G), None)
            if pact:
                gs.cast_spell(pact)
                self._pact_used = True
                # Find Rider in library
                rider_in_lib = next((c for c in gs.zones.library if c.name == RIDER), None)
                if rider_in_lib:
                    gs.zones.library.remove(rider_in_lib)
                    gs.zones.hand.append(rider_in_lib)
                    rider_card = rider_in_lib
                    gs._log("  Summoner's Pact → Allosaurus Rider to hand")
                else:
                    return False
            else:
                return False

        # ── Step 2: Cast Rider for free (exile 2 green cards) ──────────
        pitchables = self._pitchable_cards(gs)
        if len(pitchables) < 2:
            return False

        pitch1, pitch2 = pitchables[0], pitchables[1]
        gs.zones.hand.remove(rider_card)
        if pitch1 in gs.zones.hand:
            gs.zones.hand.remove(pitch1)
            gs.zones.exile.append(pitch1)
        if pitch2 in gs.zones.hand:
            gs.zones.hand.remove(pitch2)
            gs.zones.exile.append(pitch2)
        gs.zones.battlefield.append(rider_card)
        rider_card.summoning_sickness = True
        rider_card.turn_entered = gs.turn
        self._rider_in_play = True
        gs._log(f"  Allosaurus Rider (free): pitched {pitch1.name}, {pitch2.name}")

        # ── Step 3: Find evolution spell ────────────────────────────────
        evo_card = next((c for c in gs.hand() if c.name in EVOLUTION_SPELLS), None)
        if not evo_card:
            return False

        # Check mana: Neoform = {G}{U}, Eldritch Evolution = {1}{G}{G}
        if evo_card.name == NEOFORM and gs.mana_pool.total() < 2:
            return False
        if evo_card.name == EVOLVE and gs.mana_pool.total() < 3:
            return False

        # Pay mana
        mana_cost = 2 if evo_card.name == NEOFORM else 3
        gs.mana_pool.flex = max(0, gs.mana_pool.flex - mana_cost)

        # Sacrifice Rider
        if rider_card in gs.zones.battlefield:
            gs.zones.battlefield.remove(rider_card)
            gs.zones.graveyard.append(rider_card)
        self._rider_in_play = False
        gs._log(f"  {evo_card.name}: sacrifice Rider (MV 7) → fetch MV {7+1 if evo_card.name==NEOFORM else '≤9'}")

        # Remove evolution spell
        if evo_card in gs.zones.hand:
            gs.zones.hand.remove(evo_card)
        if evo_card.name == EVOLVE:
            gs.zones.exile.append(evo_card)  # Evolution exiles itself
        else:
            gs.zones.graveyard.append(evo_card)

        # ── Step 4: Fetch Ghalta ────────────────────────────────────────
        # Priority: Ghalta > Griselbrand (draw 7) > Ureni
        for target_name in [GHALTA, GRISEL, URENI]:
            target = next((c for c in gs.zones.library if c.name == target_name), None)
            if target:
                gs.zones.library.remove(target)
                gs.zones.battlefield.append(target)
                target.summoning_sickness = True
                target.turn_entered = gs.turn
                gs._log(f"  {evo_card.name} → {target.name} into play")

                if target.name == GHALTA:
                    self._ghalta_in_play = True
                    # ── Step 5: Ghalta ETB — dump creatures from hand ──
                    creatures_in_hand = [c for c in gs.hand()
                                         if "creature" in c.type_line.lower()]
                    for creature in creatures_in_hand:
                        gs.zones.hand.remove(creature)
                        gs.zones.battlefield.append(creature)
                        creature.summoning_sickness = False  # dumped via Ghalta ETB (not summoning)
                        creature.turn_entered = gs.turn
                        gs._log(f"  Ghalta ETB: dumped {creature.name} onto battlefield")
                        if creature.name == XENAGOS:
                            self._xenagos_in_play = True

                    # ── Step 6: Xenagos beginning-of-combat trigger ───
                    if self._xenagos_in_play:
                        # Xenagos gives Ghalta haste + +12/+12 (X = Ghalta's power = 12)
                        ghalta_power = 12
                        ghalta_card = next(c for c in gs.zones.battlefield if c.name == GHALTA)
                        ghalta_card.summoning_sickness = False  # haste
                        ghalta_card.power = str(12 + ghalta_power)  # 24
                        ghalta_card.toughness = str(12 + ghalta_power)  # 24
                        gs._log(f"  Xenagos: Ghalta gets haste + +12/+12 = {ghalta_card.power}/{ghalta_card.toughness}")

                    # ── Step 7: Ghalta attacks ─────────────────────────
                    ghalta_on_bf = next(
                        (c for c in gs.zones.battlefield if c.name == GHALTA), None
                    )
                    if ghalta_on_bf and not ghalta_on_bf.summoning_sickness:
                        power = int(ghalta_on_bf.power or 12)
                        gs.damage_dealt += power
                        gs._log(f"  Ghalta attacks for {power} trample ({gs.damage_dealt} total)")
                        self._combo_fired = True
                        return True
                    elif self._xenagos_in_play:
                        # Haste was granted — can attack
                        power = int(ghalta_on_bf.power or 24) if ghalta_on_bf else 24
                        gs.damage_dealt += power
                        gs._log(f"  Ghalta (haste via Xenagos) attacks for {power} ({gs.damage_dealt} total)")
                        self._combo_fired = True
                        return True
                    else:
                        # No haste — Ghalta gets summoning sickness, deal 0 combat damage this turn
                        # But we still won if damage threshold was met via other creatures or next turn
                        gs._log("  Ghalta: no haste, will attack next turn")
                        return False

                elif target.name == GRISEL:
                    self._grisel_in_play = True
                    # Pay 7 life → draw 7 cards
                    gs.life = getattr(gs, 'life', 20) - 7
                    for _ in range(7):
                        if gs.zones.library:
                            gs.zones.hand.append(gs.zones.library.pop(0))
                    gs._log("  Griselbrand: pay 7 life → draw 7 cards")
                    # Try to recombo immediately with new hand
                    return self._execute_combo(gs)

                return False
        return False

    # ── Planar Genesis (setup/dig) ──────────────────────────────────────
    def _try_planar_genesis(self, gs: GameState):
        """
        Planar Genesis ({G}{U}): look at top 4, put a land into play tapped OR put a card into hand.
        In goldfish: always take the best card (Rider, Neoform, Xenagos).
        """
        for card in list(gs.hand()):
            if card.name == GENESIS and gs.mana_pool.total() >= 2:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                gs.zones.hand.remove(card)
                gs.zones.graveyard.append(card)  # it goes to GY after resolving

                revealed = []
                for _ in range(4):
                    if gs.zones.library:
                        revealed.append(gs.zones.library.pop(0))

                # Priority: Rider > Neoform > Evolve > Xenagos > land
                priority = [RIDER, NEOFORM, EVOLVE, PACT_G, XENAGOS, GHALTA, GRISEL, VEIL]
                kept = None
                for pname in priority:
                    kept = next((c for c in revealed if c.name == pname), None)
                    if kept:
                        break

                # Fallback: take the land for extra mana
                if kept is None:
                    kept = next((c for c in revealed if c.is_land()), None)
                    if kept:
                        revealed.remove(kept)
                        gs.zones.battlefield.append(kept)
                        gs.mana_pool.flex += 1
                        for r in revealed:
                            gs.zones.library.append(r)
                        gs._log(f"  Planar Genesis: put {kept.name} onto battlefield (land mode)")
                        return

                if kept:
                    revealed.remove(kept)
                    gs.zones.hand.append(kept)
                    gs._log(f"  Planar Genesis: took {kept.name} into hand")
                for r in revealed:
                    gs.zones.library.append(r)
                break


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat for a pure combo deck:
          1. Reset on T1
          2. Play land (1 land is usually all we need)
          3. Attempt full combo if we have all pieces
          4. If not: dig with Planar Genesis or Generous Ent cycle
          5. Deploy protection pieces (hold Pact of Negation for the combo turn)
        """
        if gs.turn == 1:
            self.reset_game()

        if self._combo_fired:
            return

        # ── 1. Land drop ────────────────────────────────────────────────
        # Prefer dual lands that make both {G} and {U} for Neoform
        if not gs.land_played:
            dual_priority = [HEDGE, "Breeding Pool", "Misty Rainforest",
                             "Flooded Strand", "Polluted Delta", "Windswept Heath"]
            placed = False
            for name in dual_priority:
                land = next((c for c in gs.hand() if c.name == name), None)
                if land:
                    gs.zones.play_from_hand(land)
                    gs.mana_pool.flex += 2  # dual lands give both colors
                    gs._log(f"  Land: {name}")
                    placed = True
                    break
            if not placed:
                for c in list(gs.hand()):
                    if c.is_land():
                        gs.zones.play_from_hand(c)
                        gs.mana_pool.flex += 1
                        gs._log(f"  Land: {c.name}")
                        break

        # ── 2. Attempt the combo ─────────────────────────────────────────
        if self._combo_is_assembledable(gs):
            self._execute_combo(gs)
            return

        # ── 3. Dig for missing pieces ───────────────────────────────────
        # Planar Genesis if Rider or Neoform missing
        if not self._has_rider(gs) and not any(c.name == PACT_G for c in gs.hand()):
            self._try_planar_genesis(gs)
        if not self._has_evolution_spell(gs):
            self._try_planar_genesis(gs)

        # Generous Ent forestcycle for a Forest (to fix mana)
        if gs.mana_pool.total() == 0:
            for c in list(gs.hand()):
                if c.name == ENT and gs.mana_pool.total() >= 1:
                    # Forestcycling: {1}, discard → get a Forest
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    forest = next((lib_c for lib_c in gs.zones.library
                                   if lib_c.name == "Forest"), None)
                    if forest:
                        gs.zones.library.remove(forest)
                        gs.zones.hand.append(forest)
                        gs._log("  Generous Ent: cycle → Forest to hand")
                    break

        # ── 4. Try combo again with new cards ──────────────────────────
        if self._combo_is_assembledable(gs):
            self._execute_combo(gs)

    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat. For a combo deck, most damage happens in step 3 (pre-combat execute_combo).
        But if Ghalta entered with summoning sickness (no Xenagos), it attacks now.
        Also: Griselbrand may attack for 7 lifelink.
        """
        if self._combo_fired:
            return

        # Ghalta or Griselbrand already in play from a prior turn — attack
        for c in gs.zones.battlefield:
            if c.name in {GHALTA, GRISEL} and not getattr(c, "summoning_sickness", True):
                try:
                    power = int(c.power or 0)
                except (ValueError, TypeError):
                    power = 12 if c.name == GHALTA else 7
                if power > 0:
                    # Check for Xenagos trigger (beginning of combat, already passed)
                    if c.name == GHALTA and self._xenagos_in_play:
                        power = power * 2  # Xenagos doubled it
                    gs.damage_dealt += power
                    gs._log(f"  {c.name} attacks for {power} ({gs.damage_dealt} total)")

        # Second attempt at combo if we drew into pieces post-combat
        if not self._combo_fired and self._combo_is_assembledable(gs):
            self._execute_combo(gs)

    # ── Sideboard premium ────────────────────────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        """
        Neoform SB: Mystical Dispute (counters blue interaction), Into the Flood Maw
        (bounces creatures attacking us), Nature's Claim (hits Leyline of the Void),
        Endurance (resets GY vs. exile), Elesh Norn (kills small creatures).
        """
        opp = opponent.lower()
        if any(x in opp for x in ("living end", "cascade")):
            return -0.08  # They can hate-race; Nature's Claim helps
        if any(x in opp for x in ("control", "blink")):
            return 0.04   # Mystical Dispute + Pact of Negation protects combo
        if any(x in opp for x in ("boros energy", "prowess", "affinity")):
            return -0.05  # Too fast; we die before T3
        if any(x in opp for x in ("yawgmoth", "reanimator")):
            return 0.05   # They combo slower; we're faster
        if any(x in opp for x in ("humans",)):
            return -0.03  # Meddling Mage naming Rider is brutal
        return 0.0



# ── Edge Case Registry ──────────────────────────────────────────────────────
#
# EC-01: Allosaurus Rider alt cost — exile from hand, not from anywhere.
#   "Exile two green cards from your hand" — must be in hand, not graveyard/library.
#   The exiled cards are gone permanently (no return trigger).
#   CMC of Rider remains 7 even when cast via alt cost — Neoform gets MV 8.
#
# EC-02: Neoform "exactly 1 plus" — not "up to." Rider = MV 7 → must get MV 8.
#   Ghalta ({5}{G}{G}{G}) = MV 8. Griselbrand ({4}{B}{B}{B}{B}) = MV 8. Ureni = MV 8. ✓
#   If opponent exiles your only MV-8 creatures from library → combo fizzles.
#   COUNTER: Eldritch Evolution has "up to" (MV ≤ 9) — more flexibility.
#
# EC-03: Ghalta ETB — "any number of creature cards from your hand."
#   This is a triggered ability that goes on the stack after Ghalta enters.
#   Opponent can respond before the ETB resolves — e.g., Bolt Ghalta in response.
#   If Ghalta dies before ETB resolves: the ETB still resolves but Ghalta isn't on BF.
#   You still dump creatures from hand even if Ghalta died.
#
# EC-04: Xenagos timing with Ghalta ETB.
#   Ghalta ETB resolves (main phase) → Xenagos enters battlefield via ETB.
#   Moving to combat step: "beginning of combat" trigger fires.
#   Xenagos says "at the beginning of combat on your turn" → trigger goes on stack.
#   Target Ghalta → give it haste + +12/+12. Ghalta can now attack this turn.
#   KEY TIMING: Xenagos must be on battlefield when beginning-of-combat step starts.
#   If Xenagos enters DURING combat (impossible here) → trigger wouldn't fire until next turn.
#
# EC-05: Griselbrand "pay 7 life" — activated ability, not triggered.
#   Can activate multiple times in one turn (as long as you have 7 life each time).
#   Pay 7 → draw 7. Pay 7 more → draw 7 more. Pay 7 more → draw 7 more. Total: 21 cards.
#   Starting life: 20. After 3 activations: 20 - 21 = -1 → you're dead.
#   Safe: 1 activation (13 life remaining), maybe 2 (6 life) if the second draw wins.
#
# EC-06: Pact of Negation upkeep — must pay {3}{U}{U} or lose.
#   In goldfish: irrelevant (no opponent spells to counter).
#   In match: only cast Pact on the combo turn when you're winning this turn.
#   If the combo fails and you cast Pact, you lose next upkeep.
#
# EC-07: Consign to Memory counters TRIGGERED ABILITIES or COLORLESS SPELLS.
#   NOT regular spells. Can counter: Grief ETB trigger (exiling Rider from hand),
#   Subtlety ETB trigger (bouncing Ghalta to library), Solitude ETB.
#   CANNOT counter: Force of Negation, Counterspell, other blue instants.
#   This is the primary protection against Elementals (Grief/Subtlety/Solitude).
#
# EC-08: Allosaurus Rider's power varies — pitchables must be green cards.
#   Consign to Memory is blue — can't pitch. Pact of Negation IS green ({0}).
#   Summoner's Pact is green. Veil of Summer is green. Nourishing Shoal is green.
#   Hooting Mandrills is green. Generous Ent is green.
#   Hedge Maze is a LAND — not pitchable. Breeding Pool is a LAND — not pitchable.
#
# EC-09: Eldritch Evolution exiles itself after resolving.
#   This is significant: can't be recurred from GY with Regrowth effects.
#   Also counts as "leaving the battlefield" — relevant for Omnath-style triggers.
#
# EC-10: Hooting Mandrills can be cast cheaply via Delve.
#   With 5 cards in GY (typical after Griselbrand draw): costs {G}.
#   MV is still 6 (delve doesn't reduce MV).
#   Can be sacced to Evolution → gets MV ≤ 8 creature (Ghalta ✓).
#   Alternative to Rider if Rider is exiled/countered.
#
EDGE_CASES = [
    "EC-01: Rider exile cost from HAND only — CMC remains 7 regardless of alt cost",
    "EC-02: Neoform is EXACTLY MV+1 (8 only) — Evolution is up to MV+2 (≤9, more flexible)",
    "EC-03: Ghalta ETB resolves even if Ghalta dies in response — creatures still dump from hand",
    "EC-04: Xenagos timing — enters via Ghalta ETB (main phase), triggers at beginning-of-combat (next step)",
    "EC-05: Griselbrand 7-life draws — max 2 activations safely at 20 starting life",
    "EC-06: Pact of Negation kills you next upkeep if combo fails — only cast on kill turn",
    "EC-07: Consign to Memory counters TRIGGERED ABILITIES only, not regular spells",
    "EC-08: Pitchable to Rider = green non-land cards. Consign (blue) and lands can't be pitched",
    "EC-09: Eldritch Evolution exiles itself — not recurrable from GY",
    "EC-10: Hooting Mandrills with Delve costs {G} and has MV 6 — can replace Rider in Evolution lines",
]
