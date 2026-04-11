"""
amulet_titan.py — APL for Modern Amulet Titan (full rewrite, April 2026)

VERIFIED card interactions (CardDB, deck: amulet_titan_modern.txt):

  Amulet of Vigor [{1}] — Artifact.
    Whenever a permanent you control enters tapped → untap it.
    KEY COMBO: Bounce land (Gruul Turf, Simic Growth Chamber) enters tapped →
    Amulet untaps it → tap it for {RG} or {GU} → bounce trigger returns a land to hand.
    Net: 2 mana from one land drop. With 2 Amulets: 2 untap triggers (still 2 mana,
    but the land untaps after each trigger, so it's tapped at the end from the tap).
    Actually with 2 Amulets: land enters tapped → trigger 1: untap → trigger 2: untap
    → land is untapped. Tap for mana. Bounce trigger returns a land to hand.
    Same net result: 2 mana from 1 land drop.

  Arboreal Grazer [{G}] — 0/3 Reach. ETB: put a land from hand onto battlefield tapped.
    With Amulet: land enters tapped → untaps → tap for mana.
    T1 line: Forest → Grazer (G mana) → ETB puts Gruul Turf tapped → Amulet untaps it
    → tap Turf for {RG} → bounce trigger bounces Forest to hand.
    Next turn: replay Forest, replay Grazer's land, Amulet untaps.

  Spelunking [{2}{G}] — Enchantment.
    ETB: draw a card, then may put a land from hand onto battlefield.
    STATIC: All lands you control enter untapped.
    KEY: This makes ALL land drops untap for free — bounce lands included.
    Bounce land enters → Spelunking makes it enter untapped (skip the "tapped" state)
    → tap for 2 mana → bounce trigger returns a land to hand.
    DOES NOT need Amulet when Spelunking is in play.

  Malevolent Rumble [{1}{G}] — Sorcery.
    Reveal top 4. Put 1 permanent card into hand. Rest to GY.
    Create 1 Eldrazi Spawn token (Sac: Add {C}).
    KEY: Digs for Amulet, Titan, or Spelunking. Spawn provides {C} mana buffer.

  Aftermath Analyst [{1}{G}] — Creature 1/3. ETB: mill 3.
    {3}{G}, Sacrifice: Return all land cards from your graveyard to battlefield tapped.
    With Amulet: all returned lands untap → massive mana burst.
    KEY LINE: Scapeshift fills GY with lands → Analyst sac returns them all → Amulet untaps all.

  Cultivator Colossus [{4}{G}{G}{G}] — *//* Trample.
    ETB: put a land from hand onto battlefield tapped, draw a card, repeat.
    With Amulet: each tapped land untaps → tap for mana → bounce trigger returns land to hand.
    If hand is full of lands: chain until hand has no lands. Can generate massive mana.

  Primeval Titan [{4}{G}{G}] — 6/6 Trample.
    ETB or attack: search for up to 2 land cards, put them onto battlefield tapped.
    With Amulet: each fetched land enters tapped → Amulet untaps → mana.
    Fetching 2 bounce lands with 1 Amulet = 4 extra mana + 2 bounce triggers.
    Fetching 2 bounce lands with 2 Amulets = 4 extra mana (same, just untaps twice each).
    ATTACK TRIGGER: T4 Titan attacks → 6 trample + fetch 2 more lands = huge acceleration.

  Gruul Turf / Simic Growth Chamber [Lands]:
    Enter tapped. When enters: return a land you control to hand. Tap for 2 mana ({RG}/{GU}).
    With Amulet or Spelunking: enter untapped → tap for 2 → bounce another land to hand.

  Lotus Field [Land]:
    Hexproof. Enters tapped. ETB: sacrifice 2 lands.
    Taps for 3 mana of any one color.
    With Spelunking: enters untapped. Net: lose 2 lands, gain {3} per turn.
    Without Spelunking/Amulet: expensive. Usually only in specific Scapeshift lines.

  Scapeshift [{2}{G}{G}] — Sorcery.
    Sacrifice any number of lands → search for up to that many lands, put them into play tapped.
    With Amulet: all new lands untap. Classic line: sac 6, fetch 6 bounce lands → 12 mana.
    With Aftermath Analyst in GY: sac lands, put them in GY, Analyst returns them.

  Summoner's Pact [{0}] — Instant.
    Search for green creature, put into hand. At next upkeep: pay {2}{G}{G} or lose.
    Gets Titan for free. Win that turn or you die.

  Green Sun's Zenith [{X}{G}]:
    Search for green creature with MV ≤ X, put into battlefield. Shuffles back in.
    X=0: gets Dryad Arbor (a Forest creature — free land drop that is a creature).
    X=1: gets Arboreal Grazer (extra land drop + ETB land).
    X=6: gets Primeval Titan (but costs 7 mana total).

  Urza's Cave [Land]:
    {T}: Add {C}.
    {3},{T}, Sacrifice: Search for a land, put into play tapped.
    Slower Expedition Map for any land.

  Echoing Deeps [Land — Cave]:
    May enter tapped as a copy of any land in any GY.
    Else {T}: Add {C}.
    Usually a Lotus Field copy or bounce land copy.

  Vexing Bauble [{1}] — Artifact.
    Whenever a player casts a spell, if no mana was spent → counter it.
    {1},{T}, Sacrifice: Draw a card.
    Mostly SB protection against free spells. Goldfish: sac for draw.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Card name constants ────────────────────────────────────────────────────────
TITAN       = "Primeval Titan"
AMULET      = "Amulet of Vigor"
GRAZER      = "Arboreal Grazer"
SPELUNKING  = "Spelunking"
RUMBLE      = "Malevolent Rumble"
ANALYST     = "Aftermath Analyst"
COLOSSUS    = "Cultivator Colossus"
ZENITH      = "Green Sun's Zenith"
PACT        = "Summoner's Pact"
SCAPESHIFT  = "Scapeshift"
LOTUS       = "Lotus Field"
GRUUL_TURF  = "Gruul Turf"
SIMIC_CHAMBER = "Simic Growth Chamber"
URZA_CAVE   = "Urza's Cave"
ECHOING     = "Echoing Deeps"
VEXING      = "Vexing Bauble"
DRYAD_ARBOR = "Dryad Arbor"
BOSEIJU     = "Boseiju, Who Endures"
HANWEIR     = "Hanweir Battlements"
MIRRORPOOL  = "Mirrorpool"
SAGA        = "Urza's Saga"

BOUNCE_LANDS = {GRUUL_TURF, SIMIC_CHAMBER}
RAMP_SPELLS  = {GRAZER, SPELUNKING, RUMBLE, ANALYST}
WIN_CONS     = {TITAN, ZENITH, PACT, SCAPESHIFT, COLOSSUS}


class AmuletTitanAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Amulet Titan (2026).

    Kill axes:
      A) T3 Titan via Amulet + bounce land mana engine (6 mana T3 on the play).
      B) Spelunking → all lands enter untapped → bounce lands generate 2 mana each.
      C) Scapeshift + Aftermath Analyst → burst mana from GY lands + Amulet.
      D) Green Sun's Zenith → Primeval Titan (X=6 for 7 mana total).

    Core mechanic:
      Amulet of Vigor + bounce land = 2 mana from 1 land drop.
      Spelunking replaces Amulet for lands (static "lands enter untapped").
      Primeval Titan ETB/attack fetches bounce lands → more Amulet triggers → avalanche.

    Typical kill: T3 with perfect Amulet draw, T4–5 otherwise.
    """

    name = "Amulet Titan"
    win_condition_damage = 20
    max_turns = 12

    # ── Per-game state ─────────────────────────────────────────────────
    _amulet_count       = 0     # Amulets on battlefield
    _spelunking_up      = False # Spelunking in play (lands enter untapped)
    _titan_up           = False # Primeval Titan on battlefield
    _titan_attacked     = False # Titan attack trigger used this turn
    _analyst_up         = False # Aftermath Analyst on battlefield
    _spawn_count        = 0     # Eldrazi Spawn from Rumble
    _lands_in_gy        = 0     # Land count in GY (for Analyst + Scapeshift)
    _pact_in_flight     = False # Summoner's Pact used (must pay next upkeep)

    def reset_game(self):
        self._amulet_count   = 0
        self._spelunking_up  = False
        self._titan_up       = False
        self._titan_attacked = False
        self._analyst_up     = False
        self._spawn_count    = 0
        self._lands_in_gy    = 0
        self._pact_in_flight = False

    # ── Core helpers ────────────────────────────────────────────────────
    def _untaps_on_entry(self) -> bool:
        """True if a tapped land would immediately untap (Amulet or Spelunking)."""
        return self._amulet_count > 0 or self._spelunking_up

    def _bounce_land_mana(self, gs: GameState) -> int:
        """
        Mana generated by playing a bounce land with Amulet/Spelunking active.
        If untaps on entry: enter → untap → tap for 2 → bounce a land to hand.
        Return 2 (net mana from the land drop itself).
        """
        return 2 if self._untaps_on_entry() else 0

    def _count_bounce_lands_in_play(self, gs: GameState) -> int:
        return sum(1 for c in gs.zones.battlefield if c.name in BOUNCE_LANDS)

    def _count_bounce_lands_in_hand(self, gs: GameState) -> int:
        return sum(1 for c in gs.hand() if c.name in BOUNCE_LANDS)

    def _total_lands_in_play(self, gs: GameState) -> int:
        return sum(1 for c in gs.zones.battlefield if c.is_land())

    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Amulet Titan keep criteria:
          - The deck is a combo deck — needs either the combo piece (Amulet) or
            the ramp to assemble it (Grazer, Spelunking, Rumble) plus a payoff.
          - Perfect keeps: Amulet + bounce land + any land + payoff.
          - Acceptable: 2 lands + ramp + payoff (find Amulet via Rumble).
          - Mull: 0 lands, or 5+ lands (flood), or no payoff with 3 mulls.
        """
        if len(hand) <= 4:
            return True

        lands    = [c for c in hand if c.is_land()]
        amulets  = [c for c in hand if c.name == AMULET]
        bounce   = [c for c in hand if c.name in BOUNCE_LANDS]
        ramp     = [c for c in hand if c.name in RAMP_SPELLS]
        payoffs  = [c for c in hand if c.name in WIN_CONS]
        spelunk  = any(c.name == SPELUNKING for c in hand)

        # Hard mulls
        if not lands:
            return False
        if len(lands) >= 5:
            return False

        # Ideal combo hand: Amulet + bounce land + payoff
        if amulets and bounce and payoffs and len(lands) >= 2:
            return True

        # Spelunking hand: replaces Amulet, all lands untap
        if spelunk and len(lands) >= 2 and payoffs:
            return True

        # Amulet + ramp + any land: can find bounce land by T2
        if amulets and ramp and len(lands) >= 1 and payoffs:
            return True

        # Two lands + ramp + payoff: can find Amulet through Rumble
        if len(lands) >= 2 and ramp and payoffs and mulligans <= 1:
            return True

        # Three lands + payoff: brute force keep
        if len(lands) >= 2 and payoffs and len(hand) <= 6:
            return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority:
          1. Excess bounce lands past 1 in hand (they cycle anyway, 1 is enough to start)
          2. Excess non-bounce lands past 2
          3. Duplicate Amulets (1 is enough to combo, 2nd is redundant early)
          4. High CMC without enough mana to cast (Colossus, Titan in pure ramp draws)
          5. Summoner's Pact (risky early, bottom in most cases)
        """
        to_bottom: list[Card] = []
        bounce = [c for c in hand if c.name in BOUNCE_LANDS]
        other_lands = [c for c in hand if c.is_land() and c.name not in BOUNCE_LANDS]
        amulets = [c for c in hand if c.name == AMULET]

        # Keep 1 bounce land, bottom the rest
        for c in bounce[1:]:
            if len(to_bottom) < n:
                to_bottom.append(c)

        # Keep 2 non-bounce lands max
        for c in other_lands[2:]:
            if len(to_bottom) < n:
                to_bottom.append(c)

        # Keep 1 Amulet
        for c in amulets[1:]:
            if len(to_bottom) < n and c not in to_bottom:
                to_bottom.append(c)

        # Bottom Pact (dangerous without enough mana to pay)
        for c in hand:
            if len(to_bottom) >= n:
                break
            if c.name == PACT and c not in to_bottom:
                to_bottom.append(c)

        # Bottom high CMC that we can't cast soon
        rest = sorted(
            [c for c in hand if c not in to_bottom and not c.is_land()],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n:
                break
            to_bottom.append(c)

        return to_bottom[:n]


    # ── Bounce land mana engine ─────────────────────────────────────────
    def _play_bounce_land(self, card: Card, gs: GameState):
        """
        Play a bounce land. With Amulet/Spelunking: generates 2 mana + bounces a land.
        Without: enters tapped, generates nothing this turn, bounces a land.
        """
        # Find a non-bounce land to return to hand (keep bounce lands in play)
        non_bounce = next(
            (c for c in gs.zones.battlefield
             if c.is_land() and c.name not in BOUNCE_LANDS),
            None
        )
        if non_bounce is None:
            # Only bounce lands in play — must return one (return lowest value)
            non_bounce = next(
                (c for c in gs.zones.battlefield if c.is_land()), None
            )

        # Play the bounce land
        gs.zones.hand.remove(card)
        gs.zones.battlefield.append(card)
        card.summoning_sickness = False
        card.turn_entered = gs.turn

        # Bounce trigger: return chosen land to hand
        if non_bounce:
            gs.zones.battlefield.remove(non_bounce)
            gs.zones.hand.append(non_bounce)
            gs._log(f"  {card.name}: bounced {non_bounce.name} to hand")

        # Amulet / Spelunking: land enters "untapped" effectively
        if self._untaps_on_entry():
            # Tap for mana immediately
            gs.mana_pool.flex += 2
            gs._log(f"  {card.name}: Amulet/Spelunking → +2 mana (total amulets: {self._amulet_count})")
        else:
            gs._log(f"  {card.name}: entered tapped (no Amulet/Spelunking)")

        gs.land_played = True

    # ── Amulet deployment ───────────────────────────────────────────────
    def _try_cast_amulet(self, gs: GameState):
        """Cast Amulet of Vigor if available. Multiple copies stack."""
        for card in list(gs.hand()):
            if card.name == AMULET and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                self._amulet_count += 1
                gs._log(f"  Amulet of Vigor #{self._amulet_count}: all tapped permanents untap on entry")
                # Re-cast if more copies
                break

    # ── Ramp package ────────────────────────────────────────────────────
    def _try_arboreal_grazer(self, gs: GameState):
        """
        Arboreal Grazer ({G}): 0/3, ETB put a land from hand into play tapped.
        With Amulet: the tapped land untaps → extra mana this turn.
        Priority: put a bounce land into play for the 2-mana engine.
        """
        for card in list(gs.hand()):
            if card.name != GRAZER:
                continue
            if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                continue
            gs.cast_spell(card)
            card.summoning_sickness = True
            card.turn_entered = gs.turn

            # ETB: put a land from hand onto battlefield tapped
            # Priority: bounce land > other land
            land_targets = sorted(
                [c for c in gs.hand() if c.is_land()],
                key=lambda c: (0 if c.name in BOUNCE_LANDS else 1)
            )
            if land_targets:
                target = land_targets[0]
                if target.name in BOUNCE_LANDS:
                    self._play_bounce_land(target, gs)
                else:
                    gs.zones.hand.remove(target)
                    gs.zones.battlefield.append(target)
                    target.turn_entered = gs.turn
                    if self._untaps_on_entry():
                        gs.mana_pool.flex += 1  # untapped by Amulet
                        gs._log(f"  Grazer ETB: {target.name} enters, Amulet untaps → +1 mana")
                    else:
                        gs._log(f"  Grazer ETB: {target.name} enters tapped")
                    gs.land_played = True
            break

    def _try_spelunking(self, gs: GameState):
        """
        Spelunking ({2}{G}): enchantment. ETB: draw + may put land from hand onto battlefield.
        Static: lands you control enter untapped.
        Cast ASAP — completely transforms the mana engine.
        """
        if self._spelunking_up:
            return
        for card in list(gs.hand()):
            if card.name == SPELUNKING and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                self._spelunking_up = True
                gs._log("  Spelunking: all lands now enter untapped!")

                # ETB: draw a card
                if gs.zones.library:
                    drawn = gs.zones.library.pop(0)
                    gs.zones.hand.append(drawn)
                    gs._log(f"  Spelunking ETB: drew {drawn.name}")

                # ETB: may put a land from hand onto battlefield
                land_targets = sorted(
                    [c for c in gs.hand() if c.is_land()],
                    key=lambda c: (0 if c.name in BOUNCE_LANDS else 1)
                )
                if land_targets and not gs.land_played:
                    target = land_targets[0]
                    if target.name in BOUNCE_LANDS:
                        self._play_bounce_land(target, gs)
                    else:
                        gs.zones.hand.remove(target)
                        gs.zones.battlefield.append(target)
                        target.turn_entered = gs.turn
                        gs.mana_pool.flex += 1  # Spelunking: enters untapped
                        gs.land_played = True
                break

    def _try_rumble(self, gs: GameState):
        """
        Malevolent Rumble ({1}{G}): reveal top 4, keep 1 permanent, rest to GY.
        Creates 1 Eldrazi Spawn token (Sac: Add {C}).
        Priority: keep Amulet > keep Titan > keep Spelunking > keep best spell.
        """
        for card in list(gs.hand()):
            if card.name == RUMBLE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Reveal top 4 → keep the best
                revealed = []
                for _ in range(4):
                    if gs.zones.library:
                        revealed.append(gs.zones.library.pop(0))
                if revealed:
                    # Priority order for keeping
                    priority = [AMULET, TITAN, SPELUNKING, ZENITH, PACT, SCAPESHIFT, COLOSSUS, ANALYST]
                    kept = None
                    for pname in priority:
                        kept = next((c for c in revealed if c.name == pname), None)
                        if kept:
                            break
                    if kept is None:
                        # Keep highest CMC permanent
                        permanents = [c for c in revealed if "land" in c.type_line.lower()
                                      or "creature" in c.type_line.lower()
                                      or "artifact" in c.type_line.lower()
                                      or "enchantment" in c.type_line.lower()
                                      or "planeswalker" in c.type_line.lower()]
                        kept = max(permanents, key=lambda c: c.cmc) if permanents else None
                        if kept is None:
                            kept = revealed[0]  # keep anything
                    gs.zones.hand.append(kept)
                    revealed.remove(kept)
                    for c in revealed:
                        gs.zones.graveyard.append(c)
                        if c.is_land():
                            self._lands_in_gy += 1
                    gs._log(f"  Malevolent Rumble: kept {kept.name}, {len(revealed)} to GY")
                # Create Eldrazi Spawn
                self._spawn_count += 1
                gs._log("  Malevolent Rumble: +1 Eldrazi Spawn ({C} on demand)")
                break


    # ── Win condition casts ─────────────────────────────────────────────
    def _try_primeval_titan(self, gs: GameState):
        """
        Primeval Titan ({4}{G}{G} = 6 mana). 6/6 Trample.
        ETB: search for 2 lands → put into play tapped → Amulet untaps them.
        Fetch strategy: 2 bounce lands → 4 mana + 2 bounce triggers.
        """
        if self._titan_up:
            return
        for card in list(gs.hand()):
            if card.name == TITAN and gs.mana_pool.total() >= 6:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 6)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                self._titan_up = True

                # ETB: fetch 2 lands from library
                # Priority: bounce lands (for mana engine), then utility
                fetched = 0
                for target_name in [GRUUL_TURF, SIMIC_CHAMBER, GRUUL_TURF, SIMIC_CHAMBER]:
                    if fetched >= 2:
                        break
                    land = next((c for c in gs.zones.library if c.name == target_name), None)
                    if land:
                        gs.zones.library.remove(land)
                        # ETB tapped → Amulet untaps → 2 mana + bounce trigger
                        if self._untaps_on_entry():
                            # Bounce a non-bounce land back to hand
                            non_bounce = next(
                                (c for c in gs.zones.battlefield
                                 if c.is_land() and c.name not in BOUNCE_LANDS), None
                            )
                            if non_bounce:
                                gs.zones.battlefield.remove(non_bounce)
                                gs.zones.hand.append(non_bounce)
                            gs.zones.battlefield.append(land)
                            gs.mana_pool.flex += 2
                            gs._log(f"  Titan ETB: fetched {land.name}, Amulet +2 mana")
                        else:
                            gs.zones.battlefield.append(land)
                            gs._log(f"  Titan ETB: fetched {land.name} (enters tapped)")
                        land.turn_entered = gs.turn
                        fetched += 1

                # Titan is 6/6 trample — will deal damage in combat
                gs._log(f"  Primeval Titan: 6/6 trample in play, ETB fetched {fetched} lands")
                break

    def _try_summoners_pact(self, gs: GameState):
        """
        Summoner's Pact ({0}): free instant — find green creature, put in hand.
        Next upkeep: pay {2}{G}{G} or lose.
        In goldfish: use to get Titan for free when we have enough mana to win this turn.
        Only cast if we have 6+ mana to immediately cast Titan.
        """
        if self._pact_in_flight:
            return
        total = gs.mana_pool.total() + self._spawn_count
        if total < 6:
            return
        for card in list(gs.hand()):
            if card.name == PACT:
                gs.cast_spell(card)
                self._pact_in_flight = True
                # Find Titan and put in hand
                titan = next((c for c in gs.zones.library if c.name == TITAN), None)
                if titan:
                    gs.zones.library.remove(titan)
                    gs.zones.hand.append(titan)
                    gs._log("  Summoner's Pact: Titan found, added to hand")
                else:
                    # Find Cultivator Colossus
                    col = next((c for c in gs.zones.library if c.name == COLOSSUS), None)
                    if col:
                        gs.zones.library.remove(col)
                        gs.zones.hand.append(col)
                        gs._log("  Summoner's Pact: Cultivator Colossus found")
                break

    def _try_green_sun_zenith(self, gs: GameState):
        """
        Green Sun's Zenith ({X}{G}): put green creature with MV ≤ X into play. Shuffles back in.
        X=1: Arboreal Grazer (cost {1}{G} = 2 mana).
        X=6: Primeval Titan (cost {6}{G} = 7 mana — puts Titan directly into play!).
        """
        for card in list(gs.hand()):
            if card.name != ZENITH:
                continue
            total = gs.mana_pool.total() + self._spawn_count

            # Best use: get Titan directly into play (X=6, total cost 7)
            if total >= 7:
                self._apply_spawn_mana(gs)
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 7)
                gs.zones.hand.remove(card)  # Zenith shuffles itself back in
                gs.zones.library.append(card)

                titan = next((c for c in gs.zones.library if c.name == TITAN and c is not card), None)
                if titan:
                    gs.zones.library.remove(titan)
                    gs.zones.battlefield.append(titan)
                    titan.summoning_sickness = True
                    titan.turn_entered = gs.turn
                    self._titan_up = True
                    self._titan_etb(titan, gs)
                    gs._log("  Green Sun's Zenith X=6: Primeval Titan directly into play!")
                break

            # Alternative: X=1 for Grazer (2 mana)
            if total >= 2:
                self._apply_spawn_mana(gs)
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                gs.zones.hand.remove(card)
                gs.zones.library.append(card)

                grazer = next((c for c in gs.zones.library if c.name == GRAZER and c is not card), None)
                if grazer:
                    gs.zones.library.remove(grazer)
                    gs.zones.battlefield.append(grazer)
                    grazer.summoning_sickness = True
                    grazer.turn_entered = gs.turn
                    gs._log("  Green Sun's Zenith X=1: Arboreal Grazer into play")
                break

    def _titan_etb(self, card: Card, gs: GameState):
        """Shared Titan ETB logic — fetch 2 bounce lands."""
        fetched = 0
        for target_name in [GRUUL_TURF, SIMIC_CHAMBER, GRUUL_TURF, SIMIC_CHAMBER]:
            if fetched >= 2:
                break
            land = next((c for c in gs.zones.library if c.name == target_name), None)
            if land:
                gs.zones.library.remove(land)
                if self._untaps_on_entry():
                    non_bounce = next(
                        (c for c in gs.zones.battlefield
                         if c.is_land() and c.name not in BOUNCE_LANDS), None
                    )
                    if non_bounce:
                        gs.zones.battlefield.remove(non_bounce)
                        gs.zones.hand.append(non_bounce)
                    gs.zones.battlefield.append(land)
                    gs.mana_pool.flex += 2
                else:
                    gs.zones.battlefield.append(land)
                land.turn_entered = gs.turn
                fetched += 1
        return fetched

    def _apply_spawn_mana(self, gs: GameState):
        """Sac all Spawn tokens for mana."""
        if self._spawn_count > 0:
            gs.mana_pool.flex += self._spawn_count
            gs._log(f"  Sac {self._spawn_count} Spawn: +{self._spawn_count}C")
            self._spawn_count = 0

    def _try_scapeshift(self, gs: GameState):
        """
        Scapeshift ({2}{G}{G} = 4 mana): sac N lands → get N lands from library tapped.
        With Amulet: all enter tapped → untap → massive mana.
        Best line: have 4+ lands in play, Amulet active, sac all → fetch bounce lands.
        """
        for card in list(gs.hand()):
            if card.name != SCAPESHIFT:
                continue
            if gs.mana_pool.total() < 4:
                continue
            lands_in_play = [c for c in gs.zones.battlefield if c.is_land()]
            if len(lands_in_play) < 4:
                continue
            if not self._untaps_on_entry():
                continue  # Scapeshift without Amulet is too slow in goldfish

            gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
            n = len(lands_in_play)
            # Sacrifice all lands
            for land in lands_in_play:
                gs.zones.battlefield.remove(land)
                gs.zones.graveyard.append(land)
                self._lands_in_gy += 1

            # Fetch N bounce lands from library
            fetched_count = 0
            for _ in range(n):
                for target_name in [GRUUL_TURF, SIMIC_CHAMBER]:
                    land = next((c for c in gs.zones.library if c.name == target_name), None)
                    if land:
                        gs.zones.library.remove(land)
                        gs.zones.battlefield.append(land)
                        land.turn_entered = gs.turn
                        gs.mana_pool.flex += 2  # Amulet untaps each
                        fetched_count += 1
                        break
                else:
                    # Fallback: fetch any land
                    land = next((c for c in gs.zones.library if c.is_land()), None)
                    if land:
                        gs.zones.library.remove(land)
                        gs.zones.battlefield.append(land)
                        land.turn_entered = gs.turn
                        gs.mana_pool.flex += 1

            gs._log(f"  Scapeshift: sac {n} lands, fetched {fetched_count} bounce lands → Amulet burst")
            break


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat priority order:
          1. Reset on T1
          2. Land drop (bounce land > Forest > other)
          3. Amulet of Vigor (enables the mana engine)
          4. Arboreal Grazer (free land drop = another Amulet trigger)
          5. Malevolent Rumble (dig for Amulet/Titan, create Spawn)
          6. Spelunking (replaces Amulet for lands, draw+land ETB)
          7. Summoner's Pact (get Titan for free if 6+ mana available)
          8. Primeval Titan (the win condition)
          9. Green Sun's Zenith (Titan X=6 or Grazer X=1)
          10. Scapeshift (burst mana with Amulet, then Titan next turn)
          11. Aftermath Analyst (mill 3, set up late-game GY return)
        """
        if gs.turn == 1:
            self.reset_game()

        # ── 1. Land drop ────────────────────────────────────────────────
        if not gs.land_played:
            self._play_best_land(gs)

        # ── 2. Amulet of Vigor ─────────────────────────────────────────
        for _ in range(4):  # can have multiple copies
            self._try_cast_amulet(gs)
            if not any(c.name == AMULET for c in gs.hand()):
                break

        # ── 3. Arboreal Grazer (T1 mana accelerant) ────────────────────
        self._try_arboreal_grazer(gs)

        # ── 4. Malevolent Rumble (dig + Spawn) ─────────────────────────
        for card in list(gs.hand()):
            if card.name == RUMBLE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._try_rumble(gs)
                break

        # ── 5. Spelunking ───────────────────────────────────────────────
        self._try_spelunking(gs)

        # ── 6. Spawn mana for upcoming big spells ──────────────────────
        # Only sac Spawn if we need the mana to hit 6 for Titan
        total_with_spawn = gs.mana_pool.total() + self._spawn_count
        if total_with_spawn >= 6 and gs.mana_pool.total() < 6:
            self._apply_spawn_mana(gs)

        # ── 7. Summoner's Pact → free Titan ────────────────────────────
        self._try_summoners_pact(gs)

        # ── 8. Primeval Titan ───────────────────────────────────────────
        self._try_primeval_titan(gs)

        # ── 9. Green Sun's Zenith ───────────────────────────────────────
        if not self._titan_up:
            self._try_green_sun_zenith(gs)

        # ── 10. Scapeshift ──────────────────────────────────────────────
        if not self._titan_up:
            self._try_scapeshift(gs)

        # ── 11. Aftermath Analyst (mill 3 + future setup) ──────────────
        if not self._analyst_up:
            for card in list(gs.hand()):
                if card.name == ANALYST and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    card.summoning_sickness = True
                    card.turn_entered = gs.turn
                    self._analyst_up = True
                    # ETB: mill 3
                    for _ in range(3):
                        if gs.zones.library:
                            milled = gs.zones.library.pop(0)
                            gs.zones.graveyard.append(milled)
                            if milled.is_land():
                                self._lands_in_gy += 1
                    gs._log("  Aftermath Analyst: mill 3, ready for GY return combo")
                    break

        # ── 12. Vexing Bauble sac for draw ─────────────────────────────
        for card in list(gs.hand()):
            if card.name == VEXING and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Sac for draw immediately in goldfish
                if gs.mana_pool.total() >= 1:
                    gs.mana_pool.flex -= 1
                    gs.zones.battlefield.remove(
                        next(c for c in gs.zones.battlefield if c.name == VEXING)
                    )
                    if gs.zones.library:
                        gs.zones.hand.append(gs.zones.library.pop(0))
                    gs._log("  Vexing Bauble: sac for draw")
                break

    def _play_best_land(self, gs: GameState):
        """
        Land priority:
          1. Bounce land (if Amulet/Spelunking active — generates 2 mana)
          2. Forest (basic mana, enables Grazer on T1)
          3. Any other land
          4. If no land in hand: skip
        """
        hand_lands = [c for c in gs.hand() if c.is_land()]
        if not hand_lands:
            return

        # Priority 1: bounce land if engine is active
        if self._untaps_on_entry():
            for c in hand_lands:
                if c.name in BOUNCE_LANDS:
                    self._play_bounce_land(c, gs)
                    return

        # Priority 2: Forest / Gruul Turf (even without Amulet on T1)
        for c in hand_lands:
            if "Forest" in c.type_line or c.name == "Forest":
                gs.zones.play_from_hand(c)
                gs.land_played = True
                gs._log(f"  Land drop: {c.name}")
                return

        # Priority 3: any non-bounce land
        for c in hand_lands:
            if c.name not in BOUNCE_LANDS:
                gs.zones.play_from_hand(c)
                gs.land_played = True
                gs._log(f"  Land drop: {c.name}")
                return

        # Priority 4: bounce land without engine (enters tapped, bounces a land — risky)
        if hand_lands:
            c = hand_lands[0]
            gs.zones.play_from_hand(c)
            gs.land_played = True
            gs._log(f"  Land drop: {c.name} (tapped, no engine)")

    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat:
          1. Titan attack trigger: fetch 2 more lands → more Amulet mana
          2. Compute Titan trample damage
          3. Aftermath Analyst sac if enough GY lands
          4. Cast remaining ramp/threats with leftover mana
          5. Cultivator Colossus chain if available
        """
        # ── 1 & 2. Titan attacks ────────────────────────────────────────
        titans = [c for c in gs.zones.battlefield
                  if c.name == TITAN and not getattr(c, "summoning_sickness", True)]
        for titan in titans:
            # Attack for 6 trample
            gs.damage_dealt += 6
            gs._log(f"  Titan attacks: 6 trample damage ({gs.damage_dealt} total)")
            # Attack trigger: fetch 2 more bounce lands
            self._titan_etb(titan, gs)
            # Count all other creatures attacking
            for c in gs.zones.battlefield:
                if c is titan or c.is_land() or c.has(Tag.ARTIFACT):
                    continue
                if not getattr(c, "summoning_sickness", True):
                    try:
                        pw = int(c.power or 0)
                    except (ValueError, TypeError):
                        pw = 0
                    if pw > 0:
                        gs.damage_dealt += pw

        # ── 3. Aftermath Analyst sac for GY land return ─────────────────
        if self._analyst_up and self._lands_in_gy >= 4:
            analysts = [c for c in gs.zones.battlefield
                        if c.name == ANALYST and not getattr(c, "summoning_sickness", True)]
            if analysts and gs.mana_pool.total() >= 4:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 4)
                ana = analysts[0]
                gs.zones.battlefield.remove(ana)
                gs.zones.graveyard.append(ana)
                self._analyst_up = False
                # Return all land cards from GY to battlefield tapped → Amulet untaps
                returned = 0
                for c in list(gs.zones.graveyard):
                    if c.is_land():
                        gs.zones.graveyard.remove(c)
                        if self._amulet_count > 0:
                            gs.zones.battlefield.append(c)
                            gs.mana_pool.flex += 1  # untapped by Amulet
                            returned += 1
                self._lands_in_gy = 0
                gs._log(f"  Aftermath Analyst sac: returned {returned} lands (Amulet +{returned} mana)")

        # ── 4. Cultivator Colossus chain ────────────────────────────────
        for card in list(gs.hand()):
            if card.name == COLOSSUS and gs.mana_pool.total() >= 7:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 7)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                # ETB: put land from hand, draw, repeat
                chain = 0
                while True:
                    hand_lands = [c for c in gs.hand() if c.is_land()]
                    if not hand_lands:
                        break
                    land = sorted(hand_lands, key=lambda c: (0 if c.name in BOUNCE_LANDS else 1))[0]
                    if land.name in BOUNCE_LANDS:
                        self._play_bounce_land(land, gs)
                    else:
                        gs.zones.hand.remove(land)
                        gs.zones.battlefield.append(land)
                        land.turn_entered = gs.turn
                        if self._untaps_on_entry():
                            gs.mana_pool.flex += 1
                    if gs.zones.library:
                        gs.zones.hand.append(gs.zones.library.pop(0))
                    chain += 1
                    if chain > 20:  # safety limit
                        break
                gs._log(f"  Cultivator Colossus: ETB chain {chain} lands")
                break

        # ── 5. Cast spells with leftover mana ───────────────────────────
        self._apply_spawn_mana(gs)
        if not self._titan_up:
            self._try_primeval_titan(gs)
            self._try_green_sun_zenith(gs)

    # ── Sideboard premium ────────────────────────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        opp = opponent.lower()
        if any(x in opp for x in ("living end", "cascade")):
            return 0.06   # Bojuka Bog disrupts GY, Force of Vigor hits artifacts
        if any(x in opp for x in ("affinity", "artifact")):
            return 0.07   # Force of Vigor destroys artifacts free
        if any(x in opp for x in ("boros energy", "prowess")):
            return -0.03  # They're faster
        if any(x in opp for x in ("control", "blink")):
            return 0.04   # Trinisphere taxes interaction
        if any(x in opp for x in ("storm", "combo")):
            return 0.05   # Trinisphere shuts down cheap combo pieces
        return 0.0



