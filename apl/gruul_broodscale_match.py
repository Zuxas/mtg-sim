"""
apl/gruul_broodscale_match.py -- Broodscale Bloodchief (Modern), hand-written.

REPLACES (2026-07-02) the synthetic creature-deck stub of 2026-06-29 (which
played a guessed dork/Grumgully 60 and modeled no combo at all; sim ~89% was
flagged INFLATED/STUB). Deck is now the REAL June-2026 modal list
(decks/gruul_broodscale_modern.txt, 5 top finishes -- see deck header).

COMBO (verified via mtg_meta.db deck_cards; oracle from card knowledge):
  Basking Broodscale ({1}{G} Eldrazi): "Whenever one or more +1/+1 counters
    are put on this creature, create a 0/1 Eldrazi Spawn token ('Sacrifice
    this creature: Add {C}')."  Adapt 1 -- {2}.
  Blade of the Bloodchief ({1} Equipment, equip {1}): "Whenever a creature
    dies, put a +1/+1 counter on equipped creature."
  Loop: Spawn sacs ITSELF for {C} -> dies -> Blade counter on equipped
    Broodscale -> new Spawn -> repeat. Free once started (starter = an
    existing Spawn, or adapt for {2}). Infinite Spawn ETBs + infinite {C}.
  Glaring Fleshraker (colorless Eldrazi): "Whenever you cast a colorless
    spell, create a 0/1 Eldrazi Spawn" + "Whenever another Eldrazi you
    control enters, deal 1 damage to each opponent." With the loop running,
    infinite Spawn ETBs = infinite face damage = the kill.

ENGINE-BOUNDS MODELING (house convention, mirrors apl/yawgmoth_match.py):
  The engine cannot express an unbounded loop; the SANCTIONED idiom is a
  one-shot assembly check that routes lethal through gs.damage_dealt with
  WANTS_BURN=True (a scalar opponent.life write is dropped -- spec spine #3).
  * Loop WITH Fleshraker: gs.damage_dealt += max(20, opp life). Kill.
  * Loop WITHOUT Fleshraker (documented least-fake proxy): the loop is still
    real (infinite mana + arbitrarily large Broodscale) but not an instant
    win, so we BOUND it: Broodscale set to 20/20, +20 {C} to the pool
    (deploys the hand), 3 Spawn tokens. Wins via combat a turn later.
  * Fleshraker chip clock modeled honestly: each colorless CAST makes a real
    Spawn token; each Eldrazi ENTERING pings 1 per Fleshraker (damage_dealt).
  * Urza's Saga: APL-local chapter engine (pattern: apl/affinity_match.py).
    Chapter III tutors a MV<=1 artifact (Blade first) then sacs the Saga.
    Chapter II Constructs NOT modeled (small board undercount for us).
  * Eldrazi Temple: +1 generic per Temple toward ELDRAZI creature casts only
    (manual-cast path). Ugin's Labyrinth imprint mana NOT modeled.
  * Sowing Mycospawn kicker land-tutor, Emrakul extra-turn ETB, and
    opponent interaction with the loop are NOT modeled (known engine class:
    combo-decks-not-sampled / no interaction vs our combo).

Validation gate: mtg_meta.db matchup_matrix 2026-04-24 'Eldrazi Bloodchief
Combo' rows (STALE pre-ban). NOT a tuning target (forbidden); see
mismodeled_matchups.py entry for the calibration verdict.
"""
from apl.match_apl import MatchAPL
from data.card import Tag
from engine.match_state import safe_power, safe_toughness

