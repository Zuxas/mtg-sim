"""apl/izzet_prowess_nick_tokyo_standard_match.py -- Nick Tokyo match APL.

Worldly Counsel post-PT-SOS / RC Tokyo update. Inherits from the existing PT
consensus match APL and overrides:
  - COUNTER_CARDS: only Spell Pierce / Disdainful Stroke / Annul (no Three Steps Ahead)
  - MATCH_REMOVAL: Tokyo SB cards (Slagstorm 2x, Sear, no Sear-main / no Stock Up)
  - MATCHUP_SB_PLANS: per-matchup IN/OUT from primer
  - main_phase_match: layers Furnace removal + Stormchaser L3 + Sauna timing
    on top of the inherited plot-and-burst plan
  - end_step_actions: adds Sauna EOT draw on top of inherited Eddymurk flash

Source primer: Team Resolve/worldly_council_prowess_guide.md
Decklist:     decks/izzet_prowess_nick_tokyo_standard.txt
"""
from apl.izzet_prowess_standard_match import IzzetProwessStandardMatchAPL
from engine.game_state import GameState
from engine.match_state import safe_toughness


class IzzetProwessNickTokyoMatchAPL(IzzetProwessStandardMatchAPL):
    ARCHETYPE = "tempo"

    # Tokyo only runs Spell Pierce as main counter (1 main, 1 SB).
    COUNTER_COST  = 1
    COUNTER_CARDS = {"Spell Pierce", "Disdainful Stroke", "Annul"}

    FLASH_THREATS = {"Eddymurk Crab"}

    MATCH_REMOVAL = {
        "Burst Lightning":   ("R",   2),    # kickered: {4}{R} for 4 dmg
        "Boomerang Basics":  ("U",   None), # FIN Lesson, 1 mana (was wrongly "1U")
        "Eddymurk Crab":     ("UU",  None), # actual cost {5}{U}{U} = 7, often 2-3 after I/S reduction
        # Crab note: 5/5 flash, TAPS up to 2 opp creatures on ETB (does NOT bounce -- parent APL doc is wrong)
        "Roaring Furnace":   ("1R",  None),
        "Get Out":           ("UU",  None),
        "Impractical Joke":  ("R",   3),
        "Prismari Charm":    ("UR",  1),
        "Slagstorm":         ("1RR", 3),
        "Sear":              ("1R",  4),
        "Abrade":            ("1R",  3),
        "Broadside Barrage": ("1UR", None),  # actual cost {1}{U}{R}=3, was wrongly "2R"
        "Bounce Off":        ("U",   None),
        "Annul":             ("U",   None),
    }
    MATCH_WIPES   = {"Slagstorm"}
    MATCH_BOUNCE  = {"Boomerang Basics", "Eddymurk Crab", "Bounce Off", "Get Out"}
    MATCH_EXILE   = set()

    BLINK_TARGETS = {
        "Llanowar Elves",
        "Badgermole Cub",
        "Mightform Harmonizer",
        "Sazh's Chocobo",
        "Icetill Explorer",
        "Voice of Victory",
        "Skycoach Conductor",
        "Gran-Gran",
    }

    _COUNTER_PRIORITY = {
        "Badgermole Cub", "Mightform Harmonizer", "Earthbender Ascension",
        "Sazh's Chocobo", "Lumbering Worldwagon", "Sapling Nursery",
        "Dryadine, Sun's Blessing",
        "Artist's Talent", "Monument to Endurance", "Gran-Gran",
        "High Noon", "Aang, Swift Savior",
        "Doomsday Excruciator", "Omniscience", "North Wind Avatar",
        "Winternight Stories",
    }

    # Categorical SB plans (used by sideboard.py runner when no per-matchup plan matches)
    SB_PLANS = {
        "aggro": (
            ["1 Get Out", "1 Bounce Off", "1 Abrade", "1 Wan Shi Tong, Librarian", "1 Spell Pierce", "1 Sear"],
            ["3 Eddymurk Crab", "1 Spell Pierce", "1 Prismari Charm", "1 Stormchaser's Talent"],
        ),
        "control": (
            ["2 Ral, Crackling Wit", "2 Disdainful Stroke", "1 Wan Shi Tong, Librarian",
             "1 Abrade", "1 Broadside Barrage", "1 Get Out", "1 Spell Pierce"],
            ["4 Slickshot Show-Off", "2 Burst Lightning", "1 Spell Pierce",
             "1 Impractical Joke", "1 Roaring Furnace // Steaming Sauna"],
        ),
        "combo": (
            ["1 Get Out", "1 Bounce Off", "1 Spell Pierce", "1 Disdainful Stroke",
             "1 Abrade", "1 Broadside Barrage"],
            ["3 Eddymurk Crab", "1 Burst Lightning", "1 Impractical Joke",
             "1 Roaring Furnace // Steaming Sauna"],
        ),
        "ramp": (
            ["1 Get Out", "1 Bounce Off", "1 Abrade", "2 Wan Shi Tong, Librarian", "1 Sear"],
            ["3 Eddymurk Crab", "1 Spell Pierce", "1 Prismari Charm", "1 Stormchaser's Talent"],
        ),
        "tempo": (
            ["1 Spell Pierce", "1 Get Out", "2 Disdainful Stroke", "1 Abrade",
             "1 Broadside Barrage", "2 Ral, Crackling Wit"],
            ["4 Slickshot Show-Off", "3 Burst Lightning", "1 Impractical Joke"],
        ),
    }

    # Per-matchup plans (Tokyo update from primer)
    MATCHUP_SB_PLANS = {
        # MGL: lean cuts — Crab is MVP vs wide token board, keep all 4.
        # 2026-05-12 re-tune: was -12pp post-board (cut 3 Crab + 1 Talent =
        # gutted core); reduced to dead-card cuts + 1 utility add.
        "monogreenlandfall": (
            ["1 Get Out", "1 Bounce Off", "1 Abrade", "1 Sear"],
            ["1 Spell Pierce", "1 Prismari Charm", "1 Slickshot Show-Off",
             "1 Impractical Joke"],
        ),
        "selesnyalandfall": (
            ["1 Get Out", "1 Abrade", "1 Sear", "1 Annul"],
            ["1 Spell Pierce", "1 Prismari Charm", "1 Slickshot Show-Off",
             "1 Impractical Joke"],
        ),
        # Mirror: conservative cuts — Slickshot is the 4-of pressure, Burst is
        # the efficient burn. 2026-05-12 re-tune: was -18pp post-board (cut all
        # 4 Slick + 3 Burst); now cut 1 each + bring 1-2 reactive cards.
        "izzetprowessstandard": (
            ["1 Spell Pierce", "1 Disdainful Stroke", "1 Abrade",
             "1 Ral, Crackling Wit"],
            ["1 Slickshot Show-Off", "1 Burst Lightning", "1 Impractical Joke",
             "1 Roaring Furnace // Steaming Sauna"],
        ),
        # Spellementals (already validated at 88.5% post-board, leaving as-is
        # but capping cuts to 2 each to be safe).
        "izzetspellementals": (
            ["1 Spell Pierce", "1 Get Out", "1 Disdainful Stroke",
             "1 Broadside Barrage", "1 Abrade", "1 Ral, Crackling Wit"],
            ["1 Impractical Joke", "2 Burst Lightning", "2 Slickshot Show-Off",
             "1 Flow State"],
        ),
        # Lessons default plan = (on_play, opp_has_talent) per Nick's primer.
        # Use _pick_lessons_sb_plan() for the other 3 variants. Tokyo SB
        # substitutes Vacuum/Snare for Disdainful Stroke / Annul (see
        # LESSONS_SUB_PLANS comment).
        "izzetlessons": (
            ["1 Disdainful Stroke", "1 Spell Pierce", "1 Annul",
             "2 Ral, Crackling Wit", "1 Abrade"],
            ["4 Slickshot Show-Off", "1 Impractical Joke",
             "1 Roaring Furnace // Steaming Sauna"],
        ),
        "izzetlesson": None,  # alias resolved at lookup
        # 7 IN / 7 OUT — balanced. Less aggressive Slickshot cut than before
        # (still 4 in plan was costly per re-tune findings, but vs HN/UW Tempo
        # Slickshot is genuinely dead per primer "can't plot vs T2 HN").
        "azoriushighnoon": (
            ["1 Spell Pierce", "2 Ral, Crackling Wit", "1 Abrade",
             "1 Wan Shi Tong, Librarian", "1 Broadside Barrage", "1 Get Out"],
            ["4 Slickshot Show-Off", "2 Burst Lightning", "1 Impractical Joke"],
        ),
        "azoriustempo": (
            ["1 Spell Pierce", "2 Ral, Crackling Wit", "1 Abrade",
             "1 Wan Shi Tong, Librarian", "1 Broadside Barrage", "1 Get Out"],
            ["4 Slickshot Show-Off", "2 Burst Lightning", "1 Impractical Joke"],
        ),
        "temuromniscience": (
            ["1 Spell Pierce", "1 Disdainful Stroke", "1 Get Out", "1 Bounce Off",
             "1 Abrade", "1 Broadside Barrage"],
            ["3 Eddymurk Crab", "1 Burst Lightning", "1 Impractical Joke",
             "1 Roaring Furnace // Steaming Sauna"],
        ),
        "bantomniscience": (
            ["1 Spell Pierce", "1 Disdainful Stroke", "1 Get Out", "1 Bounce Off",
             "1 Abrade", "1 Broadside Barrage"],
            ["3 Eddymurk Crab", "1 Burst Lightning", "1 Impractical Joke",
             "1 Roaring Furnace // Steaming Sauna"],
        ),
        "dimirexcruciator": (
            ["1 Get Out", "1 Disdainful Stroke", "2 Ral, Crackling Wit", "1 Broadside Barrage"],
            ["3 Burst Lightning", "1 Impractical Joke", "1 Slickshot Show-Off"],
        ),
        "fourcolorelemental": (
            ["1 Abrade", "1 Bounce Off", "1 Disdainful Stroke"],
            ["1 Spell Pierce", "1 Eddymurk Crab", "1 Burst Lightning"],
        ),
        "mardudiscard": (
            ["1 Disdainful Stroke", "1 Abrade", "1 Bounce Off"],
            ["1 Eddymurk Crab", "1 Spell Pierce", "1 Prismari Charm"],
        ),
        "rakdosdiscard": (
            ["1 Disdainful Stroke", "1 Abrade", "1 Bounce Off"],
            ["1 Eddymurk Crab", "1 Spell Pierce", "1 Prismari Charm"],
        ),
        "borosdiscard": (
            ["1 Disdainful Stroke", "1 Abrade", "1 Bounce Off"],
            ["1 Eddymurk Crab", "1 Spell Pierce", "1 Prismari Charm"],
        ),
        "azoriusmomo": (
            ["1 Get Out", "2 Slagstorm", "2 Ral, Crackling Wit",
             "1 Wan Shi Tong, Librarian", "1 Abrade", "1 Broadside Barrage"],
            ["4 Slickshot Show-Off", "2 Eddymurk Crab", "1 Spell Pierce", "1 Flow State"],
        ),

        # Bant/Simic Rhythm: shell of 1/1-2/2 creatures (Llanowar, Gene
        # Pollinator, Spider Manifestation) + Riddler/Ouroboroid finishers.
        # Slagstorm 2-dmg wipes most of the board; Burst Lightning is dead
        # vs token spam. 2026-05-12: covers 9-31% pre-plan matchups.
        # 6 IN / 6 OUT balanced.
        "bantrhythm": (
            ["2 Slagstorm", "1 Sear", "1 Abrade", "1 Get Out", "1 Bounce Off"],
            ["1 Slickshot Show-Off", "2 Burst Lightning",
             "1 Roaring Furnace // Steaming Sauna", "2 Flow State"],
        ),
        "simicrhythm": (
            ["2 Slagstorm", "1 Sear", "1 Abrade", "1 Get Out", "1 Bounce Off"],
            ["1 Slickshot Show-Off", "2 Burst Lightning",
             "1 Roaring Furnace // Steaming Sauna", "2 Flow State"],
        ),

        # Selesnya Ouroboroid: similar wide-board with Llanowar/Pawpatch/
        # Badgermole + 4 Ouroboroid (4/3 lifelink). Slagstorm + Annul (hits
        # Brightglass Gearhulk artifact) + Get Out for value bounce.
        # 6 IN / 6 OUT balanced.
        "selesnyaouroboroid": (
            ["2 Slagstorm", "1 Sear", "1 Abrade", "1 Get Out", "1 Annul"],
            ["1 Slickshot Show-Off", "2 Burst Lightning",
             "1 Impractical Joke", "1 Roaring Furnace // Steaming Sauna",
             "1 Spell Pierce"],
        ),

        # Gruul Ramp/Overlord: structurally hard matchup. Same finding as
        # Looting: maindeck has the best mix of tools for the matchup, every
        # SB pivot tested (Disdainful-heavy / Slagstorm-heavy / Lean removal)
        # regresses by 2-5pp from no-SB at 33.5%. Empty plan = preserve maindeck.
        "gruulaggro": ([], []),
    }

    # ── Lessons sub-plans (Nick's primer, page on Izzet Lessons) ─────
    # MATCHUP_SB_PLANS['izzetlessons'] holds the (play, has_talent) default.
    # The other 3 variants live here. Sims can route via _pick_lessons_sb_plan
    # for finer-grained game-by-game decisions; human pilots reference the
    # printed cheat sheet for which plan applies.
    #
    # Tokyo SB substitutions vs primer text (deck doesn't run Vacuum/Snare):
    #   Ghost Vacuum  -> Disdainful Stroke  (Phlage / Ral counter, role overlap)
    #   Spell Snare   -> Annul              (hits Monument / Talent / Furnace)
    # Pyroclasm not in Tokyo SB; (draw, True) uses Slagstorm (closest substitute).
    LESSONS_SUB_PLANS = {
        # On the play vs Stormchaser's Talent (= default izzetlessons entry)
        ("play", True): (
            ["1 Disdainful Stroke", "1 Spell Pierce", "1 Annul",
             "2 Ral, Crackling Wit", "1 Abrade"],
            ["4 Slickshot Show-Off", "1 Impractical Joke",
             "1 Roaring Furnace // Steaming Sauna"],
        ),
        # On the draw vs Stormchaser's Talent: + sweeper; drop both Furnace + 1 Get Out
        ("draw", True): (
            ["1 Disdainful Stroke", "1 Spell Pierce", "1 Annul",
             "2 Ral, Crackling Wit", "1 Abrade", "1 Slagstorm"],
            ["4 Slickshot Show-Off", "2 Roaring Furnace // Steaming Sauna",
             "1 Get Out"],
        ),
        # On the play vs ZERO Stormchaser's Talent: keep 2 Slickshot, cut Crab
        ("play", False): (
            ["1 Disdainful Stroke", "1 Spell Pierce", "1 Annul",
             "2 Ral, Crackling Wit", "1 Abrade", "1 Get Out"],
            ["2 Slickshot Show-Off", "2 Eddymurk Crab",
             "1 Impractical Joke", "1 Roaring Furnace // Steaming Sauna",
             "1 Prismari Charm"],
        ),
        # On the draw vs ZERO Stormchaser's Talent: leanest IN, drop both Furnace
        ("draw", False): (
            ["1 Disdainful Stroke", "1 Spell Pierce", "1 Annul",
             "2 Ral, Crackling Wit", "1 Abrade"],
            ["2 Slickshot Show-Off", "2 Eddymurk Crab",
             "2 Roaring Furnace // Steaming Sauna"],
        ),
    }

    def _pick_lessons_sb_plan(self, on_play: bool, opp_has_talent: bool = True):
        """Pick the Lessons sub-plan per Nick's primer matrix.

        on_play: True if we're on the play this game.
        opp_has_talent: True if opp's Lessons list runs Stormchaser's Talent.

        Returns (in_list, out_list) — same shape as MATCHUP_SB_PLANS entries.
        """
        key = ("play" if on_play else "draw", bool(opp_has_talent))
        return self.LESSONS_SUB_PLANS[key]

    # ── Mulligan (bypass aware_match_apl.py keep <-> keep_vs_opp recursion bug) ──

    def keep(self, hand, mulligans, on_play):
        """Tokyo mulligan rules per Nick's primer:
          - 0 lands -> mull
          - 1 land + 2+ cantrips on draw -> 95% snap keep
          - 1 land + 0 cantrips -> mull (esp. mirror)
          - 2-4 lands -> keep
          - 5+ lands -> mull (flooded)
          - 5-card hands -> always keep
        Bypasses AwareMatchAPL.keep -> keep_vs_opp -> keep recursion.
        """
        if len(hand) <= 5:
            return True
        lands = sum(1 for c in hand if c.is_land())
        cantrips = sum(1 for c in hand
                       if c.name in ("Opt", "Sleight of Hand", "Flow State",
                                     "Stock Up", "Boomerang Basics", "Prismari Charm"))
        threats = sum(1 for c in hand
                      if c.name in ("Slickshot Show-Off", "Stormchaser's Talent",
                                    "Eddymurk Crab"))
        # Hard floor / ceiling
        if lands == 0 or lands >= 6:
            return False
        # 1-lander rules (per primer)
        if lands == 1:
            if not on_play and cantrips >= 2:
                return True   # 95% snap keep on draw
            if cantrips >= 1 and threats >= 1 and mulligans >= 1:
                return True   # tighter on the play
            return False
        # 2+ lands
        return mulligans >= 2 or threats >= 1 or cantrips >= 2

    def keep_vs_opp(self, hand, mulligans, on_play, opp_key=None):
        """Bypass framework dispatch — go straight to our keep()."""
        return self.keep(hand, mulligans, on_play)

    # ── Crab Control mode (per primer matchup gating) ────────────────
    # vs UW HN, Momo, Jeskai Control, Spellementals (better-crab-deck wins),
    # Izzet Lessons (when they have removal heavy), Dimir Excruciator:
    # commit to Crab Control plan from G1 -- Slickshot is dead, Furnace+Sauna+Talent L3 are key.
    # vs Landfall (MGL/GW), Mirror, Rhythm decks: stay in aggro plan.
    CRAB_CONTROL_MATCHUPS = {
        # vs UW HN / Tempo / Prison: per primer "play Izzet Control from G1, despite dead cards"
        "azoriushighnoon", "azoriustempo", "highnoon", "azoriusprison",
        # vs UW Momo: per primer "this is the matchup where Aggro plan works WORST and Control plan works BEST"
        "azoriusmomo",
        # vs Jeskai Control: dead Slickshots, Sauna is the value engine
        "jeskaicontrol",
        # vs Spellementals: per primer "boils down to who can be the best Eddymurk Crab deck"
        "izzetspellementals",
        # vs Lessons: per primer "you need to keep Slickshot in" — it's HYBRID, not pure CC.
        # Removed -- aggro-leaning by primer
        # vs Dimir Excruciator: per primer "Great matchup. Plot Slickshots until they tap out for Doomsday."
        # HYBRID -- removed (regressed -12pp when forced into CC mode)
    }

    def _in_crab_control_mode(self) -> bool:
        """Return True if the current matchup wants Crab Control plan."""
        opp_key = getattr(self, "_opp_key", "") or ""
        return opp_key in self.CRAB_CONTROL_MATCHUPS

    # ── Get Out modes (engine handler is stubbed) ────────────────────
    # Mode 1: counter target creature/enchantment spell  (handled in respond_to_spell)
    # Mode 2: bounce 1-2 creatures/enchantments you OWN to your hand
    #   Use case: bounce Stormchaser's Talent for prowess re-trigger,
    #             rescue own creature from removal in response, re-ETB Eddymurk
    def _try_cast_get_out_for_value(self, gs: GameState) -> bool:
        """Cast Get Out's mode 2 to bounce own permanent for value (re-ETB / prowess).

        Targets we benefit from bouncing:
          - Stormchaser's Talent (re-cast = +1 Otter token + Lv1 reset)
          - Eddymurk Crab (re-cast = ETB bounces opp creature again)
          - Own creature about to die or with no targets to attack
        """
        get_out = next((c for c in gs.zones.hand if c.name == "Get Out"), None)
        if not get_out:
            return False
        if not gs.mana_pool.can_cast("UU", 2):
            return False
        # Find self-bounce target: prefer Eddymurk (re-ETB), then Stormchaser
        own = [c for c in gs.zones.battlefield
               if c.name in ("Eddymurk Crab", "Stormchaser's Talent")]
        if not own:
            return False
        target = next((c for c in own if c.name == "Eddymurk Crab"),
                      own[0])
        gs.mana_pool.pay("UU", 2)
        gs.zones.hand.remove(get_out)
        gs.zones.graveyard.append(get_out)
        gs.zones.battlefield.remove(target)
        gs.zones.hand.append(target)
        # Reset summoning sickness so a re-cast Eddymurk works
        if hasattr(target, 'summoning_sickness'):
            target.summoning_sickness = True
        # If it's the Class enchantment, reset its level
        if target.name == "Stormchaser's Talent" and hasattr(target, 'counters'):
            target.counters = 0
        gs._log(f"  [Get Out mode 2] bounce own {target.name} for re-ETB / re-trigger")
        return True

    # ── Ral combo-kill detection ─────────────────────────────────────
    # Per primer: T5 Ral cast + uptick → T6 ultimate after enough I/S spells.
    # Burst Lightning kicker {3R} for 4 dmg = the combo enabler.
    # Detect: opp_life small + Ral on board + Burst in hand + sufficient mana.
    def _try_ral_combo_kill(self, gs: GameState, opponent: GameState) -> bool:
        """If Ral ultimate + Burst combo can lethal opponent, fire it.

        Per primer: T5 Ral cast, uptick, T6 ultimate after enough I/S spells.
        Ral oracle: noncreature casts auto-tick +1 loyalty.
        Burst Lightning kicker: {4} additional -> total {4}{R} = 5 mana for 4 dmg.

        MVP: just fire kickered Burst face if opp <= 7 and we have 5 mana.
        Full Ral ultimate sequencing deferred.
        """
        if not opponent:
            return False
        burst = next((c for c in gs.zones.hand if c.name == "Burst Lightning"), None)
        if not burst:
            return False
        if opponent.life > 7:   # need 4 dmg to lethal-range
            return False
        if gs.mana_pool.total() < 5:   # need 5 for {4}{R} kicker
            return False
        if not gs.mana_pool.can_cast("4R", 5):
            return False
        gs.mana_pool.pay("4R", 5)
        gs.zones.hand.remove(burst)
        gs.zones.graveyard.append(burst)
        opponent.life -= 4
        if hasattr(gs, 'damage_dealt'):
            gs.damage_dealt += 4
        gs._log(f"  [Ral combo / Burst kicker] 4 face dmg (opp at {opponent.life})")
        return True

    # ── Helpers (Tokyo additions) ────────────────────────────────────

    def _try_stormchaser_levelup(self, gs: GameState) -> bool:
        """Level up Stormchaser's Talent if on board.

        L2 cost {3}{U} = 4 mana. L3 cost {5}{U} = 6 mana.
        Per primer: L3 is core control finisher in Spellementals/UW HN/Momo.
        Don't level into open opp counter mana.
        """
        from engine.classes import level_up
        sct = next((c for c in gs.zones.battlefield
                    if c.name == "Stormchaser's Talent"), None)
        if not sct:
            return False
        opp_untapped = self._opp_untapped_lands() if hasattr(self, "_opp_untapped_lands") else 0
        if opp_untapped >= 2:
            return False
        leveled = False
        for _ in range(2):
            if level_up(sct, gs):
                leveled = True
            else:
                break
        return leveled

    def _try_cast_furnace(self, gs: GameState, opponent: GameState) -> bool:
        """Cast Roaring Furnace as removal. Engine handler kills the target."""
        from data.card import Tag
        furnace = next((c for c in gs.zones.hand
                        if c.name in ("Roaring Furnace // Steaming Sauna",
                                      "Roaring Furnace / Steaming Sauna")), None)
        if not furnace:
            return False
        if not opponent:
            return False
        hand_size = len(gs.zones.hand)
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        targets = [c for c in opp_creatures if safe_toughness(c) <= hand_size]
        if not targets:
            return False
        if not gs.mana_pool.can_cast(furnace.mana_cost, furnace.cmc):
            return False
        gs.cast_spell(furnace)
        gs._log(f"  [Furnace] cast (hand={hand_size}, killed via engine handler)")
        return True

    def _try_open_sauna(self, gs: GameState) -> bool:
        """Open Steaming Sauna for {3}{U}{U}: no max hand size + draw at EOT.

        Engine doesn't wire Sauna's static effect; APL credits as +1 card on cast
        and persists the room via gs._sauna_draws_active for future EOT draws.
        Don't open if Furnace would be useful as removal first.
        """
        sauna = next((c for c in gs.zones.hand
                      if c.name in ("Roaring Furnace // Steaming Sauna",
                                    "Roaring Furnace / Steaming Sauna")), None)
        if not sauna:
            return False
        if gs.mana_pool.total() < 5:
            return False
        if not gs.mana_pool.can_cast("3UU", 5):
            return False
        gs.mana_pool.pay("3UU", 5)
        gs.zones.hand.remove(sauna)
        gs.zones.battlefield.append(sauna)
        gs._sauna_draws_active = True
        gs.zones.draw(1)
        gs._log(f"  [Sauna] opened ({gs.zones.hand and len(gs.zones.hand) or 0} in hand, +1 immediate)")
        return True

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Layer Furnace removal + Stormchaser L3 + Sauna timing + Get Out value
        + Ral combo on top of the inherited plot-and-burst main phase.

        Crab Control mode (vs UW HN/Momo/Spellementals/Lessons/Dimir):
          - PRIORITIZE Furnace, Sauna, Stormchaser leveling
          - DEPRIORITIZE Slickshot plot/cast (it's "dead" per primer)
          - The inherited plot logic still runs as backup but Furnace+Sauna
            run first, consuming the mana that Slickshot would have used.

        Aggro mode (vs Landfall/Mirror/Rhythm):
          - Run inherited plot-and-burst plan as primary
          - Furnace as opportunistic removal
          - Sauna as fallback grindy plan
        """
        crab_mode = self._in_crab_control_mode()

        # Try Ral combo-kill first -- if it lethals, end here
        if opponent is not None and opponent.life <= 12:
            self._try_ral_combo_kill(gs, opponent)

        # Cast Furnace as removal (highest tempo move when target exists)
        if opponent is not None:
            self._try_cast_furnace(gs, opponent)

        if crab_mode:
            # Crab Control: lead with Sauna / Stormchaser leveling BEFORE plot logic
            # (consumes mana that aggro plan would spend on Slickshot)
            if gs.mana_pool.total() >= 5:
                self._try_open_sauna(gs)
            if gs.turn >= 4 and gs.mana_pool.total() >= 4:
                self._try_stormchaser_levelup(gs)
            # Inherited plot logic still runs but mana is mostly consumed
            super().main_phase_match(gs, opponent)
            # Get Out for value (re-ETB Eddymurk) -- end of phase, opportunistic
            self._try_cast_get_out_for_value(gs)
        else:
            # Aggro mode: inherited plot logic primary, Sauna/Talent as fallback
            super().main_phase_match(gs, opponent)
            if gs.turn >= 5 and gs.mana_pool.total() >= 6:
                self._try_stormchaser_levelup(gs)
            if gs.mana_pool.total() >= 5:
                self._try_open_sauna(gs)

    def end_step_actions(self, gs: GameState, opponent: GameState):
        """Sauna EOT draw + inherited Eddymurk Crab flash logic."""
        if getattr(gs, "_sauna_draws_active", False):
            gs.zones.draw(1)
            gs._log("  [Sauna EOT] draw 1")
        super().end_step_actions(gs, opponent)