# ── Edge Case Registry ──────────────────────────────────────────────────────
#
# EC-01: Amulet of Vigor triggers on the TAPPED state, not on ETB.
#   The untap trigger goes on the stack when the permanent ENTERS tapped.
#   With 2 Amulets: 2 untap triggers both go on the stack → both resolve → land is untapped.
#   Land is still untapped after both, same result as 1 Amulet. But each trigger is separate.
#
# EC-02: Spelunking static vs Amulet trigger — they stack differently.
#   Spelunking says "lands you control enter untapped" — this is a replacement effect,
#   not a triggered ability. It replaces "enters tapped" with "enters untapped".
#   Result: the land NEVER enters tapped. Amulet doesn't trigger (no tapped entry).
#   So with Spelunking active, Amulet triggers DON'T fire for lands.
#   You still get the 2-mana untapped entry from Spelunking, just not from Amulet stacking.
#
# EC-03: Arboreal Grazer ETB — the land enters as a SEPARATE event, not the Grazer's ETB.
#   Grazer's ETB puts the land into play (from your hand). That land enters tapped.
#   Amulet triggers from the land entering, not from Grazer's ETB.
#   You can hold priority after Grazer ETB goes on stack and respond before the land enters.
#
# EC-04: Primeval Titan ETB — "up to two land cards" means you can fetch 1 or 0.
#   The trigger puts them onto the battlefield TAPPED. Amulet untaps them.
#   With 2 bounce lands fetched and 1 Amulet: 4 mana + 2 bounce triggers.
#   Bounce triggers EACH return a land to hand — you choose which land for each.
#   You can return the same land twice (if it's not a bounce land itself).
#
# EC-05: Summoner's Pact upkeep cost — if you can't pay, you LOSE THE GAME.
#   "If you don't" means it's a delayed triggered ability. You can respond by winning first.
#   In goldfish model: always have the mana to pay OR win before next upkeep.
#   Never cast Pact if you can't pay {2}{G}{G} next turn AND can't win this turn.
#
# EC-06: Lotus Field self-sacrifice on ETB.
#   "When this land enters, sacrifice two lands" — mandatory triggered ability.
#   You can sacrifice other Lotus Fields (creates a loop in practice).
#   With Spelunking: Lotus Field enters untapped. You tap for 3 mana before the
#   sac trigger resolves? No — lands tap at sorcery speed. You can't tap in response
#   to the triggered sac since you don't have priority until the trigger resolves.
#   Actually: with Spelunking, Lotus enters untapped → you can tap it in response to
#   its own ETB trigger before the trigger resolves → get 3 mana, then sacrifice 2 lands.
#
# EC-07: Scapeshift — sacrificed lands go to GY, then fetched lands enter.
#   If Aftermath Analyst is in GY (from an earlier mill): fetch lands can include ones
#   you just sacrificed? No — they go to GY, then you search library for LIBRARY cards.
#   The sac'd lands are in GY, not library. Scapeshift + Analyst = two-step combo.
#
# EC-08: Cultivator Colossus chain — power/toughness is dynamic.
#   Colossus = number of lands you control. As you chain land drops during its ETB,
#   each land drop makes Colossus bigger. It also becomes harder to kill mid-chain.
#
# EC-09: Echoing Deeps copies "any land card in a graveyard."
#   It copies the card, not the permanent. If copying a bounce land: enters tapped,
#   bounce a land, tap for 2 — but Echoing Deeps is also a Cave (gets +4 life from Spelunking?
#   No — Spelunking gives +4 life only when you PUT a Cave onto the battlefield via Spelunking).
#
# EC-10: Green Sun's Zenith X=6 puts Titan directly into play.
#   "Put it onto the battlefield" — Titan's ETB triggers immediately.
#   This skips casting, so Summoner's Pact upkeep can't be "answered" — Zenith doesn't cast.
#   But you don't get the cast trigger on Pact either. Zenith directly triggers Titan ETB.
#
EDGE_CASES = [
    "EC-01: 2 Amulets = 2 untap triggers but same mana result — each trigger fires separately",
    "EC-02: Spelunking is a REPLACEMENT EFFECT — land never enters tapped, so Amulet doesn't trigger",
    "EC-03: Grazer ETB lands enter separately from Grazer's ETB — Amulet triggers on the land, not Grazer",
    "EC-04: Titan ETB fetches 2 bounce lands → 4 mana + 2 bounce triggers (each returns a different land)",
    "EC-05: Summoner's Pact — must pay {2}{G}{G} at next upkeep or lose. Only cast if winning this turn",
    "EC-06: Lotus Field + Spelunking — tap for 3 in response to own ETB sac trigger",
    "EC-07: Scapeshift sac'd lands go to GY (not searchable) — Aftermath Analyst is a separate second step",
    "EC-08: Cultivator Colossus P/T grows during its own ETB chain as lands accumulate",
    "EC-09: Echoing Deeps copies land CARD (not permanent) — bounce land copy works but needs Amulet",
    "EC-10: GSZ X=6 puts Titan into play (not cast) — triggers ETB, skips Pact risk, no cast trigger",
]