BROODSCALE = "Basking Broodscale"
BLADE      = "Blade of the Bloodchief"
FLESHRAKER = "Glaring Fleshraker"
STIRRINGS  = "Ancient Stirrings"
RUMBLE     = "Malevolent Rumble"
COMMAND    = "Kozilek's Command"
DEVOURER   = "Devourer of Destiny"
MYCOSPAWN  = "Sowing Mycospawn"
EMRAKUL    = "Emrakul, the Promised End"
SAGA       = "Urza's Saga"
TEMPLE     = "Eldrazi Temple"
BAUBLE     = "Vexing Bauble"
DRUM       = "Springleaf Drum"
LANTERN    = "Soul-Guide Lantern"
MITE       = "Haywire Mite"
SPAWN      = "Eldrazi Spawn Token"

# Eldrazi CREATURES castable via the Temple-discount manual path (colorless).
ELDRAZI_COLORLESS = (FLESHRAKER, MYCOSPAWN, DEVOURER, EMRAKUL)
# Colorless SPELLS (Fleshraker cast-trigger). Broodscale/Stirrings/Rumble are
# green; everything else in the 60 is colorless.
COLORLESS_SPELLS = {BLADE, BAUBLE, DRUM, LANTERN, MITE, COMMAND,
                    FLESHRAKER, MYCOSPAWN, DEVOURER, EMRAKUL}
GREEN_LANDS = ("Forest", "Grove of the Burnwillows", "Boseiju, Who Endures")
# Saga chapter-III tutor priority (all MV<=1 artifacts in the 60).
SAGA_TARGETS = (BLADE, BAUBLE, DRUM, LANTERN, MITE)


