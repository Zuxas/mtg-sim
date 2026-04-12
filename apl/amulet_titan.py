"""
amulet_titan.py — APL for Modern Amulet Titan (FULL REWRITE, April 2026)

Based on Dom Harvey's "All About Amulet Titan" (the Titan Bible, Nov 2025 edition).

This APL models Amulet Titan as a DETERMINISTIC COMBO DECK, not a beatstick.
Kill lines (in priority order):
  1. Scapeshift OHKO (1 Amulet + 4 lands = deterministic kill)
  2. Titan + haste + Mirrorpool chain (immediate lethal with 2+ Amulets)
  3. Analyst infinite loop (Amulet + Lotus + Deeps + Woodland + delirium)
  4. Raw Titan beatdown (fallback: 6/6 trample, 4 attacks to kill)

Core mechanic:
  Amulet of Vigor + bounce land = 2 mana per land drop per Amulet.
  With extra land drops (Grazer/Spelunking): replay same bounce land 3-4 times.
  A single bounce land can generate 6+ mana with 1 Amulet and 3 land drops.
  With 2 Amulets: each replay = 4 mana. T2-T3 kills are possible.

  Bible: "you should use bouncelands' triggers on themselves after you tap
  them for mana, so that you can play them again."
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState, GameResult, Phase
from engine.keywords import KWTag

# ══════════════════════════════════════════════════════════════════════════════
# Card name constants
# ══════════════════════════════════════════════════════════════════════════════
TITAN          = "Primeval Titan"
AMULET         = "Amulet of Vigor"
GRAZER         = "Arboreal Grazer"
SPELUNKING     = "Spelunking"
MINSTREL       = "The Wandering Minstrel"
RUMBLE         = "Malevolent Rumble"
ANALYST        = "Aftermath Analyst"
COLOSSUS       = "Cultivator Colossus"
ZENITH         = "Green Sun's Zenith"
PACT           = "Summoner's Pact"
SCAPESHIFT     = "Scapeshift"
LOTUS          = "Lotus Field"
GRUUL_TURF     = "Gruul Turf"
SIMIC_CHAMBER  = "Simic Growth Chamber"
SELESNYA_SANC  = "Selesnya Sanctuary"
URZA_CAVE      = "Urza's Cave"
ECHOING        = "Echoing Deeps"
VEXING         = "Vexing Bauble"
DRYAD_ARBOR    = "Dryad Arbor"
BOSEIJU        = "Boseiju, Who Endures"
OTAWARA        = "Otawara, Soaring City"
HANWEIR        = "Hanweir Battlements"
MIRRORPOOL     = "Mirrorpool"
SAGA           = "Urza's Saga"
GARDENS        = "The Mycosynth Gardens"
SHIFTING       = "Shifting Woodland"
TOLARIA        = "Tolaria West"
VESTIGE        = "Crumbling Vestige"
VESUVA         = "Vesuva"
FOREST_        = "Forest"
ICETILL        = "Icetill Explorer"

BOUNCE_LANDS   = {GRUUL_TURF, SIMIC_CHAMBER, SELESNYA_SANC}
ALWAYS_UNTAPPED = {FOREST_, "Snow-Covered Forest", BOSEIJU, OTAWARA, HANWEIR,
                   URZA_CAVE, SHIFTING, GARDENS, DRYAD_ARBOR, "Ghost Quarter"}
FOREST_TYPES    = {FOREST_, "Snow-Covered Forest", DRYAD_ARBOR}

# Mana produced by each land when tapped (for custom tap logic)
LAND_MANA = {
    GRUUL_TURF:    {'R': 1, 'G': 1},
    SIMIC_CHAMBER: {'G': 1, 'U': 1},
    SELESNYA_SANC: {'G': 1, 'W': 1},
    LOTUS:         {'G': 3},       # 3 of any one color; default to G
    FOREST_:       {'G': 1},
    "Snow-Covered Forest": {'G': 1},
    DRYAD_ARBOR:   {'G': 1},
    BOSEIJU:       {'G': 1},
    OTAWARA:       {'U': 1},
    HANWEIR:       {'C': 1},
    MIRRORPOOL:    {'C': 1},
    URZA_CAVE:     {'C': 1},
    ECHOING:       {'C': 1},       # default; may copy another land
    VESTIGE:       {'C': 1},       # ETB gives 1 any color; tap gives C
    SAGA:          {'C': 1},       # Chapter I gives {T}: Add {C}
    VESUVA:        {'C': 1},       # copies whatever it entered as
    SHIFTING:      {'G': 1},
    GARDENS:       {'C': 1},
    "Ghost Quarter": {'C': 1},
}

# Saga search targets (MV 0-1 artifacts)
SAGA_TARGETS = [AMULET, VEXING]


# ══════════════════════════════════════════════════════════════════════════════
# APL Class
# ══════════════════════════════════════════════════════════════════════════════

class AmuletTitanAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Amulet Titan.

    This is a COMBO DECK. The goal is to assemble a deterministic kill via:
    1. Scapeshift (most common): 1 Amulet + 4 lands → Shift→Lotus→TWest→Pact→Analyst→loop
    2. Titan + haste chain: Deploy Titan → ETB fetches lands → Mirrorpool copies → chain
    3. Analyst loop: Amulet + Lotus + 2nd Lotus/Deeps + Woodland = infinite mana → win
    4. Beatdown (fallback): 6/6 Titan attacks 4 times

    Core engine: Amulet of Vigor + bounce lands + extra land drops (Grazer/Spelunking)
    """

    name = "Amulet Titan"
    win_condition_damage = 20
    max_turns = 15

    # ── Per-game state ───────────────────────────────────────────────
    def reset_game(self):
        self._amulets         = 0      # Amulet of Vigor count on BF
        self._spelunking_cnt  = 0      # Spelunking count
        self._minstrel_up     = False  # Wandering Minstrel
        self._titan_on_bf     = False
        self._titan_has_haste = False
        self._titan_etb_used  = False
        self._analyst_on_bf   = False
        self._icetill_on_bf   = False
        self._gardens_on_bf   = False
        self._hanweir_on_bf   = False
        self._hanweir_tapped  = False
        self._mirror_on_bf    = False
        self._mirror_used     = False
        self._saga_on_bf      = False
        self._vexing_on_bf    = False
        self._spawn_count     = 0
        self._pact_owed       = False
        self._pact_turn_cast  = -1
        self._lands_in_gy     = []     # list of land NAMES in GY
        self._delirium_types  = set()  # card types in GY for delirium
        self._construct_count = 0
        self._extra_land_used = False

    def reset_turn(self):
        self._hanweir_tapped  = False
        self._titan_has_haste = False
        self._extra_land_used = False
        self._titan_etb_used  = False
        self._mirror_used     = False
        self._land_drops_used = 0     # total land drops this turn (including replays)
        self._max_land_drops  = 1     # base: 1 land drop per turn

    # ══════════════════════════════════════════════════════════════════
    # CORE ENGINE: Amulet untap + mana generation
    # ══════════════════════════════════════════════════════════════════

    def _untap_replacement_active(self) -> bool:
        """True if lands entering tapped will be untapped (Amulet or Spelunking)."""
        return self._amulets > 0 or self._spelunking_cnt > 0 or self._minstrel_up

    def _add_land_mana(self, land_name: str, gs: GameState):
        """Add the correct mana for tapping a specific land."""
        mana = LAND_MANA.get(land_name, {'C': 1})
        for color, amount in mana.items():
            cur = getattr(gs.mana_pool, color, 0)
            setattr(gs.mana_pool, color, cur + amount)

    def _resolve_land_etb(self, land_name: str, gs: GameState) -> int:
        """
        Resolve a land entering the battlefield with Amulet/Spelunking.
        Returns total mana generated.
        
        With N Amulets: land enters tapped → N untap triggers → tap between each.
        Bible: "with two Amulets you can tap in response to each trigger"
        So N Amulets = N taps = N * (land's mana output).
        
        Spelunking: land enters untapped (replacement effect, NOT trigger).
        Only 1 tap regardless of Amulet count when Spelunking is active.
        """
        am = self._amulets
        repl = self._spelunking_cnt > 0 or self._minstrel_up
        total = 0

        # Vesuva: copies best land already on BF
        if land_name == VESUVA:
            bf_land_names = [x.name for x in gs.zones.battlefield if x.is_land() and x.name != VESUVA]
            if bf_land_names:
                for target in [LOTUS, GRUUL_TURF, SIMIC_CHAMBER, SAGA]:
                    if target in bf_land_names:
                        land_name = target
                        gs._log(f"  Vesuva copies {target}")
                        break

        # Echoing Deeps: copies best land in GY
        if land_name == ECHOING:
            gy_names = list(self._lands_in_gy)
            if gy_names:
                for target in [LOTUS, GRUUL_TURF, SIMIC_CHAMBER, VESTIGE]:
                    if target in gy_names:
                        land_name = target
                        gs._log(f"  Deeps copies {target} from GY")
                        break

        if repl and am == 0:
            # Spelunking only: enters untapped, tap once
            self._add_land_mana(land_name, gs)
            total = sum(LAND_MANA.get(land_name, {'C': 1}).values())
        elif am > 0 and not repl:
            # Amulet(s) only: enters tapped → N untap triggers → tap N times
            mana_per_tap = sum(LAND_MANA.get(land_name, {'C': 1}).values())
            for _ in range(am):
                self._add_land_mana(land_name, gs)
            total = mana_per_tap * am
        elif am > 0 and repl:
            # Spelunking + Amulet: land enters UNTAPPED (replacement effect)
            # Amulet triggers DON'T fire (land never entered tapped)
            # Bible EC-02: "Spelunking is a REPLACEMENT EFFECT — Amulet doesn't trigger"
            # Result: just 1 tap
            self._add_land_mana(land_name, gs)
            total = sum(LAND_MANA.get(land_name, {'C': 1}).values())
        else:
            # No engine: land enters tapped, no mana this turn
            total = 0

        if land_name == VESTIGE and (am > 0 or repl):
            # Vestige ETB: add 1 mana of any color (triggered, separate from tap)
            # Choose R if Hanweir is on BF and needs haste activation
            if self._hanweir_on_bf and not self._titan_has_haste and not self._hanweir_tapped:
                gs.mana_pool.R += 1
            else:
                gs.mana_pool.G += 1
            total += 1

        return total

    def _apply_bounce_return(self, bounce_name: str, gs: GameState):
        """
        Bounce land trigger: return a land you control to hand.
        
        CRITICAL BIBLE MECHANIC: When you have extra land drops available,
        bounce the bounce land ITSELF back to hand so you can replay it
        for another Amulet chain.
        
        Bible: "you should use bouncelands' triggers on themselves after
        you tap them for mana, so that you can play them again. A single
        bounceland can generate 6 mana all by itself this way."
        
        Decision:
        - If extra land drops available + Amulet: bounce ITSELF (replay for chain)
        - On the LAST available land drop: bounce the least valuable other land
        - If no extra drops: bounce least valuable permanent land
        """
        bf_lands = [c for c in gs.zones.battlefield if c.is_land()]
        
        # Check extra land drops
        has_extra_drops = (
            not gs.land_played
            or self._icetill_on_bf
            or (not self._extra_land_used and self._icetill_on_bf)
        )
        # Also check if Grazer is in hand (ETB = extra land drop)
        grazer_in_hand = any(c.name == GRAZER for c in gs.zones.hand)
        
        # Calculate remaining drops: base (1) + extra from Grazer ETBs + Icetill + Spelunking
        max_drops = self._max_land_drops
        if self._icetill_on_bf:
            max_drops += 1
        remaining_drops = max_drops - self._land_drops_used
        can_replay = remaining_drops > 0 or grazer_in_hand
        
        # CRITICAL: Don't self-return if only 1 land on BF!
        # Need at least 2 lands so one stays as permanent mana while we chain the other.
        # Bible: the bounce chain generates burst mana on TOP of your permanent mana base.
        n_bf_lands = len(bf_lands)
        if n_bf_lands <= 1:
            can_replay = False
        
        if can_replay and self._amulets >= 1:
            # BOUNCE ITSELF — replay for another Amulet chain
            bounce_cards = [c for c in bf_lands if c.name == bounce_name]
            if bounce_cards:
                to_return = bounce_cards[-1]
                rid = id(to_return)
                gs.zones.battlefield = [c for c in gs.zones.battlefield if id(c) != rid]
                gs.zones.hand.append(to_return)
                # Reset land_played so the greedy loop can replay this bounce land
                gs.land_played = False
                gs._log(f"  Bounce SELF-RETURN: {bounce_name} → hand (will replay)")
                return
        
        # No extra drops or last replay — bounce least valuable other land
        def bounce_prio(c):
            n = c.name
            if n in FOREST_TYPES:      return 0   # return first (cheap, replaceable)
            if n == DRYAD_ARBOR:       return 1
            if n == TOLARIA:           return 2   # good to pick up for transmute
            if n == VESTIGE:           return 3   # replay for ETB mana
            if n == SHIFTING:          return 4
            if n == URZA_CAVE:         return 5
            if n == MIRRORPOOL:        return 6
            if n == ECHOING:           return 7
            if n in BOUNCE_LANDS:      return 8   # keep bounce on BF
            if n == LOTUS:             return 9   # NEVER bounce (3-mana land!)
            if n == HANWEIR:           return 9   # NEVER bounce (need for haste)
            if n == SAGA:              return 10  # NEVER bounce (need Ch III)
            if n == BOSEIJU:           return 6
            if n == GARDENS:           return 7
            return 5

        candidates = [c for c in bf_lands if c.name != bounce_name]
        if not candidates:
            candidates = [c for c in bf_lands if c.name == bounce_name]
        if not candidates:
            return
        candidates.sort(key=bounce_prio)
        to_return = candidates[0]
        rid = id(to_return)
        gs.zones.battlefield = [c for c in gs.zones.battlefield if id(c) != rid]
        gs.zones.hand.append(to_return)
        gs._log(f"  Bounce return: {to_return.name} → hand")
        
        # Update tracking
        if to_return.name == HANWEIR: self._hanweir_on_bf = False
        if to_return.name == MIRRORPOOL: self._mirror_on_bf = False
        if to_return.name == SAGA: self._saga_on_bf = False
        if to_return.name == GARDENS: self._gardens_on_bf = False

    def _apply_lotus_sac(self, gs: GameState):
        """Lotus Field ETB: sacrifice 2 lands (mandatory)."""
        bf_lands = [c for c in gs.zones.battlefield if c.is_land()]
        # Priority: sac least valuable (but never sac Lotus itself on first ETB)
        def sac_prio(c):
            n = c.name
            if n == LOTUS:         return 10  # never sac Lotus to itself
            if n == SAGA:          return 10  # never sac Saga
            if n == HANWEIR:       return 9
            if n in BOUNCE_LANDS:  return 9   # keep bounce
            if n == MIRRORPOOL:    return 6
            if n == GARDENS:       return 5
            if n in FOREST_TYPES:  return 0   # sac first
            if n == VESTIGE:       return 1
            return 3
        
        candidates = sorted([c for c in bf_lands if c.name != LOTUS], key=sac_prio)
        sacced = 0
        for c in candidates:
            if sacced >= 2: break
            cid = id(c)
            gs.zones.battlefield = [x for x in gs.zones.battlefield if id(x) != cid]
            gs.zones.graveyard.append(c)
            self._track_land_to_gy(c.name)
            sacced += 1
            gs._log(f"  Lotus Field: sacrificed {c.name}")

    def _track_land_to_gy(self, name: str):
        """Track a land going to the graveyard."""
        self._lands_in_gy.append(name)
        self._delirium_types.add("land")

    def _track_card_to_gy(self, type_line: str):
        """Track a non-land card going to GY for delirium."""
        tl = type_line.lower()
        for t in ("creature", "artifact", "enchantment", "instant", "sorcery", "planeswalker"):
            if t in tl:
                self._delirium_types.add(t)

    def _refresh_delirium(self, gs: GameState):
        """Scan actual GY for all card types — catches anything the manual tracking missed."""
        self._delirium_types = set()
        for c in gs.zones.graveyard:
            tl = getattr(c, 'type_line', '').lower()
            if c.is_land():
                self._delirium_types.add('land')
            for t in ("creature", "artifact", "enchantment", "instant", "sorcery", "planeswalker"):
                if t in tl:
                    self._delirium_types.add(t)

    # ══════════════════════════════════════════════════════════════════
    # LAND PLACEMENT: place a land on BF with proper tracking
    # ══════════════════════════════════════════════════════════════════

    def _place_land_on_bf(self, land: Card, gs: GameState, from_hand=True, give_haste=False):
        """
        Place a land on the battlefield with full ETB resolution.
        Handles: Amulet untap + mana, bounce triggers, Lotus sac, Saga tracking.
        """
        if from_hand and land in gs.zones.hand:
            gs.zones.hand.remove(land)
        
        land.tapped = False
        land.turn_entered = gs.turn
        gs.zones.battlefield.append(land)

        name = land.name
        
        # Track board state
        if name == HANWEIR:   self._hanweir_on_bf = True
        if name == MIRRORPOOL: self._mirror_on_bf = True
        if name == SAGA:      self._saga_on_bf = True
        if name == GARDENS:   self._gardens_on_bf = True

        # Generate mana from Amulet/Spelunking
        mana = 0
        if name in BOUNCE_LANDS or name == LOTUS or name == VESTIGE or name == ECHOING:
            mana = self._resolve_land_etb(name, gs)
        elif name in ALWAYS_UNTAPPED:
            # Untapped lands: just tap for 1 mana
            self._add_land_mana(name, gs)
            mana = sum(LAND_MANA.get(name, {'C': 1}).values())
        elif self._untap_replacement_active():
            # Other tapped lands with engine: untap + tap
            mana = self._resolve_land_etb(name, gs)
        
        # Bounce trigger
        if name in BOUNCE_LANDS:
            self._apply_bounce_return(name, gs)
        
        # Lotus sac trigger
        if name == LOTUS:
            self._apply_lotus_sac(gs)

        # Saga enters on Ch I (gains "{T}: Add {C}")
        if name == SAGA:
            pass  # Chapter advancement handled in upkeep()

        gs._log(f"  Placed {name}: +{mana} mana")
        return mana

    def _fetch_land_to_bf(self, name: str, gs: GameState, give_haste=False) -> bool:
        """Find a land by name in library and place it on BF tapped (Amulet untaps)."""
        for i, c in enumerate(gs.zones.library):
            if c.name == name:
                gs.zones.library.pop(i)
                self._place_land_on_bf(c, gs, from_hand=False, give_haste=give_haste)
                return True
        return False

    # ══════════════════════════════════════════════════════════════════
    # LAND PLAY VALUE: which land to play from hand
    # ══════════════════════════════════════════════════════════════════

    def _land_play_value(self, land: Card, gs: GameState) -> float:
        """
        Heuristic value for playing this land NOW.
        Priority:
        1. Bounce land that enables Titan this turn (value 200)
        2. Hanweir when Titan is castable (haste = 2-3 turns saved, value 150)
        3. T1 engine setup (value 100)
        4. Bounce with engine active (value 90)
        5. Untapped permanent mana (value 50-85)
        """
        n = land.name
        am = self._amulets
        repl = self._untap_replacement_active()
        has_titan = any(c.name == TITAN for c in gs.zones.hand)
        has_gsz = any(c.name == ZENITH for c in gs.zones.hand)
        has_pact = any(c.name == PACT for c in gs.zones.hand)
        has_threat = has_titan or has_gsz or has_pact
        pool = gs.mana_pool.total()

        # Chain mana from this land
        if n in BOUNCE_LANDS:
            chain_mana = max(am, 1 if repl else 0) * 2
        elif n == LOTUS and am >= 1:
            chain_mana = am * 3
        elif n == VESTIGE:
            chain_mana = (am + 1) if am > 0 else (1 if repl else 0)
        elif n in ALWAYS_UNTAPPED or n == "Snow-Covered Forest":
            chain_mana = 1
        else:
            chain_mana = max(1, am) if (am > 0 or repl) else 0

        projected = pool + chain_mana

        # ═══ WINNING PLAY: bounce chain → Titan this turn ═══
        if (am > 0 or repl) and has_threat:
            if n in BOUNCE_LANDS and projected >= 6:
                return 200

        # ═══ HANWEIR: play before Titan for haste ═══
        if n == HANWEIR:
            can_cast = (pool >= 6 or projected >= 6)
            if can_cast and has_threat and not self._titan_on_bf:
                return 150
            if self._titan_on_bf and not self._hanweir_on_bf:
                return 140

        # ═══ T1 SPECIAL ═══
        if gs.turn == 1:
            if am > 0 or repl:
                if n in BOUNCE_LANDS:    return 100
                if n == VESTIGE:         return 80 + am
                if n in FOREST_TYPES:    return 30
            else:
                # T1 without Amulet: Saga is BEST (finds Amulet by T3)
                # But only if we have Grazer to put it in (Saga + Grazer = T3 Amulet)
                has_amulet_hand = any(h.name == AMULET for h in gs.zones.hand)
                if n == SAGA and not has_amulet_hand:
                    return 95  # Saga finds Amulet — highest T1 priority without engine
                if n in FOREST_TYPES:    return 90
                if n == BOSEIJU:         return 90
                if n == HANWEIR:         return 85
                if n == URZA_CAVE:       return 85
                if n in BOUNCE_LANDS:    return 10  # tapped, no engine
                if n == SAGA:            return 70  # lower if we already have Amulet

        # ═══ Engine active ═══
        if repl or am > 0:
            if n in BOUNCE_LANDS:        return 90 + am * 5
            if n == LOTUS and am >= 1:   return 85 + am * 3
            if n == VESTIGE:             return 70 + am
            if n == GARDENS:             return 65  # copy Amulet opportunity
            if n == SAGA:                return 60
            if n in ALWAYS_UNTAPPED:     return 50
            if n == LOTUS and am == 0:   return 5

        # ═══ LOTUS FIELD: needs 2 lands to sacrifice ═══
        if n == LOTUS:
            bf_land_count = len([x for x in gs.zones.battlefield if x.is_land()])
            if bf_land_count < 2:
                return -10  # can't sac 2 lands → don't play

        # ═══ BOUNCE LANDS: need at least 1 other land on BF to bounce ═══
        if n in BOUNCE_LANDS:
            bf_land_count = len([x for x in gs.zones.battlefield if x.is_land()])
            if bf_land_count == 0 and not (am > 0 or repl):
                return 10  # enters tapped, bounces nothing useful — very bad

        # ═══ No engine ═══
        if not repl and am == 0:
            if n in ALWAYS_UNTAPPED or n == "Snow-Covered Forest": return 80
            if n == SAGA:                return 60
            if n in BOUNCE_LANDS:        return 20

        return 40

    def _best_land_to_play(self, gs: GameState):
        """Pick the best land from hand to play."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands:
            return None
        return max(lands, key=lambda c: self._land_play_value(c, gs))

    def _play_land(self, gs: GameState) -> bool:
        """Play the best land from hand."""
        if gs.land_played:
            return False
        land = self._best_land_to_play(gs)
        if not land:
            return False
        gs.land_played = True
        self._land_drops_used += 1
        self._place_land_on_bf(land, gs, from_hand=True)
        return True

    # ══════════════════════════════════════════════════════════════════
    # MULLIGAN
    # ══════════════════════════════════════════════════════════════════

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Amulet Titan mulligan — Bible philosophy:
        - "Drawing the first bounceland is often the key to your draw being functional"
        - Speed matters: T3-4 Titan hands are gold
        - 5-land hands are KEEPABLE when they have engine + threat (deck is 40% lands)
        - Saga hands are keepable (T1 Saga → T3 Amulet → T4+ Titan)
        """
        if len(hand) <= 4:
            return True

        lands     = [c for c in hand if c.is_land()]
        engines   = [c for c in hand if c.name in {AMULET, SPELUNKING, SAGA, MINSTREL}]
        amulets   = [c for c in hand if c.name == AMULET]
        bounce    = [c for c in hand if c.name in BOUNCE_LANDS]
        threats   = [c for c in hand if c.name in {TITAN, ZENITH, PACT, SCAPESHIFT}]
        rumbles   = [c for c in hand if c.name == RUMBLE]
        grazers   = [c for c in hand if c.name == GRAZER]
        n_lands   = len(lands)

        # Hard mulls
        if n_lands == 0:                     return False
        if n_lands >= 6:                     return False
        if n_lands == 1 and not on_play:     return False

        # 5-land hands: keep with action (Bible: deck is 40% lands, common and keepable)
        if n_lands == 5:
            has_shift = any(c.name == SCAPESHIFT for c in hand)
            if engines and threats:   return True
            if has_shift:             return True
            if bounce and threats:    return True
            if engines and rumbles:   return True
            if grazers and threats:   return True
            return False

        # Pattern A: T2-3 Titan (Amulet + bounce + threat)
        if amulets and bounce and threats and n_lands >= 2:
            return True
        if len(amulets) >= 2 and bounce:
            return True  # double Amulet + bounce = T2 potential

        # Pattern B: Spelunking hand
        if any(c.name == SPELUNKING for c in hand) and n_lands >= 2 and threats:
            return True

        # Pattern C: Grazer + Amulet + bounce
        if grazers and amulets and bounce and n_lands >= 1:
            return True

        # Pattern D: GSZ hand
        if any(c.name == ZENITH for c in hand) and engines and n_lands >= 2:
            return True

        # Pattern E: Saga hand (slower but consistent)
        if any(c.name == SAGA for c in hand) and n_lands >= 2 and rumbles:
            return True
        if any(c.name == SAGA for c in hand) and n_lands >= 2 and threats:
            return True

        # Pattern F: Rumble/Grazer + bounce + threat (no engine — Rumble finds Amulet)
        if n_lands >= 2 and bounce and threats and (rumbles or grazers):
            return True

        # Pattern G: Multiple bounce + threat
        if n_lands >= 2 and len(bounce) >= 2 and threats:
            return True

        # Pattern H: Scapeshift + lands/engine
        if any(c.name == SCAPESHIFT for c in hand) and n_lands >= 2 and (engines or bounce):
            return True

        # Generic: 2-4 lands + engine + threat
        if 2 <= n_lands <= 4 and engines and (threats or rumbles or grazers):
            return True

        # On mull 1+: keep more liberally
        if mulligans >= 1 and 2 <= n_lands <= 4 and (engines or bounce or threats):
            return True
        if mulligans >= 2 and n_lands >= 1:
            return True

        return False

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """Bottom priority: excess lands > excess Amulets > Pact > high CMC."""
        to_bottom = []
        bounce = [c for c in hand if c.name in BOUNCE_LANDS]
        other_lands = [c for c in hand if c.is_land() and c.name not in BOUNCE_LANDS]
        amulets = [c for c in hand if c.name == AMULET]

        for c in bounce[1:]:
            if len(to_bottom) < n: to_bottom.append(c)
        for c in other_lands[2:]:
            if len(to_bottom) < n: to_bottom.append(c)
        for c in amulets[1:]:
            if len(to_bottom) < n and c not in to_bottom: to_bottom.append(c)
        for c in hand:
            if len(to_bottom) >= n: break
            if c.name == PACT and c not in to_bottom: to_bottom.append(c)

        rest = sorted([c for c in hand if c not in to_bottom and not c.is_land()],
                      key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            to_bottom.append(c)

        return to_bottom[:n]

    # ══════════════════════════════════════════════════════════════════
    # UPKEEP: Pact debt + Saga chapter advancement
    # ══════════════════════════════════════════════════════════════════

    def upkeep(self, gs: GameState):
        """Pay Summoner's Pact debt or lose. Advance Urza's Saga chapters."""
        # Pact debt
        if self._pact_owed and gs.turn > self._pact_turn_cast:
            # Tap lands for mana before trying to pay
            self._tap_all_lands_for_mana(gs)
            if gs.mana_pool.total() >= 4 and gs.mana_pool.G >= 2:
                # Pay {2}{G}{G}: 2 green + 2 generic
                gs.mana_pool.G -= 2
                remaining = 2
                for attr in ('flex', 'C', 'U', 'R', 'B', 'W', 'G'):
                    have = getattr(gs.mana_pool, attr)
                    take = min(have, remaining)
                    if take > 0:
                        setattr(gs.mana_pool, attr, have - take)
                        remaining -= take
                    if remaining <= 0: break
                if remaining <= 0:
                    self._pact_owed = False
                    gs._log("  Pact upkeep: paid {2}{G}{G}")
                else:
                    gs.damage_dealt = -999
                    gs._log("  Pact upkeep: CANNOT PAY — loss!")
            else:
                gs.damage_dealt = -999  # loss
                gs._log("  Pact upkeep: CANNOT PAY — loss!")
                return

        # Urza's Saga: advance chapter for each Saga on BF (per-card tracking)
        saga_cards = [c for c in gs.zones.battlefield if c.name == SAGA]
        for saga in saga_cards:
            entered = getattr(saga, 'turn_entered', gs.turn)
            turns_on_bf = gs.turn - entered
            if turns_on_bf == 1:
                self._resolve_saga_chapter2(gs)
            elif turns_on_bf >= 2:
                self._resolve_saga_chapter3(gs)
                # Saga sacrifices after Ch III
                sid = id(saga)
                gs.zones.battlefield = [c for c in gs.zones.battlefield if id(c) != sid]
                gs.zones.graveyard.append(saga)
                self._track_card_to_gy("enchantment")
                self._track_land_to_gy(SAGA)
                gs._log(f"  Saga: sacrificed after Ch III")
                if not any(c.name == SAGA for c in gs.zones.battlefield):
                    self._saga_on_bf = False
                break

    def _resolve_saga_chapter2(self, gs: GameState):
        """Saga Ch II: Create a Construct artifact creature token (+1/+1 per artifact)."""
        n_artifacts = sum(1 for c in gs.zones.battlefield
                         if 'artifact' in getattr(c, 'type_line', '').lower()
                         or c.name == AMULET or c.name == VEXING
                         or c.name == "Amulet of Vigor (Gardens)")
        pt = max(1, n_artifacts + 1)  # +1 for itself
        token = Card(name="Construct Token", mana_cost="", cmc=0,
                     type_line="Artifact Creature — Construct",
                     oracle_text="Gets +1/+1 for each artifact you control.",
                     power=str(pt), toughness=str(pt), colors=[])
        token.tags.add('creature')
        token.tags.add('artifact')
        token.summoning_sickness = True
        token.turn_entered = gs.turn
        gs.zones.battlefield.append(token)
        self._construct_count += 1
        gs._log(f"  Saga Ch II: {pt}/{pt} Construct token")

    def _update_construct_power(self, gs: GameState):
        """Update Construct tokens and Colossus P/T each turn."""
        n_artifacts = sum(1 for c in gs.zones.battlefield
                         if 'artifact' in getattr(c, 'type_line', '').lower()
                         or c.name == AMULET or c.name == "Amulet of Vigor (Gardens)")
        n_lands = len([x for x in gs.zones.battlefield if x.is_land()])
        for c in gs.zones.battlefield:
            if c.name == "Construct Token":
                pt = max(1, n_artifacts)
                c.power = str(pt)
                c.toughness = str(pt)
            elif c.name == COLOSSUS or c.name == "Colossus Token":
                # Colossus P/T = number of lands you control
                c.power = str(n_lands)
                c.toughness = str(n_lands)

    def _resolve_saga_chapter3(self, gs: GameState):
        """Saga Ch III: Search library for artifact with MV 0-1, put on BF."""
        for target in SAGA_TARGETS:
            for i, c in enumerate(gs.zones.library):
                if c.name == target:
                    gs.zones.library.pop(i)
                    gs.zones.battlefield.append(c)
                    if c.name == AMULET:
                        self._amulets += 1
                        gs._log(f"  Saga Ch III: found Amulet #{self._amulets}!")
                    elif c.name == VEXING:
                        self._vexing_on_bf = True
                        gs._log(f"  Saga Ch III: found Vexing Bauble")
                    return
        gs._log("  Saga Ch III: no artifact found in library")

    # ══════════════════════════════════════════════════════════════════
    # SPELL CASTING: Amulet, Grazer, Spelunking, Rumble, Analyst, etc
    # ══════════════════════════════════════════════════════════════════

    def _try_cast_amulet(self, gs: GameState) -> bool:
        """Cast Amulet of Vigor ({1}). Multiple copies stack for more untap triggers."""
        for c in list(gs.zones.hand):
            if c.name == AMULET and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if gs.cast_spell(c):
                    self._amulets += 1
                    gs._log(f"  Amulet #{self._amulets}")
                    return True
        return False

    def _try_cast_amulet_with_spawn(self, gs: GameState) -> bool:
        """Cast Amulet, using Spawn mana if needed."""
        for c in list(gs.zones.hand):
            if c.name != AMULET: continue
            total = gs.mana_pool.total() + self._spawn_count
            if total >= 1:
                if gs.mana_pool.total() < 1:
                    self._sac_spawn_for_mana(gs, 1)
                if gs.cast_spell(c):
                    self._amulets += 1
                    gs._log(f"  Amulet #{self._amulets}")
                    return True
        return False

    def _try_copy_amulet_with_gardens(self, gs: GameState) -> bool:
        """Mycosynth Gardens: {1}, {T} → copy Amulet. Single → double Amulet!"""
        if not self._gardens_on_bf or self._amulets < 1 or gs.mana_pool.total() < 1:
            return False
        # Pay {1}
        for attr in ('C', 'flex', 'G', 'U', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            if have >= 1:
                setattr(gs.mana_pool, attr, have - 1)
                break
        for c in gs.zones.battlefield:
            if c.name == GARDENS:
                c.name = "Amulet of Vigor (Gardens)"
                c.tapped = True
                break
        self._gardens_on_bf = False
        self._amulets += 1
        gs._log(f"  Gardens: copied Amulet → {self._amulets} Amulets!")
        return True

    def _try_cast_spelunking(self, gs: GameState) -> bool:
        """Spelunking ({2}{G}): ETB draw + put land. Static: lands enter untapped."""
        for c in list(gs.zones.hand):
            if c.name != SPELUNKING: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if gs.cast_spell(c):
                self._spelunking_cnt += 1
                gs._log("  Spelunking: lands enter untapped!")
                # ETB: draw 1
                if gs.zones.library:
                    drawn = gs.zones.library.pop(0)
                    gs.zones.hand.append(drawn)
                    gs._log(f"  Spelunking ETB: drew {drawn.name}")
                # ETB: may put a land from hand onto BF
                # This is a SPECIAL ABILITY, NOT a land drop — doesn't use the land drop!
                land = self._best_land_to_play(gs)
                if land:
                    self._place_land_on_bf(land, gs, from_hand=True)
                    # DON'T set gs.land_played — Spelunking ETB is separate from land drop
                return True
        return False

    def _try_cast_grazer(self, gs: GameState) -> bool:
        """Arboreal Grazer ({G}): 0/3, ETB put land from hand onto BF tapped."""
        for c in list(gs.zones.hand):
            if c.name != GRAZER: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if gs.cast_spell(c):
                c.summoning_sickness = True
                c.turn_entered = gs.turn
                # ETB: put a land
                land = self._best_land_to_play(gs)
                if land:
                    self._place_land_on_bf(land, gs, from_hand=True)
                    # Grazer ETB is an EXTRA land drop (doesn't use normal drop)
                    # But it does count as a drop for chain-limiting purposes
                    self._max_land_drops += 1
                    self._land_drops_used += 1
                    gs.land_played = False  # normal land drop still available
                gs._log("  Grazer: 0/3 + extra land")
                return True
        return False

    def _try_cast_rumble(self, gs: GameState) -> bool:
        """Malevolent Rumble ({1}{G}): reveal 4, keep 1 permanent, rest to GY. +1 Spawn."""
        for c in list(gs.zones.hand):
            if c.name != RUMBLE: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if gs.cast_spell(c):
                revealed = [gs.zones.library.pop(0) for _ in range(min(4, len(gs.zones.library)))]
                if revealed:
                    # Priority: Amulet > Titan > Spelunking > Scapeshift > other permanents
                    priority = [AMULET, TITAN, SPELUNKING, ZENITH, PACT, SCAPESHIFT, ANALYST]
                    kept = None
                    for pn in priority:
                        kept = next((r for r in revealed if r.name == pn), None)
                        if kept: break
                    if not kept:
                        perms = [r for r in revealed if any(t in r.type_line.lower()
                                 for t in ("creature", "artifact", "enchantment", "land"))]
                        kept = max(perms, key=lambda r: r.cmc) if perms else revealed[0]
                    gs.zones.hand.append(kept)
                    revealed.remove(kept)
                    for r in revealed:
                        gs.zones.graveyard.append(r)
                        if r.is_land():
                            self._track_land_to_gy(r.name)
                        else:
                            self._track_card_to_gy(r.type_line)
                    gs._log(f"  Rumble: kept {kept.name}")
                self._spawn_count += 1
                return True
        return False

    def _sac_spawn_for_mana(self, gs: GameState, amount: int = 1):
        """Sacrifice Eldrazi Spawn tokens for {C} mana."""
        use = min(amount, self._spawn_count)
        if use > 0:
            self._spawn_count -= use
            gs.mana_pool.C += use
            gs._log(f"  Sac {use} Spawn: +{use}C")

    def _try_cast_analyst(self, gs: GameState) -> bool:
        """Aftermath Analyst ({1}{G}): 1/3, ETB mill 3."""
        for c in list(gs.zones.hand):
            if c.name != ANALYST: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if gs.cast_spell(c):
                self._analyst_on_bf = True
                c.summoning_sickness = True
                c.turn_entered = gs.turn
                # ETB: mill 3
                for _ in range(min(3, len(gs.zones.library))):
                    milled = gs.zones.library.pop(0)
                    gs.zones.graveyard.append(milled)
                    if milled.is_land():
                        self._track_land_to_gy(milled.name)
                    else:
                        self._track_card_to_gy(milled.type_line)
                gs._log("  Analyst: ETB mill 3")
                return True
        return False

    def _try_sacrifice_analyst(self, gs: GameState) -> bool:
        """Sac Analyst ({3}{G}): return ALL GY lands to BF tapped → Amulet chains."""
        if not self._analyst_on_bf or len(self._lands_in_gy) < 2:
            return False
        total = gs.mana_pool.total() + self._spawn_count
        if total < 4:
            return False
        if gs.mana_pool.total() < 4:
            self._sac_spawn_for_mana(gs, 4 - gs.mana_pool.total())
        if gs.mana_pool.G < 1:
            return False
        # Pay {3}{G}
        gs.mana_pool.G -= 1
        paid = 0
        for attr in ('flex', 'C', 'U', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            take = min(have, 3 - paid)
            if take > 0:
                setattr(gs.mana_pool, attr, have - take)
                paid += take
            if paid >= 3: break

        # Remove Analyst from BF
        for c in list(gs.zones.battlefield):
            if c.name == ANALYST:
                gs.zones.battlefield.remove(c)
                gs.zones.graveyard.append(c)
                self._track_card_to_gy("creature")
                break
        self._analyst_on_bf = False

        # Return ALL GY lands to BF tapped (Amulet untaps)
        gy_lands = [c for c in gs.zones.graveyard if c.is_land()]
        total_mana = 0
        for gl in gy_lands:
            gs.zones.graveyard.remove(gl)
            gl.tapped = False
            gl.turn_entered = gs.turn
            gs.zones.battlefield.append(gl)
            # Mana from Amulet chains
            if gl.name in BOUNCE_LANDS:
                m = self._amulets * 2
            elif gl.name == LOTUS:
                m = self._amulets * 3
            elif gl.name == VESTIGE:
                m = self._amulets + (1 if self._amulets > 0 else 0)
            elif gl.name in ALWAYS_UNTAPPED:
                m = 1
            else:
                m = max(1, self._amulets)
            total_mana += m
            # Add the mana
            if gl.name in BOUNCE_LANDS:
                for _ in range(self._amulets):
                    self._add_land_mana(gl.name, gs)
            elif gl.name == LOTUS:
                for _ in range(self._amulets):
                    gs.mana_pool.G += 3
            else:
                self._add_land_mana(gl.name, gs)
            # Track
            if gl.name == HANWEIR: self._hanweir_on_bf = True
            if gl.name == MIRRORPOOL: self._mirror_on_bf = True

        self._lands_in_gy = []
        gs._log(f"  Analyst sac: returned {len(gy_lands)} lands → +{total_mana} mana")

        # Bounce triggers from returned bounce lands
        for gl in gy_lands:
            if gl.name in BOUNCE_LANDS:
                self._apply_bounce_return(gl.name, gs)

        # Check: did we assemble the Analyst loop?
        self._check_analyst_loop_win(gs)
        return True

    def _check_analyst_loop_win(self, gs: GameState):
        """
        Check if the Analyst infinite loop is assembled.
        Requirements: Amulet + Lotus + (2nd Lotus/Deeps) + Woodland + delirium
        
        Bible: "Each loop costs 5GGG... this nets mana with a second Amulet
        or a second Lotus for infinite mana."
        """
        bf_names = [c.name for c in gs.zones.battlefield if c.is_land()]
        has_lotus = bf_names.count(LOTUS) >= 1 or bf_names.count(ECHOING) >= 1
        has_2nd_field = (bf_names.count(LOTUS) >= 2
                        or (bf_names.count(LOTUS) >= 1 and bf_names.count(ECHOING) >= 1))
        has_woodland = SHIFTING in bf_names
        has_amulet = self._amulets >= 1
        has_delirium = len(self._delirium_types) >= 4
        analyst_in_gy = any(c.name == ANALYST for c in gs.zones.graveyard)
        analyst_available = analyst_in_gy or self._analyst_on_bf

        # Full loop: Amulet + Lotus + 2nd Lotus/Deeps + Woodland + delirium + Analyst
        if (has_lotus and has_2nd_field and has_woodland and has_amulet
                and has_delirium and analyst_available):
            gs._log("  *** ANALYST LOOP ASSEMBLED — INFINITE DAMAGE ***")
            gs.damage_dealt = 999
            return True

        # Partial loop with 2 Amulets: only need 1 Lotus + Woodland
        if (has_lotus and has_woodland and self._amulets >= 2
                and has_delirium and analyst_available):
            gs._log("  *** ANALYST LOOP (2 Amulets) — INFINITE DAMAGE ***")
            gs.damage_dealt = 999
            return True

        return False

    # ══════════════════════════════════════════════════════════════════
    # SUMMONER'S PACT + GREEN SUN'S ZENITH
    # ══════════════════════════════════════════════════════════════════

    def _try_summoners_pact(self, gs: GameState) -> bool:
        """
        Summoner's Pact ({0}): instant, find green creature.
        Must pay {2}{G}{G} next upkeep or lose.
        Bible: "use it when you're winning that same turn"
        Safety: only cast if we can win this turn OR have 4+ lands to pay next turn.
        """
        if self._pact_owed:
            return False
        for c in list(gs.zones.hand):
            if c.name != PACT: continue
            # Safety check — Pact costs {2}{G}{G} next upkeep
            # Need at least 2 green-producing lands + 2 other lands
            bf_lands = [x for x in gs.zones.battlefield if x.is_land()]
            g_sources = sum(1 for x in bf_lands if x.name in FOREST_TYPES
                           or x.name in BOUNCE_LANDS or x.name == SHIFTING
                           or x.name == LOTUS)
            total_lands = len(bf_lands)
            can_pay = total_lands >= 5 and g_sources >= 2
            can_win = (gs.mana_pool.total() + self._spawn_count >= 6
                       and any(h.name == TITAN for h in gs.zones.hand))
            # Also win if Titan is on BF and we have haste
            can_win = can_win or (self._titan_on_bf and self._titan_has_haste)
            if not can_pay and not can_win:
                continue

            if gs.cast_spell(c):
                self._pact_owed = True
                self._pact_turn_cast = gs.turn
                # Find best green creature
                for target in [TITAN, ANALYST, COLOSSUS, GRAZER]:
                    found = next((x for x in gs.zones.library if x.name == target), None)
                    if found:
                        gs.zones.library.remove(found)
                        gs.zones.hand.append(found)
                        gs._log(f"  Pact → {found.name}")
                        return True
        return False

    def _try_green_sun_zenith(self, gs: GameState, x_target: int = 6) -> bool:
        """Green Sun's Zenith ({X}{G}): put green creature MV≤X onto BF."""
        for c in list(gs.zones.hand):
            if c.name != ZENITH: continue
            total = gs.mana_pool.total() + self._spawn_count
            cost = x_target + 1  # X + {G}

            if total >= cost:
                if gs.mana_pool.total() < cost:
                    self._sac_spawn_for_mana(gs, cost - gs.mana_pool.total())
                # Pay
                gs.mana_pool.G = max(0, gs.mana_pool.G - 1)
                remaining = cost - 1
                for attr in ('flex', 'C', 'U', 'R', 'B', 'W', 'G'):
                    have = getattr(gs.mana_pool, attr)
                    take = min(have, remaining)
                    if take > 0:
                        setattr(gs.mana_pool, attr, have - take)
                        remaining -= take
                    if remaining <= 0: break

                gs.zones.hand.remove(c)
                gs.zones.library.append(c)  # Zenith shuffles back

                if x_target >= 6:
                    titan = next((x for x in gs.zones.library if x.name == TITAN), None)
                    if titan:
                        gs.zones.library.remove(titan)
                        gs.zones.battlefield.append(titan)
                        titan.summoning_sickness = True
                        titan.turn_entered = gs.turn
                        self._titan_on_bf = True
                        gs._log("  GSZ X=6 → Titan!")
                        self._titan_etb(gs)
                        if self._titan_has_haste:
                            self._titan_attack(gs)
                        return True
                elif x_target >= 1:
                    grazer = next((x for x in gs.zones.library if x.name == GRAZER), None)
                    if grazer:
                        gs.zones.library.remove(grazer)
                        gs.zones.battlefield.append(grazer)
                        grazer.summoning_sickness = True
                        gs._log("  GSZ X=1 → Grazer")
                        return True
                elif x_target == 0:
                    # Dryad Arbor: 1/1 Forest creature — free ramp + delirium type
                    dryad = next((x for x in gs.zones.library if x.name == DRYAD_ARBOR), None)
                    if dryad:
                        gs.zones.library.remove(dryad)
                        gs.zones.battlefield.append(dryad)
                        dryad.summoning_sickness = True
                        dryad.turn_entered = gs.turn
                        dryad.tags.add('creature')
                        gs._log("  GSZ X=0 → Dryad Arbor (Forest creature)")
                        return True
        return False

    # ══════════════════════════════════════════════════════════════════
    # TITAN: Deploy, ETB, Attack, Fetch Decision Tree
    # ══════════════════════════════════════════════════════════════════

    def _try_deploy_titan(self, gs: GameState) -> bool:
        """Try to cast Titan or find it via Pact/GSZ."""
        if self._titan_on_bf:
            return False
        total = gs.mana_pool.total() + self._spawn_count

        # Direct cast: Titan ({4}{G}{G} = 6 mana)
        for c in list(gs.zones.hand):
            if c.name == TITAN and total >= 6:
                if gs.mana_pool.total() < 6:
                    self._sac_spawn_for_mana(gs, 6 - gs.mana_pool.total())
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    if gs.cast_spell(c):
                        self._titan_on_bf = True
                        self._titan_has_haste = False
                        gs._log("  Primeval Titan cast → ETB trigger")
                        self._titan_etb(gs)
                        if self._titan_has_haste:
                            gs._log("  Titan has haste → attack trigger!")
                            self._titan_attack(gs)
                        return True

        # GSZ for Titan (7 mana)
        if total >= 7 and any(c.name == ZENITH for c in gs.zones.hand):
            return self._try_green_sun_zenith(gs, 6)

        # Pact for Titan (need 6 mana to cast Titan after Pact)
        if total >= 6 and any(c.name == PACT for c in gs.zones.hand):
            if self._try_summoners_pact(gs):
                # Now cast the Titan we just found
                return self._try_deploy_titan(gs)

        return False

    def _titan_fetch_priority(self, gs: GameState, is_etb: bool) -> list[str]:
        """
        Titan ETB/attack: choose 2 lands to fetch.
        
        Full decision tree from the Bible:
        - No Amulet: utility lands (Boseiju, Tolaria West, Saga, etc)
        - 1 Amulet no spare: Hanweir + Vestige (haste + mana for R)
        - 1 Amulet spare mana: Hanweir + Mirrorpool (haste + copy Titan)
        - 2 Amulets: Mirrorpool + Lotus (copy Titan, massive mana)
        """
        hanweir_bf = self._hanweir_on_bf
        mirror_bf = self._mirror_on_bf
        am = self._amulets
        repl = self._untap_replacement_active()
        lib_names = {c.name for c in gs.zones.library}

        def in_lib(n): return n in lib_names

        if is_etb:
            # ETB: first priority = give Titan haste
            if not hanweir_bf and not self._titan_has_haste:
                if in_lib(HANWEIR):
                    # Hanweir needs {R} to activate — MUST pair with R source
                    if am >= 2 and in_lib(MIRRORPOOL):
                        return [HANWEIR, MIRRORPOOL]
                    # Gruul Turf: best (gives {R}{G} directly)
                    if in_lib(GRUUL_TURF):
                        return [HANWEIR, GRUUL_TURF]
                    # Vestige ETB: gives any color (will choose R for haste)
                    if in_lib(VESTIGE):
                        return [HANWEIR, VESTIGE]
                    # No R source available — DON'T fetch Hanweir (no haste = waste)
                    # Fall through to default fetch below

            # Have haste or Hanweir already on BF
            if am >= 2:
                # Double Amulet: Mirrorpool + Lotus for massive chains
                if in_lib(MIRRORPOOL) and not mirror_bf:
                    if in_lib(LOTUS):
                        return [MIRRORPOOL, LOTUS]
                    for bl in [GRUUL_TURF, SIMIC_CHAMBER]:
                        if in_lib(bl):
                            return [MIRRORPOOL, bl]

            # Default: 2 bounce lands for mana
            fetches = []
            for bl in [GRUUL_TURF, SIMIC_CHAMBER, SELESNYA_SANC]:
                if in_lib(bl):
                    fetches.append(bl)
                if len(fetches) == 2:
                    return fetches

            # Fallback: any useful lands
            for util in [VESTIGE, LOTUS if am >= 1 else None, URZA_CAVE, BOSEIJU, FOREST_]:
                if util and in_lib(util) and util not in fetches:
                    fetches.append(util)
                if len(fetches) == 2:
                    return fetches
            return fetches[:2] or [FOREST_]

        else:
            # ATTACK trigger: maximize mana or setup combo
            if not mirror_bf and in_lib(MIRRORPOOL):
                for bl in [GRUUL_TURF, SIMIC_CHAMBER, LOTUS]:
                    if in_lib(bl):
                        return [MIRRORPOOL, bl]

            # Setup Analyst loop: need Lotus + Woodland/Deeps
            if in_lib(LOTUS) and in_lib(SHIFTING):
                return [LOTUS, SHIFTING]
            if in_lib(LOTUS) and in_lib(ECHOING):
                return [LOTUS, ECHOING]

            # Default: more bounce lands
            fetches = []
            for bl in [GRUUL_TURF, SIMIC_CHAMBER, SELESNYA_SANC, VESTIGE, BOSEIJU]:
                if in_lib(bl) and bl not in fetches:
                    fetches.append(bl)
                if len(fetches) == 2:
                    return fetches
            return fetches[:2] or [FOREST_]

    def _titan_etb(self, gs: GameState):
        """Titan ETB: search for 2 lands, put onto BF tapped (Amulet untaps)."""
        fetches = self._titan_fetch_priority(gs, is_etb=True)
        gs._log(f"  Titan ETB: fetching {fetches}")
        for land_name in fetches:
            self._fetch_land_to_bf(land_name, gs)

        # Check haste from Hanweir (already on BF or just fetched)
        if not self._titan_has_haste and self._hanweir_on_bf and not self._hanweir_tapped:
            # Need R mana to activate Hanweir
            if gs.mana_pool.R >= 1:
                gs.mana_pool.R -= 1
                self._activate_haste(gs)
            elif gs.mana_pool.flex >= 1:
                gs.mana_pool.flex -= 1
                self._activate_haste(gs)
            elif gs.mana_pool.C >= 1:
                # Can't use C for R, but check if we have any colored mana
                pass
        self._titan_etb_used = True

    def _activate_haste(self, gs: GameState):
        """Give Titan haste via Hanweir Battlements."""
        self._hanweir_tapped = True
        self._titan_has_haste = True
        for c in gs.zones.battlefield:
            if c.name == TITAN:
                c.tags.add(KWTag.HASTE)
        gs._log("  Hanweir: activated haste!")

    def _titan_attack(self, gs: GameState):
        """Titan attack trigger: fetch 2 more lands. Combat damage is handled by engine."""
        fetches = self._titan_fetch_priority(gs, is_etb=False)
        gs._log(f"  Titan attack trigger: fetching {fetches}")
        for land_name in fetches:
            self._fetch_land_to_bf(land_name, gs)

        # Try Mirrorpool copy of Titan
        if self._mirror_on_bf and not self._mirror_used:
            self._try_mirrorpool_copy(gs)

        # SPEND EXCESS MANA from attack trigger lands
        # The attack fetches lands → Amulet chains → often 10-20+ mana floating
        # Use it for additional threats or combo setup
        pool = gs.mana_pool.total()
        
        # Cast Analyst → sac → return lands → check loop
        if pool >= 6 and not self._analyst_on_bf:
            if self._try_cast_analyst(gs):
                if gs.mana_pool.total() >= 4 and len(self._lands_in_gy) >= 2:
                    self._try_sacrifice_analyst(gs)
                    if gs.damage_dealt >= 20: return

        # Try Scapeshift OHKO with the floating mana
        if gs.mana_pool.total() >= 4:
            if self._try_scapeshift(gs):
                if gs.damage_dealt >= 20: return

        # Cast GSZ for Colossus/extra threat
        if gs.mana_pool.total() >= 7:
            self._try_cast_colossus(gs)

        # Play remaining lands from hand (bounce returns from ETB fetches)
        for _ in range(5):  # max 5 land plays (safety)
            hand_lands = [h for h in gs.zones.hand if h.is_land()]
            if not hand_lands: break
            best = max(hand_lands, key=lambda l: self._land_play_value(l, gs))
            val = self._land_play_value(best, gs)
            if val <= 0: break
            self._place_land_on_bf(best, gs, from_hand=True)

        # Check Analyst loop
        self._check_analyst_loop_win(gs)

    def _try_mirrorpool_copy(self, gs: GameState):
        """Mirrorpool: {4}{C}, {T}, sacrifice → copy Titan → ETB fires (legendary rule kills token)."""
        total = gs.mana_pool.total() + self._spawn_count
        if total < 5:
            return
        if gs.mana_pool.total() < 5:
            self._sac_spawn_for_mana(gs, 5 - gs.mana_pool.total())
        if gs.mana_pool.total() < 5:
            return
        # Pay {4}{C}: deduct 5 from pool
        remaining = 5
        for attr in ('C', 'flex', 'G', 'U', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            take = min(have, remaining)
            if take > 0:
                setattr(gs.mana_pool, attr, have - take)
                remaining -= take
            if remaining <= 0: break

        # Remove Mirrorpool from BF (sacrifice)
        for c in list(gs.zones.battlefield):
            if c.name == MIRRORPOOL:
                gs.zones.battlefield.remove(c)
                gs.zones.graveyard.append(c)
                self._track_land_to_gy(MIRRORPOOL)
                break
        self._mirror_on_bf = False
        self._mirror_used = True

        # Prefer Colossus copy (non-legendary, token survives!)
        colossus_on_bf = any(cc.name == COLOSSUS for cc in gs.zones.battlefield)
        if colossus_on_bf:
            n_lands = len([x for x in gs.zones.battlefield if x.is_land()])
            from data.card import Card
            token = Card.__new__(Card)
            token.name = "Colossus Token"
            token.power = str(n_lands)
            token.toughness = str(n_lands)
            token.type_line = "Creature - Plant Beast"
            token.tags = {'creature'}
            token.summoning_sickness = True
            token.turn_entered = gs.turn
            token.tapped = False
            gs.zones.battlefield.append(token)
            gs._log(f"  Mirrorpool -> Colossus copy! ({n_lands}/{n_lands} token STAYS)")
        else:
            gs._log("  Mirrorpool -> Titan copy! (ETB fires, legendary rule kills token)")
            self._titan_etb(gs)
        gs._log("  Legendary rule: token Titan sacrificed (original stays)")

    # ══════════════════════════════════════════════════════════════════
    # SCAPESHIFT DETERMINISTIC KILL
    # ══════════════════════════════════════════════════════════════════

    def _try_scapeshift(self, gs: GameState) -> bool:
        """
        Scapeshift ({2}{G}{G}): sacrifice lands → fetch that many from library.
        
        Bible: "the Scapeshift OHKO is the single most powerful angle in the deck"
        
        Standard kill (1 Amulet + 4 lands):
        Shift → 2xLotus + bounce + TWest → 9 mana → transmute → Pact → Analyst
        → sac Analyst → return all lands → massive mana → Titan → loop → WIN
        """
        for c in list(gs.zones.hand):
            if c.name != SCAPESHIFT: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            am = self._amulets
            repl = self._untap_replacement_active()
            if am == 0 and not repl:
                continue  # Need Amulet/Spelunking for Shift to generate mana

            bf_lands = [x for x in gs.zones.battlefield if x.is_land()]
            n_lands = len(bf_lands)
            lib_names = {x.name for x in gs.zones.library}
            has_titan_hand = any(h.name in {TITAN, ZENITH, PACT} for h in gs.zones.hand if h is not c)
            has_analyst = (any(h.name == ANALYST for h in gs.zones.library)
                         or any(h.name == ANALYST for h in gs.zones.graveyard)
                         or self._analyst_on_bf)
            n_lotus_lib = sum(1 for x in gs.zones.library if x.name == LOTUS)
            has_twest = TOLARIA in lib_names

            # ═══ PATH A: Full deterministic kill (4+ lands, 1+ Amulet) ═══
            if n_lands >= 4 and am >= 1 and (n_lotus_lib >= 2 or (n_lotus_lib >= 1 and ECHOING in lib_names)):
                has_bounce_lib = any(n in lib_names for n in BOUNCE_LANDS)
                # Path A.1: Full TWest chain (TWest + Pact + Analyst in lib)
                # Path A.2: Direct Analyst (Analyst in hand/GY, skip TWest)
                # Path A.3: Pact in hand (skip TWest, Pact → Analyst)
                has_analyst_hand = any(h.name == ANALYST for h in gs.zones.hand if h is not c)
                has_analyst_gy = any(x.name == ANALYST for x in gs.zones.graveyard)
                has_pact_hand = any(h.name == PACT for h in gs.zones.hand if h is not c)
                has_direct_analyst = has_analyst_hand or has_analyst_gy or has_pact_hand
                can_full_chain = has_bounce_lib and has_twest and has_analyst
                can_direct = has_bounce_lib and has_direct_analyst
                if can_full_chain or can_direct:
                    if gs.cast_spell(c):
                        gs._log("  *** SCAPESHIFT DETERMINISTIC KILL ***")
                        # Sac all lands
                        for sl in bf_lands:
                            if sl in gs.zones.battlefield:
                                gs.zones.battlefield.remove(sl)
                            gs.zones.graveyard.append(sl)
                            self._track_land_to_gy(sl.name)

                        # Fetch: 2xLotus + bounce + TWest
                        fetch_order = []
                        # Get Lotus Fields
                        for lib_c in list(gs.zones.library):
                            if lib_c.name == LOTUS and len([f for f in fetch_order if f.name == LOTUS]) < 2:
                                fetch_order.append(lib_c)
                        if len([f for f in fetch_order if f.name == LOTUS]) < 2:
                            for lib_c in gs.zones.library:
                                if lib_c.name == ECHOING and lib_c not in fetch_order:
                                    fetch_order.append(lib_c); break
                        # Get bounce
                        for bl in BOUNCE_LANDS:
                            for lib_c in gs.zones.library:
                                if lib_c.name == bl and lib_c not in fetch_order:
                                    fetch_order.append(lib_c); break
                            if len(fetch_order) >= 3: break
                        # Get TWest
                        for lib_c in gs.zones.library:
                            if lib_c.name == TOLARIA and lib_c not in fetch_order:
                                fetch_order.append(lib_c); break

                        fetch_order = fetch_order[:min(n_lands, 4)]

                        # Place on BF + generate mana
                        total_mana = 0
                        for ft in fetch_order:
                            gs.zones.library.remove(ft)
                            ft.tapped = False
                            ft.turn_entered = gs.turn
                            gs.zones.battlefield.append(ft)
                            if ft.name == LOTUS:
                                m = am * 3
                                gs.mana_pool.G += m
                            elif ft.name in BOUNCE_LANDS:
                                m = am * 2
                                self._add_land_mana(ft.name, gs)
                                if am > 1:
                                    for _ in range(am - 1):
                                        self._add_land_mana(ft.name, gs)
                            elif ft.name == TOLARIA:
                                gs.mana_pool.U += am
                                m = am
                            else:
                                m = max(1, am)
                                gs.mana_pool.C += m
                            total_mana += m

                        gs._log(f"  Shift fetched {len(fetch_order)} lands, +{total_mana} mana")

                        # Bounce trigger picks up TWest
                        # Lotus sac: sac remaining lands
                        # (simplified: we have massive mana floating)

                        # Try direct Analyst path first (skip TWest chain)
                        analyst_ready = None
                        for h in list(gs.zones.hand):
                            if h.name == ANALYST:
                                analyst_ready = h
                                break
                        if not analyst_ready:
                            # Try Pact → Analyst
                            for h in list(gs.zones.hand):
                                if h.name == PACT:
                                    a = next((x for x in gs.zones.library if x.name == ANALYST), None)
                                    if a:
                                        gs.zones.library.remove(a)
                                        gs.zones.hand.append(a)
                                        analyst_ready = a
                                        self._pact_owed = True
                                        self._pact_turn_cast = gs.turn
                                        gs._log("  Direct Pact → Analyst (skip TWest)")
                                    break

                        if analyst_ready and gs.mana_pool.total() >= 6:
                            # Cast Analyst directly
                            if analyst_ready in gs.zones.hand:
                                gs.mana_pool.G = max(0, gs.mana_pool.G - 1)
                                gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                                gs.zones.hand.remove(analyst_ready)
                                gs.zones.battlefield.append(analyst_ready)
                                self._analyst_on_bf = True
                                for _ in range(min(3, len(gs.zones.library))):
                                    milled = gs.zones.library.pop(0)
                                    gs.zones.graveyard.append(milled)
                                    if milled.is_land(): self._track_land_to_gy(milled.name)
                                    else: self._track_card_to_gy(milled.type_line)
                                gs._log("  Direct Analyst cast + mill 3")
                                if gs.mana_pool.total() >= 4:
                                    self._try_sacrifice_analyst(gs)
                                    self._try_deploy_titan(gs)
                                    self._check_analyst_loop_win(gs)
                                    return True

                        # Fallback: TWest transmute chain
                        if gs.mana_pool.U >= 2 and gs.mana_pool.total() >= 3:
                            gs.mana_pool.U -= 2
                            gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1) if gs.mana_pool.flex > 0 else 0
                            gs.mana_pool.G = max(0, gs.mana_pool.G - 1) if gs.mana_pool.U < 0 else gs.mana_pool.G
                            # Find Pact
                            pact = next((x for x in gs.zones.library if x.name == PACT), None)
                            if pact:
                                gs.zones.library.remove(pact)
                                gs.zones.hand.append(pact)
                                gs._log("  Transmute → Pact")
                            # Pact → Analyst
                            analyst = next((x for x in gs.zones.library if x.name == ANALYST), None)
                            if analyst:
                                gs.zones.library.remove(analyst)
                                gs.zones.hand.append(analyst)
                                self._pact_owed = True
                                self._pact_turn_cast = gs.turn
                                gs._log("  Pact → Analyst")
                                # Cast Analyst
                                if gs.mana_pool.total() >= 2:
                                    gs.mana_pool.G = max(0, gs.mana_pool.G - 1)
                                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                                    gs.zones.hand.remove(analyst)
                                    gs.zones.battlefield.append(analyst)
                                    self._analyst_on_bf = True
                                    # Mill 3
                                    for _ in range(min(3, len(gs.zones.library))):
                                        milled = gs.zones.library.pop(0)
                                        gs.zones.graveyard.append(milled)
                                        if milled.is_land(): self._track_land_to_gy(milled.name)
                                        else: self._track_card_to_gy(milled.type_line)
                                    # Sac Analyst → return all GY lands
                                    if gs.mana_pool.total() >= 4:
                                        self._try_sacrifice_analyst(gs)
                                        # Now try to cast Titan
                                        self._try_deploy_titan(gs)
                                        self._check_analyst_loop_win(gs)
                        return True

            # ═══ PATH B: Ramp shift (Titan in hand, need mana) ═══
            # ONLY use this if we can't reach 6 mana any other way this turn.
            # Scapeshift is too valuable as a kill spell to waste as ramp.
            can_reach_6_naturally = (gs.mana_pool.total() + self._spawn_count >= 6)
            has_grazer_or_spelunk = any(h.name in {GRAZER, SPELUNKING} for h in gs.zones.hand)
            if n_lands >= 2 and am >= 1 and has_titan_hand and not can_reach_6_naturally and not has_grazer_or_spelunk:
                if gs.cast_spell(c):
                    gs._log(f"  Scapeshift ramp: sac {n_lands} lands for Titan mana")
                    sac_ids = {id(sl) for sl in bf_lands}
                    for sl in bf_lands:
                        gs.zones.graveyard.append(sl)
                        self._track_land_to_gy(sl.name)
                    gs.zones.battlefield = [x for x in gs.zones.battlefield if id(x) not in sac_ids]
                    # Fetch Lotus + bounce for 6+ mana
                    fetched = 0
                    for target in [LOTUS, LOTUS, GRUUL_TURF, SIMIC_CHAMBER, VESTIGE]:
                        if fetched >= n_lands: break
                        if self._fetch_land_to_bf(target, gs):
                            fetched += 1
                    self._try_deploy_titan(gs)
                    return True

        return False

    # ══════════════════════════════════════════════════════════════════
    # UTILITY SPELLS: Icetill, Urza's Cave, Tolaria West, Vexing
    # ══════════════════════════════════════════════════════════════════

    def _try_cast_colossus(self, gs: GameState) -> bool:
        """
        Cultivator Colossus ({4}{G}{G}{G} = 7 mana): *//* Trample.
        ETB: repeatedly put land from hand onto BF, draw a card.
        With Amulet: each tapped land untaps → massive mana burst.
        P/T = number of lands you control. Often 8/8+ after chain.
        """
        for card in list(gs.zones.hand):
            if card.name != COLOSSUS: continue
            total = gs.mana_pool.total() + self._spawn_count
            if total < 7: continue
            if gs.mana_pool.total() < 7:
                self._sac_spawn_for_mana(gs, 7 - gs.mana_pool.total())
            if gs.mana_pool.G < 3: continue
            # Pay {4}{G}{G}{G}
            gs.mana_pool.G -= 3
            remaining = 4
            for attr in ('flex', 'C', 'U', 'R', 'B', 'W', 'G'):
                have = getattr(gs.mana_pool, attr)
                take = min(have, remaining)
                if take > 0:
                    setattr(gs.mana_pool, attr, have - take)
                    remaining -= take
                if remaining <= 0: break
            gs.zones.hand.remove(card)
            gs.zones.battlefield.append(card)
            card.summoning_sickness = True
            card.turn_entered = gs.turn
            card.tags.add('creature')
            gs._log("  Cultivator Colossus: ETB chain starting...")
            # ETB: put land from hand → draw → repeat
            chain = 0
            while chain < 30:  # safety
                hand_lands = [h for h in gs.zones.hand if h.is_land()]
                if not hand_lands: break
                # Pick best land to put in
                best = max(hand_lands, key=lambda l: self._land_play_value(l, gs))
                self._place_land_on_bf(best, gs, from_hand=True)
                # Draw a card
                if gs.zones.library:
                    drawn = gs.zones.library.pop(0)
                    gs.zones.hand.append(drawn)
                chain += 1
            # Colossus P/T = lands controlled
            n_lands = len([x for x in gs.zones.battlefield if x.is_land()])
            card.power = str(n_lands)
            card.toughness = str(n_lands)
            gs._log(f"  Colossus: chained {chain} lands, now {n_lands}/{n_lands}")
            return True
        return False

    def _try_cast_icetill(self, gs: GameState) -> bool:
        """Icetill Explorer ({2}{G}{G}): extra land drop + play lands from GY."""
        for c in list(gs.zones.hand):
            if c.name != ICETILL: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if gs.cast_spell(c):
                self._icetill_on_bf = True
                c.summoning_sickness = True
                c.turn_entered = gs.turn
                self._max_land_drops += 1  # Icetill grants +1 land drop per turn
                gs._log("  Icetill: extra land drop + play from GY")
                return True
        return False

    def _try_play_land_from_gy(self, gs: GameState) -> bool:
        """Icetill: play a land from GY (uses a land drop)."""
        if not self._icetill_on_bf or gs.land_played:
            return False
        gy_lands = [c for c in gs.zones.graveyard if c.is_land()]
        if not gy_lands:
            return False
        # Priority: bounce > Lotus > basics
        def gy_val(c):
            if c.name in BOUNCE_LANDS: return 100
            if c.name == LOTUS and self._amulets >= 1: return 90
            if c.name == VESTIGE: return 70
            return 10
        best = max(gy_lands, key=gy_val)
        gs.zones.graveyard.remove(best)
        if best.name in self._lands_in_gy:
            self._lands_in_gy.remove(best.name)
        gs.land_played = True
        self._place_land_on_bf(best, gs, from_hand=False)
        gs._log(f"  Icetill: played {best.name} from GY")
        # Landfall: mill 1
        if gs.zones.library:
            milled = gs.zones.library.pop(0)
            gs.zones.graveyard.append(milled)
            if milled.is_land(): self._track_land_to_gy(milled.name)
            else: self._track_card_to_gy(milled.type_line)
        return True

    def _try_urza_cave(self, gs: GameState) -> bool:
        """Urza's Cave: {3}, {T}, sac → search for any land, put on BF tapped."""
        if gs.mana_pool.total() < 3:
            return False
        cave = next((c for c in gs.zones.battlefield if c.name == URZA_CAVE and not getattr(c, 'tapped', False)), None)
        if not cave:
            return False
        # Pay {3}
        remaining = 3
        for attr in ('C', 'flex', 'G', 'U', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            take = min(have, remaining)
            if take > 0:
                setattr(gs.mana_pool, attr, have - take)
                remaining -= take
            if remaining <= 0: break
        cave.tapped = True
        # Sac Cave
        gs.zones.battlefield.remove(cave)
        gs.zones.graveyard.append(cave)
        self._track_land_to_gy(URZA_CAVE)
        # Fetch best land
        for target in [LOTUS, GRUUL_TURF, SIMIC_CHAMBER, SAGA, SHIFTING, HANWEIR, FOREST_]:
            if self._fetch_land_to_bf(target, gs):
                gs._log(f"  Cave: fetched {target}")
                return True
        return False

    def _try_transmute_tolaria(self, gs: GameState) -> bool:
        """Tolaria West: transmute {1}{U}{U} → find MV 0 card (Pact, land)."""
        if gs.mana_pool.U < 2 or gs.mana_pool.total() < 3:
            return False
        tw = next((c for c in gs.zones.hand if c.name == TOLARIA), None)
        if not tw:
            return False
        # Pay {1}{U}{U}
        gs.mana_pool.U -= 2
        remaining = 1
        for attr in ('flex', 'C', 'G', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            take = min(have, remaining)
            if take > 0:
                setattr(gs.mana_pool, attr, have - take)
                remaining -= take
            if remaining <= 0: break
        gs.zones.hand.remove(tw)
        gs.zones.graveyard.append(tw)
        self._track_land_to_gy(TOLARIA)
        # Find Summoner's Pact (MV 0)
        pact = next((c for c in gs.zones.library if c.name == PACT), None)
        if pact:
            gs.zones.library.remove(pact)
            gs.zones.hand.append(pact)
            gs._log("  Transmute TWest → Pact")
            return True
        gs._log("  Transmute TWest: no Pact found")
        return False

    def _try_vexing_draw(self, gs: GameState) -> bool:
        """Vexing Bauble: {1}, {T}, sac → draw a card."""
        if not self._vexing_on_bf or gs.mana_pool.total() < 1:
            return False
        vex = next((c for c in gs.zones.battlefield if c.name == VEXING), None)
        if not vex: return False
        for attr in ('C', 'flex', 'G', 'U', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            if have >= 1:
                setattr(gs.mana_pool, attr, have - 1)
                break
        gs.zones.battlefield.remove(vex)
        gs.zones.graveyard.append(vex)
        self._vexing_on_bf = False
        self._track_card_to_gy("artifact")
        if gs.zones.library:
            gs.zones.hand.append(gs.zones.library.pop(0))
        gs._log("  Vexing: sac → drew 1")
        return True

    def _try_shifting_woodland(self, gs: GameState) -> bool:
        """Shifting Woodland delirium: {2}{G}{G} → become copy of permanent in GY."""
        if len(self._delirium_types) < 4 or gs.mana_pool.total() < 4 or gs.mana_pool.G < 2:
            return False
        woodland = next((c for c in gs.zones.battlefield if c.name == SHIFTING and not getattr(c, 'tapped', False)), None)
        if not woodland: return False
        titan_in_gy = any(c.name == TITAN for c in gs.zones.graveyard)
        if not titan_in_gy: return False
        # Pay {2}{G}{G}
        gs.mana_pool.G -= 2
        remaining = 2
        for attr in ('flex', 'C', 'U', 'R', 'B', 'W'):
            have = getattr(gs.mana_pool, attr)
            take = min(have, remaining)
            if take > 0:
                setattr(gs.mana_pool, attr, have - take)
                remaining -= take
            if remaining <= 0: break
        # Woodland becomes Titan (can attack immediately — was already on BF)
        woodland.tags.add('creature')
        woodland.tags.add(KWTag.HASTE)
        self._titan_on_bf = True
        gs._log("  Woodland → Titan (delirium, can attack!)")
        return True

    def _try_cast_minstrel(self, gs: GameState) -> bool:
        """The Wandering Minstrel ({1}{G}): lands enter untapped (like cheaper Spelunking)."""
        for c in list(gs.zones.hand):
            if c.name != MINSTREL: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if gs.cast_spell(c):
                self._minstrel_up = True
                c.summoning_sickness = True
                gs._log("  Minstrel: lands enter untapped!")
                return True
        return False

    # ══════════════════════════════════════════════════════════════════
    # CUSTOM LAND TAPPING + RUN_GAME OVERRIDE
    # ══════════════════════════════════════════════════════════════════

    def _tap_all_lands_for_mana(self, gs: GameState):
        """
        Tap all untapped lands for mana using correct per-land amounts.
        Base engine's gs.tap_lands() treats non-basics as 1 flex mana.
        We need: bounce=2, Lotus=3, etc.
        Skip Hanweir if Titan might need haste this turn.
        """
        for c in gs.zones.battlefield:
            if not c.is_land(): continue
            if getattr(c, 'tapped', False): continue
            if c.name == DRYAD_ARBOR and getattr(c, 'summoning_sickness', False): continue
            # Reserve Hanweir for haste
            if c.name == HANWEIR and not self._hanweir_tapped:
                has_threat = any(h.name in {TITAN, ZENITH, PACT} for h in gs.zones.hand)
                if self._titan_on_bf or has_threat:
                    continue
            c.tapped = True
            self._add_land_mana(c.name, gs)

    def run_game(self, mainboard, on_play=True, verbose=False, seed=None, **kwargs):
        """
        Override base run_game to:
        1. Use our custom land tapping (correct mana per land type)
        2. Call self.upkeep() for Pact debt + Saga chapters
        3. Handle the Amulet-specific turn structure
        """
        from engine.game_state import GameState, GameResult, Phase
        from apl.mulligan import take_opening_hand
        import random

        if seed is not None:
            random.seed(seed)

        gs = GameState(mainboard=mainboard, on_play=on_play)
        gs.new_game()
        result = GameResult()
        result.archetype = self.name

        hand, library, mulligans = take_opening_hand(
            deck=mainboard, keep_fn=self.keep, bottom_fn=self.bottom, on_play=on_play
        )
        result.mulligans = mulligans
        result.opening_hand = [c.name for c in hand]
        gs.zones.hand = hand
        gs.zones.library = library
        gs.on_play = on_play

        if verbose:
            print(f"\n--- {self.name} | {'Play' if on_play else 'Draw'} | {mulligans} mull ---")
            print(f"  Opening hand: {result.opening_hand}")

        self.reset_game()

        for _ in range(self.max_turns):
            # Untap, engine upkeep, draw
            gs.run_turn()

            # APL upkeep: Pact debt + Saga chapters
            self.upkeep(gs)
            if gs.damage_dealt <= -900:
                break  # lost to Pact

            # Main Phase 1: custom land tapping + play
            gs.phase = Phase.MAIN1
            self.reset_turn()
            self._tap_all_lands_for_mana(gs)
            self.main_phase(gs)

            if gs.has_won(self.win_condition_damage):
                result.won = True
                result.kill_turn = gs.turn
                if verbose:
                    print(f"  *** Won on turn {gs.turn} ({gs.damage_dealt} damage) ***")
                break

            # Combat
            gs.run_combat()

            if gs.has_won(self.win_condition_damage):
                result.won = True
                result.kill_turn = gs.turn
                if verbose:
                    print(f"  *** Won on turn {gs.turn} ({gs.damage_dealt} damage) ***")
                break

            # Main Phase 2
            gs.phase = Phase.MAIN2
            self.main_phase2(gs)

            # End step
            gs._end()
            result.turn_snapshots.append(gs.snapshot())

            if verbose:
                bf = [c.name for c in gs.zones.battlefield if not c.is_land()]
                print(f"  T{gs.turn} end — {gs.damage_dealt} dmg | BF: {bf}")

            if gs.has_won(self.win_condition_damage):
                result.won = True
                result.kill_turn = gs.turn
                if verbose:
                    print(f"  *** Won on turn {gs.turn} ({gs.damage_dealt} damage) ***")
                break

        result.turn_count = gs.turn
        return result

    # ══════════════════════════════════════════════════════════════════
    # MAIN PHASE: Greedy loop — keep trying actions until none remain
    # ══════════════════════════════════════════════════════════════════

    def main_phase(self, gs: GameState):
        """
        Main phase greedy loop. Core principle from Bible:
        Keep trying actions until no more mana can be spent.
        After EVERY mana-generating action, immediately check if we can
        deploy a win condition (Titan, Scapeshift, Analyst loop).
        
        Priority order:
        1. Deploy win condition (Titan, Scapeshift)
        2. Play land (generates mana via Amulet chains)  
        2.5. Analyst sac (burst mana from GY)
        3. First Amulet (engine piece, must come before land drops)
        4. Grazer (extra land drop = more chain mana)
        5. Spelunking/Minstrel (static untap + draw)
        6. Copy Amulet with Gardens (single → double)
        7. Additional Amulets
        8. Scapeshift (if not already won)
        9. Pact for threat
        10. Rumble (dig for missing piece)
        11. Analyst cast
        12. Icetill Explorer
        13. Woodland delirium attack
        14. Tolaria West transmute
        15. Urza's Cave activation
        16. Vexing Bauble draw
        """
        actions = 0
        MAX_ACTIONS = 40

        # Refresh delirium from actual GY (catches engine-tracked cards)
        self._refresh_delirium(gs)
        # Update Construct power (dynamic: +1/+1 per artifact)
        self._update_construct_power(gs)

        # Pre-loop: cast first Amulet so land drops generate chain mana
        if self._amulets == 0:
            self._try_cast_amulet_with_spawn(gs)

        while actions < MAX_ACTIONS:
            did = False

            # ── 0.3 SCAPESHIFT DETERMINISTIC KILL (highest priority) ──
            # If we have 4+ lands, Amulet, and Shift in hand: try the OHKO first
            if not self._titan_on_bf:
                bf_land_count = len([x for x in gs.zones.battlefield if x.is_land()])
                if bf_land_count >= 4 and self._amulets >= 1:
                    shift_in_hand = any(h.name == SCAPESHIFT for h in gs.zones.hand)
                    if shift_in_hand and gs.mana_pool.total() >= 4:
                        if self._try_scapeshift(gs):
                            did = True; actions += 1
                            if gs.damage_dealt >= 20: return
                            continue

            # ── 0.5 PLAY HANWEIR BEFORE TITAN (haste setup) ──
            if (not gs.land_played and not self._titan_on_bf
                    and not self._hanweir_on_bf
                    and any(h.name == HANWEIR for h in gs.zones.hand)
                    and gs.mana_pool.total() + self._spawn_count >= 6
                    and any(h.name in {TITAN, ZENITH, PACT} for h in gs.zones.hand)):
                # Play Hanweir BEFORE casting Titan so ETB can activate haste
                hanweir = next(h for h in gs.zones.hand if h.name == HANWEIR)
                gs.land_played = True
                self._land_drops_used += 1
                self._place_land_on_bf(hanweir, gs, from_hand=True)
                did = True; actions += 1
                continue

            # ── 1. WIN CONDITION CHECK ──
            if not self._titan_on_bf:
                if self._try_deploy_titan(gs):
                    if gs.damage_dealt >= 20 or gs.damage_dealt == 999:
                        return
                    # Spend excess mana on KILL SPELLS only (not value plays)
                    pool = gs.mana_pool.total()
                    if pool >= 4:
                        self._try_scapeshift(gs)
                        if gs.damage_dealt >= 20: return
                    if pool >= 6 and not self._analyst_on_bf:
                        self._try_cast_analyst(gs)
                        if self._analyst_on_bf and gs.mana_pool.total() >= 4:
                            self._try_sacrifice_analyst(gs)
                            if gs.damage_dealt >= 20: return
                    self._check_analyst_loop_win(gs)
                    if gs.damage_dealt >= 20: return
                    if gs.mana_pool.total() >= 7:
                        self._try_cast_colossus(gs)
                    return  # done — let combat handle the rest
            # Check combo win
            if gs.damage_dealt >= 20 or gs.damage_dealt == 999:
                return

            # ── 2. PLAY LAND ──
            if not gs.land_played:
                if self._play_land(gs):
                    did = True; actions += 1
                    # Icetill: extra land drop
                    if self._icetill_on_bf and not self._extra_land_used:
                        gs.land_played = False
                        self._extra_land_used = True
                    continue

            # ── 2.1 CAST AMULET (immediately after land generates mana) ──
            # Amulet before Grazer/Spelunking so engine is active for their ETBs
            if self._amulets == 0 and gs.mana_pool.total() >= 1:
                if self._try_cast_amulet_with_spawn(gs):
                    did = True; actions += 1; continue

            # ── 2.5 ANALYST SAC (burst mana) ──
            if self._analyst_on_bf and len(self._lands_in_gy) >= 2:
                if gs.mana_pool.total() + self._spawn_count >= 4:
                    if self._try_sacrifice_analyst(gs):
                        did = True; actions += 1
                        if gs.damage_dealt >= 20: return
                        continue

            # ── 3. GRAZER (extra land drop → chain mana) ──
            if self._try_cast_grazer(gs):
                did = True; actions += 1; continue
            
            # ── 3.5 GSZ X=1 for Grazer (ONLY T1-2, save GSZ for Titan later) ──
            if (gs.turn <= 2
                    and self._amulets >= 1
                    and gs.mana_pool.total() >= 2
                    and gs.mana_pool.total() < 6
                    and any(h.name == ZENITH for h in gs.zones.hand)
                    and any(h.name in BOUNCE_LANDS for h in gs.zones.hand)):
                if self._try_green_sun_zenith(gs, 1):
                    did = True; actions += 1; continue

            # ── 4. SPELUNKING ──
            # Without Amulet: Spelunking IS the engine — cast eagerly
            # With Amulet: skip if saving 3 mana → Titan this/next turn
            if self._spelunking_cnt == 0 and not self._minstrel_up:
                should_spelunk = True
                if self._amulets >= 1:
                    has_titan = any(h.name in {TITAN, ZENITH, PACT} for h in gs.zones.hand)
                    if has_titan and gs.mana_pool.total() + self._spawn_count >= 6:
                        should_spelunk = False
                # Without Amulet: ALWAYS cast Spelunking (it's the only engine)
                if should_spelunk:
                    if self._try_cast_spelunking(gs):
                        did = True; actions += 1; continue

            # ── 5. MINSTREL ──
            if not self._minstrel_up and self._spelunking_cnt == 0:
                if self._try_cast_minstrel(gs):
                    did = True; actions += 1; continue

            # ── 6. COPY AMULET WITH GARDENS ──
            if self._gardens_on_bf and self._amulets == 1 and gs.mana_pool.total() >= 1:
                if self._try_copy_amulet_with_gardens(gs):
                    did = True; actions += 1; continue

            # ── 7. ADDITIONAL AMULETS ──
            if gs.mana_pool.total() >= 2 or self._amulets == 0:
                if self._try_cast_amulet_with_spawn(gs):
                    did = True; actions += 1; continue

            # ── 8. SCAPESHIFT ──
            if self._try_scapeshift(gs):
                did = True; actions += 1
                if gs.damage_dealt >= 20: return
                continue

            # ── 9. PACT FOR THREAT ──
            if not self._pact_owed and gs.mana_pool.total() + self._spawn_count >= 6:
                if self._try_summoners_pact(gs):
                    did = True; actions += 1; continue

            # ── 10. RUMBLE ──
            if self._try_cast_rumble(gs):
                did = True; actions += 1; continue

            # ── 11. ANALYST CAST ──
            if not self._analyst_on_bf:
                if self._try_cast_analyst(gs):
                    did = True; actions += 1; continue

            # ── 11.5 CULTIVATOR COLOSSUS (7 mana, chains lands from hand) ──
            if gs.mana_pool.total() + self._spawn_count >= 7 and not self._titan_on_bf:
                if self._try_cast_colossus(gs):
                    did = True; actions += 1; continue

            # ── 11.8 GSZ X=0 for Dryad Arbor (when we need a green source) ──
            if (not gs.land_played and gs.mana_pool.G >= 1
                    and not any(h.is_land() for h in gs.zones.hand)
                    and any(h.name == ZENITH for h in gs.zones.hand)
                    and gs.turn <= 3):
                if self._try_green_sun_zenith(gs, 0):
                    did = True; actions += 1; continue

            # ── 12. ICETILL ──
            if not self._icetill_on_bf:
                if self._try_cast_icetill(gs):
                    did = True; actions += 1; continue

            # ── 12.5 PLAY FROM GY (Icetill) ──
            if self._icetill_on_bf and not gs.land_played:
                if self._try_play_land_from_gy(gs):
                    did = True; actions += 1; continue

            # ── 13. WOODLAND DELIRIUM ──
            if len(self._delirium_types) >= 4:
                if self._try_shifting_woodland(gs):
                    did = True; actions += 1; continue

            # ── 14. TOLARIA TRANSMUTE ──
            if gs.mana_pool.U >= 2 and gs.mana_pool.total() >= 3:
                if self._try_transmute_tolaria(gs):
                    did = True; actions += 1; continue

            # ── 15. URZA'S CAVE ──
            if gs.mana_pool.total() >= 4:
                if self._try_urza_cave(gs):
                    did = True; actions += 1; continue

            # ── 16. VEXING DRAW ──
            if self._try_vexing_draw(gs):
                did = True; actions += 1; continue

            # ── 17. CHECK ANALYST LOOP ──
            self._check_analyst_loop_win(gs)
            if gs.damage_dealt >= 20: return

            if not did:
                break  # nothing left to do

    # ══════════════════════════════════════════════════════════════════
    # MAIN PHASE 2: Post-combat actions
    # ══════════════════════════════════════════════════════════════════

    def main_phase2(self, gs: GameState):
        """
        Post-combat main phase.
        Titan attack trigger (if Titan attacked this turn without haste on ETB turn).
        Try any remaining spells.
        """
        # Titan attack trigger (on subsequent turns when Titan attacks without haste)
        if self._titan_on_bf and not self._titan_has_haste:
            # The attack trigger fires during combat (handled by engine),
            # but we fire the land fetch here for simplicity
            for c in gs.zones.battlefield:
                if c.name == TITAN and not getattr(c, 'summoning_sickness', True):
                    self._titan_attack(gs)
                    break

        # Try deploy Titan if we haven't yet
        if not self._titan_on_bf:
            self._try_deploy_titan(gs)

        # Try Scapeshift with post-combat mana
        if not self._titan_on_bf:
            self._try_scapeshift(gs)

        # Check Analyst loop
        self._check_analyst_loop_win(gs)

    # ══════════════════════════════════════════════════════════════════
    # SIDEBOARD PREMIUM
    # ══════════════════════════════════════════════════════════════════

    def sideboard_premium(self, opponent: str, format_name: str = "modern") -> float:
        opp = opponent.lower()
        if any(x in opp for x in ("living end", "cascade")):
            return 6.0
        if any(x in opp for x in ("affinity", "artifact", "broodscale")):
            return 7.0
        if any(x in opp for x in ("boros energy", "prowess")):
            return -3.0
        if any(x in opp for x in ("control", "blink", "jeskai")):
            return 4.0
        if any(x in opp for x in ("storm", "ruby storm")):
            return 5.0
        if any(x in opp for x in ("goryo", "reanimator")):
            return 5.0
        if "amulet" in opp:
            return 3.0
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Edge Case Registry — from Titan Bible + oracle verification
# ══════════════════════════════════════════════════════════════════════════════
EDGE_CASES = [
    "EC-01: 2 Amulets = 2 untap triggers. Tap between each trigger for N*mana per land.",
    "EC-02: Spelunking is a REPLACEMENT EFFECT. Land never enters tapped → Amulet doesn't trigger.",
    "EC-03: Spelunking + Amulet = effectively 1 Amulet (Spelunking wins, no double-tap).",
    "EC-04: Bounce land SELF-RETURN: with extra land drops, bounce itself and replay for chain mana.",
    "EC-05: Summoner's Pact: must pay {2}{G}{G} next upkeep or lose. Only cast if winning or can pay.",
    "EC-06: Lotus Field hexproof. ETB: sac 2 lands (mandatory). Tap for 3 of any one color.",
    "EC-07: Echoing Deeps CAN copy simultaneously-returning lands (via Analyst). Opposite of Vesuva.",
    "EC-08: Vesuva CANNOT copy simultaneously-entering lands (Titan fetches). Only copies existing BF.",
    "EC-09: Titan ETB: 2 lands enter tapped → Amulet untaps each → tap for mana → bounce triggers.",
    "EC-10: Mirrorpool copy Titan: token ETB fires (2 land fetches), then legendary rule kills token.",
    "EC-11: Scapeshift deterministic kill: 1 Amulet + 4 lands → Shift→2xLotus+bounce+TWest→Pact→Analyst→loop.",
    "EC-12: Analyst loop: Amulet+Lotus+2ndLotus/Deeps+Woodland+delirium = infinite mana/damage.",
    "EC-13: Mycosynth Gardens: {1},{T} → copy Amulet. Single→double Amulet for massive burst.",
    "EC-14: Saga Ch II Constructs: +1/+1 per artifact. With 2 Amulets = 3/3 tokens (free damage).",
    "EC-15: Saga Ch III fires in upkeep 2 turns after placement. Fetches Amulet 94%+ of the time.",
    "EC-16: Hanweir Battlements: {R},{T} → haste. Reserve for Titan (never tap for mana when Titan possible).",
    "EC-17: Shifting Woodland delirium: {2}{G}{G} → becomes Titan copy. Can attack immediately (already on BF).",
    "EC-18: Tolaria West transmute: {1}{U}{U} sorcery speed. Finds Pact (MV 0). Titan→TWest→Pact→next Titan.",
    "EC-19: Crumbling Vestige: ETB adds 1 any color (trigger, separate from tap). Replay via bounce = free mana.",
    "EC-20: Grazer + Vestige = mana-neutral (costs {G}, Vestige ETB gives {G} back).",
    "EC-21: Urza's Cave: {3},{T},sac → any land to BF. Instant-speed Bojuka Bog via Cave.",
    "EC-22: Consign to Memory counters triggered abilities (Amulet untap, Titan ETB, Saga chapters).",
]
