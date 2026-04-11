"""
dimir_murktide.py — APL for Modern Dimir Oculus (formerly Murktide; April 2026)

NOTE: The registered key "murktide"/"dimirmurktide" now maps to Dimir Oculus,
the evolution of the blue-black tempo shell. Murktide Regent is still present
(2 copies) but Abhorrent Oculus and Psychic Frog are the primary threats.

VERIFIED card interactions (CardDB, deck: dimir_oculus_modern.txt):

  Abhorrent Oculus [{2}{U}] — Creature, Eye. 5/5 Flying.
    ADDITIONAL COST: exile 6 cards from your graveyard.
    ETB each opponent's upkeep: manifest dread (top 2 → 1 face-down 2/2 on BF, 1 to GY).
    KEY: The 6-exile cost is a GY tax. With Thought Scour (mill 2) + Consider (surveil 1)
    in hand, you can fill 6+ cards in GY by T2-3 and cast Oculus for {2}{U} as a 5/5 flyer.
    The manifest dread also mills 1 card per opponent upkeep = growing clock.
    Goldfish: no opponent upkeep to trigger. Just a 5/5 flyer for {2}{U} after GY fill.

  Psychic Frog [{U}{B}] — 1/2.
    Combat damage → draw a card.
    Discard a card → +1/+1 counter.
    Exile 3 from your GY → flying until EOT.
    KEY THREAT: Discard bad draws (excess lands, dead counters) → Frog grows.
    With enough discards: Frog becomes a 4/5, 5/6, etc.
    Flying can be gained at instant speed to swing over blockers.

  Murktide Regent [{5}{U}{U}] — 3/3 Flying, Delve.
    Delve: each card exiled from GY pays {1}.
    Enters with +1/+1 per instant/sorcery exiled WITH it.
    Whenever instant/sorcery leaves GY: +1/+1 counter.
    With 5 instants/sorceries in GY + 5 exiled: costs {U}{U}, enters as 8/8 (5 counters).
    GOLDFISH: usually a 5/5 to 8/8 by T3-4.

  Unearth [{B}] — Sorcery. Return creature MV ≤ 3 from GY to BF.
    Cycling {2}: discard → draw.
    KEY: Recur Psychic Frog (MV 2) or Orcish Bowmasters (MV 2) from GY.
    Cycling in goldfish if no target in GY.

  Consider [{U}] — Instant. Surveil 1 then draw a card.
    Surveil 1: look at top, may put in GY. Then draw.
    Fills GY for Oculus + draws a card. Essential cantrip.

  Thought Scour [{U}] — Instant. Target player mills 2, draw 1.
    Usually target YOURSELF: mill 2 (fill GY) + draw 1.
    Two copies = 4 cards in GY. Critical for Oculus's 6-exile cost.

  Orcish Bowmasters [{1}{B}] — 1/1 Flash.
    ETB (and whenever opponent draws beyond first each draw step): deal 1 damage + amass Orcs 1.
    Goldfish: ETB only (no opponent draws). 1 damage + 1/1 Orc Army token (amass 1).

  Harbinger of the Seas [{1}{U}{U}] — 2/2. Nonbasic lands are Islands.
    Dead in goldfish. 2/2 body.

  Gloomlake Verge [Land]: {T} Add {U}. Or {B} if you control Island or Swamp.
    Flexible dual land. No enters-tapped penalty.

  Force of Negation / Counterspell / Spell Snare: counters. Dead in goldfish.
  Sink into Stupor / Fatal Push / Shoot the Sheriff: removal. Dead in goldfish.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Constants ──────────────────────────────────────────────────────────────────
OCULUS     = "Abhorrent Oculus"
FROG       = "Psychic Frog"
MURKTIDE   = "Murktide Regent"
UNEARTH    = "Unearth"
CONSIDER   = "Consider"
SCOUR      = "Thought Scour"
BOWMASTERS = "Orcish Bowmasters"
HARBINGER  = "Harbinger of the Seas"
COUNTERSPELL = "Counterspell"
SNARE      = "Spell Snare"
FON        = "Force of Negation"
SINK       = "Sink into Stupor"
PUSH       = "Fatal Push"
SHERIFF    = "Shoot the Sheriff"

DEAD_IN_GOLDFISH = {COUNTERSPELL, SNARE, FON, SINK, PUSH, SHERIFF, HARBINGER}
CANTRIPS = {CONSIDER, SCOUR}


class MurktideAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Dimir Oculus (2026).
    Registered as 'murktide'/'dimirmurktide' for registry compatibility.

    Kill plan:
      A) T3 Abhorrent Oculus: fill GY with Thought Scour + Consider (mill 4-5
         cards), then cast Oculus ({2}{U}) exiling 6 → 5/5 flyer.
      B) Psychic Frog: grows via discards, draws cards on combat hit.
      C) Murktide Regent: T3-4 via Delve off instant/sorcery graveyard.
      D) Unearth: recur Frog or Bowmasters from GY.

    Typical kill: T4-6 with Oculus + Frog pressure.
    """

    name = "Dimir Oculus"
    win_condition_damage = 20
    max_turns = 12

    # ── Per-game state ─────────────────────────────────────────────────
    _gy_count          = 0     # cards in graveyard (simplified tracking)
    _gy_instant_count  = 0     # instants/sorceries specifically (for Murktide)
    _frog_up           = False
    _frog_counters     = 0
    _oculus_up         = False
    _murktide_up       = False
    _murktide_counters = 0
    _orc_army_power    = 0     # Orcish Bowmasters Orc Army token power

    def reset_game(self):
        self._gy_count         = 0
        self._gy_instant_count = 0
        self._frog_up          = False
        self._frog_counters    = 0
        self._oculus_up        = False
        self._murktide_up      = False
        self._murktide_counters= 0
        self._orc_army_power   = 0

    # ── GY tracking ─────────────────────────────────────────────────────
    def _sync_gy(self, gs: GameState):
        """Sync GY count from actual zone."""
        self._gy_count = len(gs.zones.graveyard)
        self._gy_instant_count = sum(
            1 for c in gs.zones.graveyard
            if "instant" in c.type_line.lower() or "sorcery" in c.type_line.lower()
        )

    def _can_cast_oculus(self, gs: GameState) -> bool:
        """Oculus costs {2}{U} + exile 6 from GY."""
        self._sync_gy(gs)
        return gs.mana_pool.total() >= 3 and self._gy_count >= 6

    def _can_cast_murktide(self, gs: GameState) -> bool:
        """
        Murktide costs {5}{U}{U} base, delve reduces generic cost by 1 per GY card exiled.
        Need at least {U}{U} remaining after delve + 5 GY cards to exile.
        Simplified: need 2 blue mana + at least 5 instants/sorceries in GY.
        """
        self._sync_gy(gs)
        if self._gy_instant_count < 3: return False
        delve = min(self._gy_instant_count, 5)
        generic_needed = max(0, 5 - delve)
        return (gs.mana_pool.U + gs.mana_pool.flex) >= 2 and gs.mana_pool.total() >= (2 + generic_needed)

    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Dimir Oculus keep criteria:
          - Need 2 lands minimum.
          - Want at least 1 cantrip (Consider/Scour) to fill GY.
          - Want a threat (Frog, Oculus, Murktide).
          - Ideal: 2 lands + 2 cantrips + Frog.
          - Dead-heavy hands: mull if 3+ dead counters/removal.
        """
        if len(hand) <= 4: return True

        lands      = [c for c in hand if c.is_land()]
        cantrips   = [c for c in hand if c.name in CANTRIPS]
        threats    = [c for c in hand if c.name in {FROG, OCULUS, MURKTIDE}]
        dead       = [c for c in hand if c.name in DEAD_IN_GOLDFISH]
        unearths   = [c for c in hand if c.name == UNEARTH]

        if not lands: return False
        if len(lands) >= 5: return False
        if len(dead) >= 3 and mulligans < 2: return False

        # Ideal: cantrips + threat + lands
        if cantrips and threats and len(lands) >= 2: return True

        # Frog + lands: can discard dead cards to grow
        if any(c.name == FROG for c in hand) and len(lands) >= 2: return True

        # Oculus + 2 cantrips: can fill GY by T3
        if any(c.name == OCULUS for c in hand) and len(cantrips) >= 2 and lands: return True

        # 2 lands + threat (no cantrips, but manageable)
        if len(lands) >= 2 and threats and mulligans <= 1: return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority:
          1. Dead counters/removal (all dead in goldfish)
          2. Excess lands past 3
          3. Sink into Stupor (bounce is useless)
          4. Harbinger (2/2 with no goldfish effect)
        """
        to_bottom: list[Card] = []
        lands = [c for c in hand if c.is_land()]

        for c in hand:
            if len(to_bottom) >= n: break
            if c.name in DEAD_IN_GOLDFISH: to_bottom.append(c)

        for c in lands[3:]:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)

        rest = sorted(
            [c for c in hand if not c.is_land() and c not in to_bottom],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n: break
            if c.name not in {FROG, OCULUS, MURKTIDE, UNEARTH, CONSIDER, SCOUR, BOWMASTERS}:
                to_bottom.append(c)

        return to_bottom[:n]


    # ── Cantrip / GY fill ────────────────────────────────────────────────
    def _cast_cantrip(self, card: Card, gs: GameState):
        """
        Consider: surveil 1 (may put top card in GY) then draw.
        Thought Scour: mill 2 (self) then draw.
        Both fill GY for Oculus / Murktide and cantrip.
        """
        gs.cast_spell(card)
        self._gy_count += 1        # the cantrip itself goes to GY

        if card.name == CONSIDER:
            # Surveil 1: look at top, put in GY if it helps (always yes for Oculus setup)
            if gs.zones.library:
                top = gs.zones.library[0]
                gs.zones.library.pop(0)
                gs.zones.graveyard.append(top)
                self._gy_count += 1
                is_instant_sorcery = ("instant" in top.type_line.lower()
                                      or "sorcery" in top.type_line.lower())
                if is_instant_sorcery:
                    self._gy_instant_count += 1
            # Draw a card
            if gs.zones.library:
                gs.zones.hand.append(gs.zones.library.pop(0))
            gs._log(f"  Consider: surveil 1 → GY ({self._gy_count} total), draw 1")

        elif card.name == SCOUR:
            # Mill 2 (self), draw 1
            for _ in range(2):
                if gs.zones.library:
                    milled = gs.zones.library.pop(0)
                    gs.zones.graveyard.append(milled)
                    self._gy_count += 1
                    if ("instant" in milled.type_line.lower()
                            or "sorcery" in milled.type_line.lower()):
                        self._gy_instant_count += 1
            if gs.zones.library:
                gs.zones.hand.append(gs.zones.library.pop(0))
            gs._log(f"  Thought Scour: mill 2 → GY ({self._gy_count} total), draw 1")

    # ── Abhorrent Oculus ─────────────────────────────────────────────────
    def _cast_oculus(self, gs: GameState):
        """
        Abhorrent Oculus ({2}{U}) + exile 6 from GY.
        5/5 Flying. Needs at least 6 cards in GY.
        """
        for card in list(gs.hand()):
            if card.name != OCULUS:
                continue
            if gs.mana_pool.total() < 3:
                continue
            self._sync_gy(gs)
            if self._gy_count < 6:
                continue
            # Pay mana
            gs.mana_pool.flex = max(0, gs.mana_pool.flex - 3)
            # Exile 6 from GY (take instants/sorceries last — preserve for Murktide)
            exiled = 0
            # Exile non-instant/sorcery first
            for c in list(gs.zones.graveyard):
                if exiled >= 6:
                    break
                if "instant" not in c.type_line.lower() and "sorcery" not in c.type_line.lower():
                    gs.zones.graveyard.remove(c)
                    gs.zones.exile.append(c)
                    self._gy_count -= 1
                    exiled += 1
            # Then exile instants/sorceries if still needed
            for c in list(gs.zones.graveyard):
                if exiled >= 6:
                    break
                gs.zones.graveyard.remove(c)
                gs.zones.exile.append(c)
                self._gy_count -= 1
                if "instant" in c.type_line.lower() or "sorcery" in c.type_line.lower():
                    self._gy_instant_count -= 1
                exiled += 1
            # Put Oculus on battlefield
            gs.zones.hand.remove(card)
            gs.zones.battlefield.append(card)
            card.summoning_sickness = True
            card.turn_entered = gs.turn
            self._oculus_up = True
            gs._log(f"  Abhorrent Oculus: 5/5 flying in play (exiled {exiled} from GY)")
            break

    # ── Murktide Regent ───────────────────────────────────────────────────
    def _cast_murktide(self, gs: GameState):
        """
        Murktide Regent ({5}{U}{U}), Delve.
        Each instant/sorcery exiled from GY pays {1}.
        Enters with +1/+1 for each exiled with it.
        With 5 in GY: costs {U}{U}, enters as 8/8.
        """
        for card in list(gs.hand()):
            if card.name != MURKTIDE:
                continue
            self._sync_gy(gs)
            exilable = self._gy_instant_count
            delve = min(exilable, 5)
            generic_needed = max(0, 5 - delve)
            blue_needed = 2
            total_needed = generic_needed + blue_needed
            if gs.mana_pool.total() < total_needed:
                continue
            # Pay
            gs.mana_pool.flex = max(0, gs.mana_pool.flex - total_needed)
            # Exile from GY for delve
            exiled_count = 0
            for c in list(gs.zones.graveyard):
                if exiled_count >= delve:
                    break
                if "instant" in c.type_line.lower() or "sorcery" in c.type_line.lower():
                    gs.zones.graveyard.remove(c)
                    gs.zones.exile.append(c)
                    self._gy_count -= 1
                    self._gy_instant_count -= 1
                    exiled_count += 1
            # Murktide enters as 3/3 + 1/1 per exiled instant/sorcery
            card.power = str(3 + exiled_count)
            card.toughness = str(3 + exiled_count)
            self._murktide_counters = exiled_count
            gs.zones.hand.remove(card)
            gs.zones.battlefield.append(card)
            card.summoning_sickness = True
            card.turn_entered = gs.turn
            self._murktide_up = True
            gs._log(f"  Murktide Regent: {card.power}/{card.toughness} (delved {exiled_count})")
            break

    # ── Unearth ───────────────────────────────────────────────────────────
    def _try_unearth(self, gs: GameState):
        """
        Unearth ({B}): return creature MV ≤ 3 from GY to BF.
        Best target: Psychic Frog (MV 2) — gets back the discard engine.
        Cycle ({2}) if no valid target.
        """
        for card in list(gs.hand()):
            if card.name != UNEARTH:
                continue
            # Try to recur Frog
            if gs.mana_pool.total() >= 1:
                frog_in_gy = next(
                    (c for c in gs.zones.graveyard if c.name == FROG), None
                )
                bowmaster_in_gy = next(
                    (c for c in gs.zones.graveyard
                     if c.name == BOWMASTERS), None
                )
                target = frog_in_gy or bowmaster_in_gy
                if target:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    gs.zones.graveyard.remove(target)
                    gs.zones.battlefield.append(target)
                    target.summoning_sickness = True
                    target.turn_entered = gs.turn
                    if target.name == FROG:
                        self._frog_up = True
                    self._gy_count -= 1  # target left GY
                    gs._log(f"  Unearth: {target.name} from GY to battlefield")
                    break
            # Cycle if no target and have {2}
            if gs.mana_pool.total() >= 2:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                gs.zones.hand.remove(card)
                gs.zones.graveyard.append(card)
                self._gy_count += 1
                if gs.zones.library:
                    gs.zones.hand.append(gs.zones.library.pop(0))
                gs._log("  Unearth: cycle for draw (no valid GY target)")
            break

    # ── Bowmasters ────────────────────────────────────────────────────────
    def _cast_bowmasters(self, gs: GameState):
        """
        Orcish Bowmasters ({1}{B} = 2 mana): 1/1 Flash.
        ETB: deal 1 damage to any target + amass Orcs 1.
        Goldfish: 1 damage to face + create/grow 1/1 Orc Army token.
        """
        for card in list(gs.hand()):
            if card.name != BOWMASTERS:
                continue
            if gs.mana_pool.total() < 2:
                continue
            gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
            gs.zones.play_from_hand(card)
            card.summoning_sickness = True
            card.turn_entered = gs.turn
            # ETB: 1 damage to any target (face in goldfish)
            gs.damage_dealt += 1
            # Amass Orcs 1: create/grow Orc Army token
            self._orc_army_power += 1
            gs._log(f"  Orcish Bowmasters: ETB 1 damage, Orc Army now {self._orc_army_power}/1")
            break


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat priority:
          1. Reset on T1
          2. Land drop
          3. Cantrips (fill GY + draw — always cast these ASAP)
          4. Psychic Frog (discard outlet + growing threat)
          5. Discard dead cards to Frog (grow it, dump useless counters)
          6. Abhorrent Oculus (5/5 flyer, needs 6 in GY)
          7. Orcish Bowmasters (1 damage ETB + Orc Army)
          8. Murktide Regent (Delve 8/8 with enough instants in GY)
          9. Unearth (recur Frog/Bowmasters OR cycle for draw)
        """
        if gs.turn == 1:
            self.reset_game()

        self._sync_gy(gs)

        # ── 1. Land drop ────────────────────────────────────────────────
        if not gs.land_played:
            self._play_land_if_able(gs)

        # ── 2. Cast all cantrips first (fill GY + draw) ─────────────────
        # Cast multiple cantrips per turn if available — GY filling is critical
        for _ in range(4):  # can cast multiple 1-mana cantrips per turn
            cast_one = False
            for card in list(gs.hand()):
                if card.name in CANTRIPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    self._cast_cantrip(card, gs)
                    cast_one = True
                    break
            if not cast_one:
                break

        self._sync_gy(gs)

        # ── 3. Psychic Frog ({U}{B} = 2 mana) ──────────────────────────
        if not self._frog_up:
            for card in list(gs.hand()):
                if card.name == FROG and gs.mana_pool.total() >= 2:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                    gs.zones.play_from_hand(card)
                    card.summoning_sickness = True
                    card.turn_entered = gs.turn
                    self._frog_up = True
                    gs._log("  Psychic Frog: 1/2 in play")
                    break

        # ── 4. Discard dead cards to Frog ───────────────────────────────
        if self._frog_up:
            for card in list(gs.hand()):
                if card.name in DEAD_IN_GOLDFISH:
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    self._frog_counters += 1
                    self._gy_count += 1
                    gs._log(f"  Frog discard: {card.name} → Frog {1+self._frog_counters}/{2+self._frog_counters}")

        # ── 5. Abhorrent Oculus ──────────────────────────────────────────
        if not self._oculus_up:
            self._cast_oculus(gs)

        # ── 6. Orcish Bowmasters ─────────────────────────────────────────
        self._cast_bowmasters(gs)

        # ── 7. Murktide Regent ───────────────────────────────────────────
        if not self._murktide_up:
            self._cast_murktide(gs)

        # ── 8. Unearth (recur or cycle) ──────────────────────────────────
        self._try_unearth(gs)

        # ── 9. Harbinger if nothing else (2/2 body) ──────────────────────
        for card in list(gs.hand()):
            if card.name == HARBINGER and gs.mana_pool.total() >= 3:
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 3)
                gs.zones.play_from_hand(card)
                card.summoning_sickness = True
                card.turn_entered = gs.turn
                gs._log("  Harbinger of the Seas: 2/2 in play")
                break

    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat:
          1. Compute creature combat damage
          2. Psychic Frog combat draw (dealt damage → drew a card)
          3. Cast remaining cantrips with leftover mana
          4. Oculus/Murktide if just became castable after cantrips
        """
        # ── 1. Combat damage ────────────────────────────────────────────
        for c in gs.zones.battlefield:
            if getattr(c, "summoning_sickness", True):
                continue
            if not c.has(Tag.CREATURE):
                continue
            try:
                power = int(c.power or 0)
            except (ValueError, TypeError):
                power = 0

            if c.name == FROG:
                power = 1 + self._frog_counters
                gs.damage_dealt += power
                # Combat damage → draw a card
                if gs.zones.library:
                    gs.zones.hand.append(gs.zones.library.pop(0))
                gs._log(f"  Psychic Frog attacks: {power}, drew 1 ({gs.damage_dealt} total)")
            elif c.name == OCULUS:
                gs.damage_dealt += 5
                gs._log(f"  Abhorrent Oculus attacks: 5 flying ({gs.damage_dealt} total)")
            elif c.name == MURKTIDE:
                pw = 3 + self._murktide_counters
                gs.damage_dealt += pw
                gs._log(f"  Murktide Regent attacks: {pw} ({gs.damage_dealt} total)")
            elif c.name == BOWMASTERS:
                gs.damage_dealt += 1
                gs._log(f"  Orcish Bowmasters attacks: 1 ({gs.damage_dealt} total)")
            elif c.name == HARBINGER:
                gs.damage_dealt += 2
                gs._log(f"  Harbinger attacks: 2 ({gs.damage_dealt} total)")
            elif self._orc_army_power > 0 and c.name == "Orc Army":
                gs.damage_dealt += self._orc_army_power
                gs._log(f"  Orc Army attacks: {self._orc_army_power} ({gs.damage_dealt} total)")

        # ── 2. More cantrips post-combat ──────────────────────────────────
        for card in list(gs.hand()):
            if card.name in CANTRIPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._cast_cantrip(card, gs)

        self._sync_gy(gs)

        # ── 3. Oculus / Murktide if now ready ────────────────────────────
        if not self._oculus_up:
            self._cast_oculus(gs)
        if not self._murktide_up:
            self._cast_murktide(gs)

        # ── 4. Unearth ────────────────────────────────────────────────────
        self._try_unearth(gs)

    # ── Sideboard premium ────────────────────────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        opp = opponent.lower()
        if any(x in opp for x in ("living end", "cascade")):
            return 0.07   # Nihil Spellbomb + Consign to Memory
        if any(x in opp for x in ("yawgmoth", "reanimator", "goryo")):
            return 0.06   # Nihil Spellbomb hits GY combos
        if any(x in opp for x in ("boros energy", "affinity")):
            return -0.03  # They're faster aggressors
        if any(x in opp for x in ("control", "blink")):
            return 0.04   # Force of Negation + Consign protect threats
        if any(x in opp for x in ("combo", "storm")):
            return 0.05   # Counterspell + Spell Snare walls cheap spells
        if any(x in opp for x in ("tron", "eldrazi")):
            return 0.03   # Harbinger makes their non-basics useless
        return 0.0



# ── Edge Case Registry ──────────────────────────────────────────────────────
#
# EC-01: Abhorrent Oculus additional cost — exile from YOUR graveyard.
#   "Exile six cards from your graveyard" — not library, not opponent's GY.
#   This is an ADDITIONAL COST, not an alternative. You pay it even if countered.
#   If you have fewer than 6 in GY, you CANNOT cast Oculus. Full stop.
#   Key implication: Nihil Spellbomb empties your GY → kills Oculus as a turn 3+ play.
#
# EC-02: Abhorrent Oculus manifest dread trigger.
#   "At the beginning of each OPPONENT'S upkeep" — fires on their turn.
#   Look at top 2: put one face-down as 2/2, other to GY.
#   Face-down 2/2 can be turned face-up by paying its mana cost if it's a creature.
#   In goldfish: no opponent upkeep, so this is a dead trigger. Just a 5/5 flyer.
#
# EC-03: Psychic Frog flying activation.
#   "Exile three cards from your graveyard: gains flying until end of turn."
#   This costs GY cards — competes with Oculus's 6-exile cost.
#   Priority: save GY for Oculus first. Activate flying only if already have Oculus out.
#   Flying matters for attacks over blockers and for dodging ground creatures.
#
# EC-04: Thought Scour targets a player — usually yourself.
#   "Target player mills two cards" — you choose. In a GY-strategy deck: target yourself.
#   vs. opponents with GY strategies (Living End): target OPPONENT instead to disrupt.
#   Don't automatically self-mill against decks that recur from GY.
#
# EC-05: Murktide Regent counter interaction.
#   "Whenever an instant or sorcery card LEAVES your graveyard" → +1/+1 counter.
#   This fires when you: cycle an Unearth ({2}, discard Unearth = instant/sorcery → GY),
#   cast Unearth from hand (it goes to GY = "left the library"), etc.
#   More broadly: Fetch lands put cards in GY; exile via Oculus cost removes from GY.
#   Exiling from GY for Oculus cost ALSO triggers Murktide's "leaves GY" ability!
#   So if Murktide is out when you cast Oculus: it gets +6/+6 from the 6 exiles.
#
# EC-06: Unearth "return to the battlefield" — not "return to hand."
#   The unearthed creature goes directly to the battlefield.
#   It gets summoning sickness (as normal for creatures entering the battlefield).
#   At end step, exile the unearthed creature (delayed trigger, like Goryo's).
#   Ephemerate can dodge Unearth's exile trigger too — same object-tracking mechanic.
#
# EC-07: Orcish Bowmasters amass Orcs 1.
#   "Amass Orcs 1" = put a +1/+1 counter on an Orc Army token you control; if none, create one.
#   The Orc Army is a creature token with changing P/T.
#   Multiple Bowmasters ETBs stack: 3 Bowmasters ETBs = 3 damage + Orc Army is 3/3.
#   In a game where Bowmasters resolves 3+ times: the Army becomes a serious attacker.
#
# EC-08: Harbinger of the Seas — "nonbasic lands are Islands."
#   This is a REPLACEMENT EFFECT that changes what nonbasic lands produce.
#   Opponent's Urza's Tower? Now an Island. Opponent's Stomping Ground? Island only.
#   This SHUTS DOWN Tron (all 3 Tron lands become Islands) and Eldrazi Temple.
#   Potentially also shuts down friendly nonbasics — be careful with Harbinger against mirrors.
#   Harbinger's ability is a STATIC ability, not a triggered one. No stack.
#
# EC-09: Force of Negation pitch cost — exile a BLUE card.
#   "If it's not your turn, you may exile a blue card from your hand rather than pay."
#   Pitchable blue cards: Consider, Counterspell, Spell Snare, Sink into Stupor,
#   Harbinger, Murktide Regent (blue), Thought Scour, another FoN.
#   NOT pitchable: Fatal Push, Orcish Bowmasters (black), Unearth (black).
#   Using FoN on your turn = must pay full {1}{U}{U}.
#
# EC-10: Gloomlake Verge produces {B} only if you control an Island or Swamp.
#   Early game with no other lands: Gloomlake taps for {U} only.
#   After playing any Island (Watery Grave, basic Island): Gloomlake = full {U}/{B} dual.
#   Deck has 3 Islands and multiple Island-typed duals — usually online by T2.
#
EDGE_CASES = [
    "EC-01: Abhorrent Oculus exile cost from YOUR GY — 6 cards required or you can't cast it",
    "EC-02: Oculus manifest trigger fires on OPPONENT's upkeep — dead in goldfish, real in match",
    "EC-03: Frog flying costs 3 GY exiles — save GY for Oculus first; activate flying after Oculus is out",
    "EC-04: Thought Scour can target OPPONENT — vs Living End/GY decks, mill them not yourself",
    "EC-05: Murktide triggers on instants/sorceries LEAVING GY — exiling 6 for Oculus = +6/+6 on Murktide",
    "EC-06: Unearth creature has summoning sickness + exiles at end step (Ephemerate can dodge this too)",
    "EC-07: Bowmasters amass stacks — 3 ETBs = 3 damage + 3/3 Orc Army attacker",
    "EC-08: Harbinger makes ALL nonbasics into Islands — shuts Tron completely, beware in mirrors",
    "EC-09: Force of Negation pitch = exile blue card from hand. Push/Bowmasters are not blue",
    "EC-10: Gloomlake Verge only produces {B} after you control an Island or Swamp",
]