class GruulBroodscaleMatchAPL(MatchAPL):
    """Broodscale Bloodchief combo (class name kept for registry stability)."""
    name = "Broodscale Bloodchief"
    ARCHETYPE = "combo"
    WANTS_BURN = True          # combo/ping damage rides gs.damage_dealt
    win_condition_damage = 20
    max_turns = 15
    ATTACK_ALL_IN = False

    # Class-level instrumentation (run_match_set builds a fresh instance per
    # game; an instance counter would not aggregate). Same as yawgmoth.
    _combo_fires = 0

    # Only real creature removal this 75 owns (SB). Kozilek's Command's
    # damage mode is handled in the main loop (modal X spell).
    MATCH_REMOVAL = {"Dismember": (1, 5)}
    MATCH_WIPES = set()
    MATCH_EXILE = set()

    def __init__(self):
        self._combo_fired = False
        self._loop_pumped = False

    # ------------------------------------------------------------------
    # Mulligan: combo piece (Broodscale / Blade / Saga-as-Blade-tutor)
    # + lands, or selection glue that finds them. Green source matters:
    # Broodscale / Stirrings / Rumble are the deck's only green cards.
    # ------------------------------------------------------------------
    def keep(self, hand, mulligans, on_play):
        # Per-game state reset: run_simulation (goldfish) REUSES one APL
        # instance across all games; keep() is called at every game start.
        self._combo_fired = False
        self._loop_pumped = False
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        green_src = sum(1 for c in hand if c.name in GREEN_LANDS)
        combo = sum(1 for c in hand if c.name in (BROODSCALE, BLADE, SAGA))
        dig = sum(1 for c in hand if c.name in (STIRRINGS, RUMBLE, COMMAND))
        # Tier 1: combo piece + 2 lands (Broodscale wants a green source)
        if combo >= 1 and lands >= 2:
            if any(c.name == BROODSCALE for c in hand) and green_src == 0 \
                    and not any(c.name in (BLADE, SAGA) for c in hand):
                pass  # Broodscale-only hand with no green: fall through
            else:
                return True
        # Tier 2: selection glue that can find the combo, on a real mana base
        if dig >= 1 and 2 <= lands <= 4 and (green_src >= 1 or dig >= 2):
            return True
        # Tier 3: at 2+ mulligans keep anything with land + a spell
        return mulligans >= 2

    def bottom(self, hand, n):
        """Bottom Emrakul first (uncastable early), then fat, then excess lands."""
        lands = [c for c in hand if c.is_land()]
        emrakuls = [c for c in hand if c.name == EMRAKUL]
        spells = sorted((c for c in hand if not c.is_land() and c.name != EMRAKUL),
                        key=lambda c: -getattr(c, "cmc", 0))
        pool = emrakuls + lands[4:] + spells
        return pool[:n]

    # ------------------------------------------------------------------
    # Turn structure
    # ------------------------------------------------------------------
    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        self._match_cast_removal(gs, opponent)   # Dismember (post-board)
        self._play_land(gs)
        self._advance_saga(gs)                   # chapter III may fetch Blade
        gs.tap_lands()
        self._cast_selection(gs)                 # Stirrings / Rumble dig
        self._deploy(gs, opponent)               # combo pieces + ramp shell
        self._cast_command(gs, opponent)         # modal utility
        self._check_combo(gs, opponent)          # the sac-loop drain
        self._value_adapt(gs)                    # non-combo adapt chip

    def _play_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        green_on_bf = any(c.name in GREEN_LANDS for c in gs.zones.battlefield
                          if c.is_land())

        def score(c):
            # Need a green source for Broodscale/Stirrings/Rumble first.
            if not green_on_bf and c.name in GREEN_LANDS:
                return 0
            if c.name == SAGA:
                return 1          # start chapters ASAP (Blade tutor)
            if c.name == TEMPLE:
                return 2          # Eldrazi discount
            if c.name in GREEN_LANDS:
                return 3
            return 4              # Ugin's Labyrinth (plain {C} here)
        gs.play_land(min(lands, key=score))

    # ------------------------------------------------------------------
    # Urza's Saga chapter engine (APL-local; pattern: apl/affinity_match.py).
    # Chapter I/II NOT modeled (no {C} bonus, no Constructs -- undercount).
    # Chapter III: tutor MV<=1 artifact -> battlefield, sacrifice the Saga.
    # ------------------------------------------------------------------
    def _advance_saga(self, gs):
        for c in list(gs.zones.battlefield):
            if c.name != SAGA:
                continue
            if getattr(c, "_saga_turn_seen", None) == gs.turn:
                continue
            c._saga_turn_seen = gs.turn
            ch = getattr(c, "_saga_chapter", 0) + 1
            c._saga_chapter = ch
            if ch >= 3:
                self._saga_chapter_three(gs, c)

    def _saga_chapter_three(self, gs, saga):
        have = {x.name for x in gs.zones.battlefield} | \
               {x.name for x in gs.zones.hand}
        want = [n for n in SAGA_TARGETS if n != BLADE or BLADE not in have]
        # Blade first unless already secured; then Bauble > Drum > Lantern > Mite.
        for name in (want if BLADE not in have else
                     [n for n in SAGA_TARGETS if n != BLADE] + [BLADE]):
            tgt = next((x for x in gs.zones.library if x.name == name), None)
            if tgt is not None:
                gs.zones.library.remove(tgt)
                gs.zones.battlefield.append(tgt)
                tgt.turn_entered = gs.turn
                gs._log(f"  Urza's Saga III: tutor {tgt.name} -> battlefield")
                break
        if saga in gs.zones.battlefield:
            gs.zones.battlefield.remove(saga)
            gs.zones.graveyard.append(saga)
        gs._log("  Urza's Saga III: sacrificed Saga")

    # ------------------------------------------------------------------
    # Fleshraker triggers (honest chip clock)
    # ------------------------------------------------------------------
    def _fleshrakers(self, gs):
        return sum(1 for c in gs.zones.battlefield if c.name == FLESHRAKER)

    def _on_eldrazi_enters(self, gs):
        """'Whenever another Eldrazi you control enters, deal 1 to each opp.'"""
        n = self._fleshrakers(gs)
        if n:
            gs.damage_dealt += n
            gs._log(f"  Glaring Fleshraker: Eldrazi entered -> {n} to face")

    def _make_spawn(self, gs):
        tok = gs._make_token(SPAWN, "0", "1", "Creature - Eldrazi Spawn")
        self._on_eldrazi_enters(gs)   # the Spawn itself is an entering Eldrazi
        return tok

    def _after_colorless_cast(self, gs):
        """'Whenever you cast a colorless spell, create a 0/1 Eldrazi Spawn.'"""
        if self._fleshrakers(gs):
            self._make_spawn(gs)

    # ------------------------------------------------------------------
    # Selection: Ancient Stirrings / Malevolent Rumble
    # ------------------------------------------------------------------
    def _piece_priority(self, gs, colorless_only):
        """Missing combo pieces first, then Fleshraker, then land, then fat."""
        have = {c.name for c in gs.zones.battlefield} | \
               {c.name for c in gs.zones.hand}
        prio = []
        if BROODSCALE not in have and not colorless_only:
            prio.append(BROODSCALE)
        if BLADE not in have:
            prio.append(BLADE)
        if FLESHRAKER not in have:
            prio.append(FLESHRAKER)
        return prio

    def _cast_selection(self, gs):
        for c in list(gs.zones.hand):
            if c.name == STIRRINGS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # "Look at top 5, put a colorless card into your hand."
                gs.cast_spell(c)
                top5 = gs.zones.library[:5]
                pick = self._pick_from(gs, top5, colorless_only=True)
                if pick is not None:
                    gs.zones.library.remove(pick)
                    gs.zones.hand.append(pick)
                    gs._log(f"  Ancient Stirrings: take {pick.name}")
                break
        for c in list(gs.zones.hand):
            if c.name == RUMBLE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # "Create a 0/1 Eldrazi Spawn. Look at top 4; put a permanent
                #  card into your hand, rest to graveyard."
                gs.cast_spell(c)
                self._make_spawn(gs)
                top4 = list(gs.zones.library[:4])
                perms = [x for x in top4 if x.has(Tag.CREATURE)
                         or x.has(Tag.ARTIFACT) or x.is_land()]
                pick = self._pick_from(gs, perms, colorless_only=False)
                if pick is None and perms:
                    pick = max(perms, key=lambda x: getattr(x, "cmc", 0))
                for card in top4:
                    if card is pick:
                        gs.zones.library.remove(card)
                        gs.zones.hand.append(card)
                    else:
                        gs.zones.library.remove(card)
                        gs.zones.graveyard.append(card)
                if pick is not None:
                    gs._log(f"  Malevolent Rumble: take {pick.name}")
                break

    def _pick_from(self, gs, cards, colorless_only):
        lands_in_hand = sum(1 for c in gs.zones.hand if c.is_land())
        for name in self._piece_priority(gs, colorless_only):
            hit = next((x for x in cards if x.name == name), None)
            if hit is not None:
                return hit
        if lands_in_hand < 2:
            land = next((x for x in cards if x.is_land()), None)
            if land is not None:
                return land
        pool = [x for x in cards if not x.is_land() and x.name != EMRAKUL]
        if pool:
            return max(pool, key=lambda x: getattr(x, "cmc", 0))
        return None

    # ------------------------------------------------------------------
    # Deployment: combo pieces first, then ramp shell.
    # ------------------------------------------------------------------
    def _temples(self, gs):
        return sum(1 for c in gs.zones.battlefield if c.name == TEMPLE)

    def _cast_eldrazi_manual(self, gs, c):
        """Manual cast for colorless Eldrazi creatures with the Eldrazi Temple
        discount (+1 generic per Temple; Temple's second {C} is otherwise
        unreachable in the 1-tap-1-mana pool model). Emrakul additionally gets
        her own printed discount (1 per card TYPE in our graveyard)."""
        eff = int(getattr(c, "cmc", 0)) - self._temples(gs)
        if c.name == EMRAKUL:
            types = set()
            for x in gs.zones.graveyard:
                for t in ("creature", "artifact", "land", "sorcery",
                          "instant", "enchantment", "planeswalker"):
                    if t in (getattr(x, "type_line", "") or "").lower():
                        types.add(t)
            eff = 13 - len(types) - self._temples(gs)
        eff = max(0, eff)
        if gs.mana_pool.total() < eff:
            return False
        gs.mana_pool.pay(None, eff)
        gs.zones.hand.remove(c)
        gs.zones.battlefield.append(c)
        c.turn_entered = gs.turn
        c.summoning_sickness = True
        gs._log(f"  Cast {c.name} (eff {eff} after Temple/type discounts)")
        self._after_colorless_cast(gs)
        self._on_eldrazi_enters(gs)
        return True

    def _deploy(self, gs, opponent):
        # 1. Broodscale (green, normal cast path) -- the combo body.
        for c in list(gs.zones.hand):
            if c.name == BROODSCALE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if gs.cast_spell(c):
                    self._on_eldrazi_enters(gs)   # Eldrazi Lizard enters
                break
        # 2. Blade ({1} artifact, colorless cast).
        for c in list(gs.zones.hand):
            if c.name == BLADE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if gs.cast_spell(c):
                    self._after_colorless_cast(gs)
                break
        # 3. Fleshraker (Temple-discounted manual path).
        for c in list(gs.zones.hand):
            if c.name == FLESHRAKER:
                self._cast_eldrazi_manual(gs, c)
                break
        # 4. Cheap utility artifacts (colorless casts feed Fleshraker).
        for name in (DRUM, BAUBLE, LANTERN, MITE):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    if gs.cast_spell(c):
                        self._after_colorless_cast(gs)
                    break
        # 5. Ramp top-end, biggest castable first (backup beatdown plan).
        for name in (MYCOSPAWN, DEVOURER, EMRAKUL):
            for c in list(gs.zones.hand):
                if c.name == name:
                    self._cast_eldrazi_manual(gs, c)
                    break

    # ------------------------------------------------------------------
    # Kozilek's Command ({X}{2}, colorless): choose two. Modeled modes:
    # removal (X damage to a creature) when a real threat exists, else dig
    # (top X, take best colorless); always + X Spawn tokens.
    # ------------------------------------------------------------------
    def _cast_command(self, gs, opponent):
        for c in list(gs.zones.hand):
            if c.name != COMMAND:
                continue
            avail = gs.mana_pool.total()
            if avail < 3:      # X >= 1
                return
            x = min(avail - 2, 3)
            tgt = None
            if opponent is not None:
                threats = [t for t in opponent.zones.battlefield
                           if t.has(Tag.CREATURE) and not t.is_land()
                           and safe_power(t) >= 2 and safe_toughness(t) <= x]
                if threats:
                    tgt = max(threats, key=safe_power)
                    x = min(x, max(safe_toughness(t) for t in threats))
                    x = max(x, safe_toughness(tgt))
            gs.mana_pool.pay(None, 2 + x)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            self._after_colorless_cast(gs)
            if tgt is not None and tgt in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(tgt)
                opponent.zones.graveyard.append(tgt)
                gs._log(f"  Kozilek's Command: {x} damage kills {tgt.name}")
            else:
                topx = gs.zones.library[:x]
                pick = self._pick_from(gs, topx, colorless_only=True)
                if pick is not None:
                    gs.zones.library.remove(pick)
                    gs.zones.hand.append(pick)
                    gs._log(f"  Kozilek's Command: dig -> {pick.name}")
            for _ in range(x):
                self._make_spawn(gs)
            return

    # ------------------------------------------------------------------
    # THE COMBO. One-shot assembly check (sanctioned yawgmoth idiom).
    # Needs: Broodscale + Blade on battlefield, equip {1} (once), and a
    # loop starter: an existing Spawn (free) or adapt for {2}.
    # ------------------------------------------------------------------
    def _check_combo(self, gs, opponent):
        if self._combo_fired:
            return
        brood = next((c for c in gs.zones.battlefield if c.name == BROODSCALE), None)
        blade = next((c for c in gs.zones.battlefield if c.name == BLADE), None)
        if brood is None or blade is None:
            return
        has_payoff = self._fleshrakers(gs) > 0
        if not has_payoff:
            if self._loop_pumped:
                return
            # Hold the pump a turn if the payoff is castable soon: firing the
            # bounded no-payoff proxy forecloses the clean lethal line.
            if any(c.name == FLESHRAKER for c in gs.zones.hand) and gs.turn < 6:
                return
        equipped = getattr(blade, "_equipped_uid", None) == id(brood)
        spawn = next((c for c in gs.zones.battlefield if c.name == SPAWN), None)
        loop_running = self._loop_pumped  # pumped earlier = loop already started
        cost = 0 if loop_running else \
            (0 if equipped else 1) + (0 if spawn is not None else 2)
        if gs.mana_pool.total() < cost:
            return
        if cost:
            gs.mana_pool.pay(None, cost)
        blade._equipped_uid = id(brood)
        if not loop_running:
            if spawn is None:
                brood._adapted = True  # adapt 1 was the starter
            else:                       # starter Spawn sacs itself for {C}
                gs.zones.battlefield.remove(spawn)
                gs.zones.graveyard.append(spawn)

        if has_payoff:
            # Infinite Spawn ETBs x Fleshraker ping = lethal. Route through
            # damage_dealt (WANTS_BURN); scalar life writes are dropped.
            opp_life = opponent.life if opponent else 20
            dmg = max(20, opp_life)
            gs.damage_dealt += dmg
            self._combo_fired = True
            type(self)._combo_fires += 1
            gs._log(f"  BROODSCALE/BLOODCHIEF COMBO: Broodscale + Blade "
                    f"+ Fleshraker = {dmg} to face (routed via damage_dealt)")
        else:
            # Loop runs but no damage payoff: BOUNDED proxy (documented in
            # module docstring). Giant Broodscale + mana + Spawn fodder.
            brood.power = "20"
            brood.toughness = "20"
            gs.mana_pool.add("C", 20)
            for _ in range(3):
                self._make_spawn(gs)
            self._loop_pumped = True
            gs._log("  BROODSCALE LOOP (no Fleshraker): Broodscale 20/20, "
                    "+20 {C}, 3 Spawns (bounded proxy for the infinite)")
            self._deploy(gs, opponent)   # spend the mana on the hand

    # ------------------------------------------------------------------
    # Non-combo value adapt: +1/+1 counter -> one Spawn (chip + fodder).
    # Adapt only works while Broodscale has no +1/+1 counters (once).
    # ------------------------------------------------------------------
    def _value_adapt(self, gs):
        if self._combo_fired or self._loop_pumped:
            return
        brood = next((c for c in gs.zones.battlefield
                      if c.name == BROODSCALE
                      and not getattr(c, "_adapted", False)), None)
        if brood is None or gs.mana_pool.total() < 2:
            return
        # Hold adapt mana if Blade is one turn away (in hand) -- the combo
        # start wants the fresh Spawn as its free starter anyway.
        gs.mana_pool.pay(None, 2)
        brood._adapted = True
        try:
            brood.power = str(int(brood.power) + 1)
            brood.toughness = str(int(brood.toughness) + 1)
        except (ValueError, TypeError):
            pass
        self._make_spawn(gs)
        gs._log("  Basking Broodscale: adapt 1 -> +1/+1 and a Spawn")

    # ------------------------------------------------------------------
    # Combat: default race-aware declare_attackers; keep 0/1 Spawns home
    # unless the loop fired (they are mana/fodder, not a clock).
    # ------------------------------------------------------------------
    def declare_attackers(self, gs, opponent):
        attackers = super().declare_attackers(gs, opponent)
        if not self._loop_pumped:
            attackers = [c for c in attackers if c.name != SPAWN]
        return attackers

    def respond_to_spell(self, gs, opponent, spell):
        return None
