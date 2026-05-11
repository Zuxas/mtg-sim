"""apl/izzet_looting_standard_match.py -- Izzet Looting Standard match APL.

Two-mode plan per McNamara primer + Worldly Counsel framing:
  - **Aggro mode** vs Landfall (pre/post Nursery), Jund Leyline, Mono Red,
    creature-heavy decks: lead Tiger-Seal, deploy on curve, Frostcliff Siege Temur
    (+1/+0 trample haste) closes
  - **Crab-Control mode** vs Spellementals, UW HN/Tempo, Sultai Reanimator,
    control: cantrip + remove, Frostcliff Siege Jeskai (card draw on combat dmg)
    + Stormchaser L3 + Quantum Riddler grinds them out

MATCHUP_SB_PLANS encoded from Team Resolve/guides/looting_sb_plans_verified.md
(every card verified via card_db). Categorical SB_PLANS as fallback.

Sources:
  - mtg-meta-analyzer/scrapers/_verified_sb_cards.txt (oracle text)
  - Team Resolve/guides/looting_store_champ_may2026.md (locked 75)
  - Team Resolve/guides/looting_portland_side_events.md (3-2 field test + 5 opp lists)
  - Team Resolve/handoffs/2026-05-11_post-compact_looting_session.md (full context)
"""
from apl.aware_match_apl import AwareMatchAPL
from apl.izzet_looting_standard import IzzetLootingAPL
from engine.game_state import GameState
from engine.match_state import safe_toughness, safe_power


class IzzetLootingStandardMatchAPL(AwareMatchAPL, IzzetLootingAPL):
    ARCHETYPE = "tempo"

    # Spell Snare {U} cmc=2 only; Annul {U} artifact/enchantment only
    COUNTER_COST  = 1
    COUNTER_CARDS = {"Spell Snare", "Annul", "Disdainful Stroke", "Flashfreeze",
                     "Spell Pierce"}

    # Flash creatures we deploy at end-of-opp-turn
    FLASH_THREATS = {"Tishana's Tidebinder"}   # 3/2 flash, counters ability

    # Removal suite per verified cards. Format: card -> (mana_cost, max_dmg_or_None)
    MATCH_REMOVAL = {
        "Torch the Tower":       ("R",   2),    # 2 dmg / 3 bargained / exiles
        "Burst Lightning":       ("R",   2),    # 2 dmg / kicker {4} for 4 (5 mana total)
        "Pyroclasm":             ("1R",  2),    # 2 dmg each creature (one-sided vs Looting threats)
        "Abrade":                ("1R",  3),    # 3 dmg creature OR destroy artifact
        "Sear":                  ("1R",  4),    # 4 dmg creature/PW -- kills Sapling Nursery 3/4 tokens
        "Boomerang Basics":      ("U",   None), # bounce + draw if owned
        "Into the Flood Maw":    ("U",   None), # bounce creature (any nonland with gift)
        "Roaring Furnace":       ("1R",  None), # dmg = cards in hand to opp creature (McNamara list only)
        "Broadside Barrage":     ("1UR", None), # 5 dmg creature/PW + loot (McNamara SB only)
        "Iroh's Demonstration":  ("1R",  4),    # 1 dmg each opp OR 4 dmg one (McNamara SB only)
        "Tishana's Tidebinder":  ("2U",  None), # counter activated/triggered ability + strip
    }
    MATCH_WIPES   = {"Pyroclasm"}
    MATCH_BOUNCE  = {"Boomerang Basics", "Into the Flood Maw"}
    MATCH_EXILE   = {"Torch the Tower"}   # exiles if would die

    # Pre-combat kill targets (per primer + Portland matchup data)
    BLINK_TARGETS = {
        # MGL / Selesnya Landfall
        "Llanowar Elves",           # MUST die T1 on draw vs MGL
        "Sazh's Chocobo",           # grows with each landfall
        "Badgermole Cub",           # earthbend land + mana bonus
        "Mightform Harmonizer",     # doubles target creature power on landfall
        "Icetill Explorer",         # 2/4 grinds card advantage via mill
        # Lessons / Monument
        "Gran-Gran",                # 1/2 cost-reducer when 3 Lessons in GY
        # UW HN / Tempo
        "Voice of Victory",         # 1/3 -- opp can't cast on your turn
        "Skycoach Conductor",       # 2/3 flash flying with prepared
        "Floodpits Drowner",        # 2/1 flash, ETB tap+stun
        # Reanimator
        "Formidable Speaker",       # 2/4 -- discard for tutor
        "Oblivious Bookworm",       # 2/3 -- end-step draw
    }

    # Counter at any CMC (priority threats):
    _COUNTER_PRIORITY = {
        # MGL / Landfall
        "Sapling Nursery", "Earthbender Ascension", "Mightform Harmonizer",
        "Icetill Explorer", "Hunter's Talent",
        # Lessons / Monument
        "Artist's Talent", "Monument to Endurance", "Gran-Gran",
        "Stormchaser's Talent",
        # UW HN / Tempo
        "High Noon", "Voice of Victory", "Aven Interrupter",
        "Aang, Swift Savior", "Airbender Ascension",
        # Reanimator
        "Bringer of the Last Gift", "Overlord of the Balemurk",
        "Awaken the Honored Dead", "Superior Spider-Man",
        # Mirror
        "Quantum Riddler", "Eddymurk Crab", "Frostcliff Siege",
        # Combo / control finishers
        "Doomsday Excruciator", "Omniscience",
        # Aggro engines
        "Leyline of Resonance",
    }

    # ── Crab Control mode (per primer matchup gating) ────────────────
    # Matchups where Looting wants the slow grind plan from G1.
    # Aggro plan stays default for Landfall (race), Jund Leyline, Mono Red, mirror.
    CRAB_CONTROL_MATCHUPS = {
        # vs Spellementals: better Crab/Riddler deck wins
        "izzetspellementals",
        # vs UW HN / Tempo / Prison: Tiger-Seal walls but Riddler-Frostcliff Jeskai is the kill
        "azoriushighnoon", "azoriustempo", "highnoon", "azoriusprison",
        # vs UW Momo (RiP shuts Lantern, Sauna substitute = Frostcliff Siege Jeskai card draw)
        "azoriusmomo",
        # vs Jeskai Control
        "jeskaicontrol",
        # vs Sultai Reanimator (per primer "We are an excellent deck at mulliganing"
        # but the path to win is Tidebinder + counters, not race)
        "sultaireanimator",
    }

    def _in_crab_control_mode(self) -> bool:
        opp_key = getattr(self, "_opp_key", "") or ""
        return opp_key in self.CRAB_CONTROL_MATCHUPS

    # ── Frostcliff Siege mode selection ──────────────────────────────
    # Jeskai (card draw on combat dmg) in grindy matchups + Crab Control mode.
    # Temur (+1/+0 trample haste) in racing/aggro matchups.
    SIEGE_JESKAI_MATCHUPS = CRAB_CONTROL_MATCHUPS | {
        "izzetlessons", "izzetlesson", "dimirexcruciator",
        "izzetprowessstandard", "izzetprowessstandardtokyo",  # mirror = grindy
    }

    def _siege_jeskai_mode(self) -> bool:
        opp_key = getattr(self, "_opp_key", "") or ""
        return opp_key in self.SIEGE_JESKAI_MATCHUPS

    # ── Categorical SB plans (fallback when MATCHUP_SB_PLANS misses) ──
    SB_PLANS = {
        "aggro": (
            ["3 Pyroclasm", "2 Abrade", "2 Sear", "2 Flashfreeze"],
            ["2 Spell Snare", "2 Frostcliff Siege", "2 Stormchaser's Talent",
             "1 Ghost Vacuum"],
        ),
        "control": (
            ["2 Annul", "1 Disdainful Stroke", "1 Tishana's Tidebinder",
             "1 Soul-Guide Lantern"],
            ["2 Burst Lightning", "3 Torch the Tower"],
        ),
        "combo": (
            ["1 Soul-Guide Lantern", "1 Ghost Vacuum", "1 Disdainful Stroke",
             "1 Tishana's Tidebinder", "2 Annul", "1 Flashfreeze"],
            ["3 Torch the Tower", "2 Burst Lightning", "2 Frostcliff Siege"],
        ),
        "ramp": (
            ["3 Pyroclasm", "2 Sear", "2 Annul", "1 Flashfreeze"],
            ["2 Spell Snare", "2 Burst Lightning", "2 Frostcliff Siege",
             "1 Tiger-Seal"],
        ),
        "tempo": (
            ["2 Abrade", "1 Disdainful Stroke", "1 Tishana's Tidebinder",
             "1 Pyroclasm"],
            ["2 Burst Lightning", "1 Frostcliff Siege", "1 Tiger-Seal",
             "1 Stormchaser's Talent"],
        ),
    }

    # ── Per-matchup SB plans (verified, from looting_sb_plans_verified.md) ──
    MATCHUP_SB_PLANS = {
        # Izzet Lessons / Monument (HIGH confidence -- Portland-tested + verified)
        # Plan optimized for Lessons; Monument similar.
        "izzetlessons": (
            ["2 Annul", "2 Abrade", "1 Ghost Vacuum", "1 Soul-Guide Lantern"],
            ["2 Burst Lightning", "1 Frostcliff Siege", "3 Torch the Tower"],
        ),
        "izzetlesson": (
            ["2 Annul", "2 Abrade", "1 Ghost Vacuum", "1 Soul-Guide Lantern"],
            ["2 Burst Lightning", "1 Frostcliff Siege", "3 Torch the Tower"],
        ),

        # Izzet Prowess (post-Cori-Steel) -- MEDIUM confidence
        # Annul misses Flow State (sorcery), misses Eddymurk Crab (creature)
        "izzetprowessstandard": (
            ["2 Abrade", "1 Disdainful Stroke", "1 Tishana's Tidebinder"],
            ["2 Burst Lightning", "1 Frostcliff Siege", "1 Tiger-Seal"],
        ),
        "izzetprowessstandardtokyo": (
            ["2 Abrade", "1 Disdainful Stroke", "1 Tishana's Tidebinder"],
            ["2 Burst Lightning", "1 Frostcliff Siege", "1 Tiger-Seal"],
        ),

        # Selesnya Landfall: keep Snare in (hits Badgermole / Llanowar cmc 2),
        # bring Abrade instead of Annul (more flexible). 2026-05-12 A/B beat
        # original by +1.5pp (29.5% -> 31.0%). Still a bad matchup; G1 31.5%
        # is the floor (sim says SB barely helps).
        "selesnyalandfall": (
            ["3 Pyroclasm", "2 Sear", "2 Abrade", "1 Flashfreeze"],
            ["2 Burst Lightning", "2 Frostcliff Siege",
             "2 Stormchaser's Talent", "1 Tiger-Seal", "1 Ghost Vacuum"],
        ),

        # Mono-Green Landfall (post-Sapling-Nursery) -- MEDIUM confidence
        # Sear kills the 3/4 reach Treefolk tokens. Annul on stack stops Nursery.
        "monogreenlandfall": (
            ["3 Pyroclasm", "2 Sear", "2 Annul", "2 Flashfreeze"],
            ["2 Spell Snare", "2 Burst Lightning", "2 Frostcliff Siege",
             "1 Ghost Vacuum", "2 Tiger-Seal"],
        ),

        # Gruul Ramp/Overlord (not classic aggro — the deck plays 2+ toughness
        # creatures + 4-of Overlord 5/4-6/6 bodies). Looting is structurally
        # bad here (G1 40.5%) and every SB pivot makes it WORSE:
        #   - Pyroclasm 2-dmg only kills Llanowar Elves (dead vs Overlords)
        #   - Cutting Talent/Frostcliff for removal drops below break-even
        #   - Tested 5 dedicated plans, all 29-37% vs no-SB at 39%
        # 2026-05-12: explicit empty plan = keep maindeck, sideboarding hurts.
        # Human pilot: trust your reads; sim says don't change anything.
        "gruulaggro": ([], []),
        # Mono Red Aggro: bring full burn/wipe package (Pyroclasm hits MR
        # weenie curve), drop slow engine. 8 IN / 8 OUT balanced.
        "monoredaggro": (
            ["3 Pyroclasm", "2 Sear", "2 Abrade", "1 Flashfreeze"],
            ["2 Spell Snare", "2 Frostcliff Siege", "2 Stormchaser's Talent",
             "1 Ghost Vacuum", "1 Burst Lightning"],
        ),
        # Mono Green Aggro: similar but +1 Flashfreeze (counters Sapling, etc.)
        # 9 IN / 9 OUT balanced.
        "monogreenaggro": (
            ["3 Pyroclasm", "2 Sear", "2 Abrade", "2 Flashfreeze"],
            ["2 Spell Snare", "2 Frostcliff Siege", "2 Stormchaser's Talent",
             "1 Ghost Vacuum", "1 Burst Lightning", "1 Boomerang Basics"],
        ),

        # Sultai Reanimator -- MEDIUM confidence (Portland 1-2 loss; refined post-event)
        # Tidebinder is MVP -- counters Bringer ETB, Spider-Man Mind Swap, Craterhoof ETB
        "sultaireanimator": (
            ["1 Soul-Guide Lantern", "1 Ghost Vacuum", "1 Disdainful Stroke",
             "1 Tishana's Tidebinder", "2 Annul", "1 Flashfreeze"],
            ["3 Torch the Tower", "2 Burst Lightning", "2 Frostcliff Siege"],
        ),

        # Dimir Excruciator: 2026-05-12 A/B test showed every dedicated SB
        # plan regresses vs NONE (43.5% Current / 46% NONE / 39-40% other
        # variants). Maindeck has the right tools — Tiger-Seal exiles
        # Excruciator on cast, Boomerang bounces Spider-Man. Empty plan.
        "dimirexcruciator": ([], []),

        # Simic Rhythm: same finding — Looting's burn+bounce package is
        # already the right shape; SB pivots regress (24-25% vs NONE 27.5%).
        # The deck's wide-board + Ouroboroid lifelink is just hard for tempo.
        # Empty plan = explicit "don't sideboard, this matchup is what it is".
        "simicrhythm": ([], []),

        # UW Tempo (Crab Control mode) -- MEDIUM confidence
        # Their threats are 2-toughness flash creatures (Voice 1/3 lives Pyroclasm,
        # Drowner 2/1 dies); main plan is counter-wars. Bring counters + Tidebinder
        # to neutralize Voice/Drowner ETB+trigger, cut slow/dead cards.
        # 6 IN / 6 OUT balanced. (was 6 IN / 6 OUT but Sear was a typo — not in main.)
        "azoriustempo": (
            ["2 Annul", "1 Disdainful Stroke", "1 Tishana's Tidebinder",
             "2 Flashfreeze"],
            ["2 Burst Lightning", "1 Frostcliff Siege",
             "2 Into the Flood Maw", "1 Stormchaser's Talent"],
        ),

        # Jeskai Control -- MEDIUM confidence
        # Counter their Sunfall (cmc 5 -> Disdainful Stroke), bait counters with
        # cheap threats, Tidebinder for planeswalker abilities. Cut dead 2-mana
        # counter (Snare misses cmc 4+ Sunfall) + dead burn (no creatures).
        # 6 IN / 6 OUT balanced. (Pyroclasm/Sear typos removed — those are SB cards.)
        "jeskaicontrol": (
            ["1 Disdainful Stroke", "1 Tishana's Tidebinder", "2 Flashfreeze",
             "2 Abrade"],
            ["2 Spell Snare", "2 Burst Lightning", "1 Tiger-Seal",
             "1 Frostcliff Siege"],
        ),

        # Izzet Spellementals (Crab Control mode) -- MEDIUM confidence
        # Mirror-like vs UR spell-heavy shell. GY hate for Phlage recursion is huge.
        # Flashfreeze counters Crab/Hearth/Phlage; Tidebinder strips their Talent.
        # 2026-05-12 A/B: light swap (keep Snare/Tiger-Seal in) beats aggressive
        # cut by +4.5pp (84% vs 79.5%). Tiger-Seal is the 1-drop snap-keep;
        # Snare hits Crab (cmc 2). Cut only redundant/slow stuff.
        # 6 IN / 6 OUT balanced.
        "izzetspellementals": (
            ["1 Soul-Guide Lantern", "1 Ghost Vacuum", "1 Disdainful Stroke",
             "1 Tishana's Tidebinder", "2 Flashfreeze"],
            ["2 Burst Lightning", "2 Frostcliff Siege", "1 Boomerang Basics",
             "1 Stormchaser's Talent"],
        ),
    }


    # ── Helpers ──────────────────────────────────────────────────────

    def keep(self, hand, mulligans, on_play):
        """Looting mulligan rules per McNamara primer:
          - Tiger-Seal is the 1-drop snap-keep anchor on the play
          - 1-lander OK on draw with cantrips/Boomerang
          - Mirror requires cantrip-heavy hands
          - Threat-less hands need Frostcliff/Stormchaser engine pieces
        Bypasses AwareMatchAPL keep/keep_vs_opp recursion (per session 2026-05-10 fix).
        """
        if len(hand) <= 5:
            return True
        lands = sum(1 for c in hand if c.is_land())
        cantrips = sum(1 for c in hand
                       if c.name in ("Boomerang Basics", "Into the Flood Maw",
                                     "Winternight Stories"))
        threats = sum(1 for c in hand
                      if c.name in ("Tiger-Seal", "Duelist of the Mind",
                                    "Fear of Missing Out", "Quantum Riddler",
                                    "Stormchaser's Talent"))
        engines = sum(1 for c in hand
                      if c.name in ("Frostcliff Siege", "Stormchaser's Talent",
                                    "Quantum Riddler"))
        # Hard floor / ceiling
        if lands == 0 or lands >= 6:
            return False
        # 1-lander rules
        if lands == 1:
            if not on_play and cantrips >= 2:
                return True   # snap keep on draw with double cantrip
            if cantrips >= 1 and threats >= 1 and mulligans >= 1:
                return True
            return False
        # 2+ lands
        if mulligans >= 2:
            return True
        return threats >= 1 or (engines >= 1 and cantrips >= 1)

    def keep_vs_opp(self, hand, mulligans, on_play, opp_key=None):
        """Bypass framework keep/keep_vs_opp recursion."""
        return self.keep(hand, mulligans, on_play)

    def _try_riddler_warp(self, gs: GameState, opponent: GameState) -> bool:
        """Cast Quantum Riddler for warp cost {1}{U} = early-tempo 4/6 flier
        with ETB-draw. Per primer: warp = aggressive cast; hardcast late = inevitability.

        Decision: warp if {1}{U} available + not in Crab Control mode (where we
        prefer hardcasting for inevitability).
        """
        if self._in_crab_control_mode():
            return False   # save for hardcast inevitability
        riddler = next((c for c in gs.zones.hand if c.name == "Quantum Riddler"), None)
        if not riddler:
            return False
        if not gs.mana_pool.can_cast("1U", 2):
            return False
        # Engine wires warp via gs.cast_spell_warp per memory session 2026-05-07
        if hasattr(gs, "cast_spell_warp"):
            try:
                gs.cast_spell_warp(riddler)
                gs._log("  [Riddler warp] cast for {1}{U} = 4/6 flying, ETB draw")
                return True
            except Exception:
                pass
        return False

    def _frostcliff_siege_mode_choice(self) -> str:
        """Return 'jeskai' or 'temur' per matchup gating."""
        return "jeskai" if self._siege_jeskai_mode() else "temur"

    def _try_stormchaser_levelup(self, gs: GameState) -> bool:
        """Level Stormchaser's Talent to 2 then 3 if mana allows. L2 = {3U} (4 mana),
        L3 = {5U} (6 mana). Don't level into open opp counter mana.
        Per primer: L3 is the closer in Crab Control vs Spellementals/UW HN.
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

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Match-aware main phase:
          - Aggro mode: deploy Tiger-Seal/Duelist/FOMO on curve, warp Riddler
            for tempo, Frostcliff Siege Temur for closing speed
          - Crab-Control mode: lead cantrips/removal, hardcast Riddler late,
            Frostcliff Siege Jeskai for grind, Stormchaser L3 for closer
        """
        # Try Riddler warp first if applicable (early tempo move)
        if opponent is not None and gs.turn <= 4:
            self._try_riddler_warp(gs, opponent)

        # Inherited deploy/cantrip plan from AggroAPL.main_phase
        IzzetLootingAPL.main_phase(self, gs)

        # Stormchaser leveling in Crab Control mode (T4+ with 6 mana)
        if self._in_crab_control_mode() and gs.turn >= 4 and gs.mana_pool.total() >= 4:
            self._try_stormchaser_levelup(gs)

    def end_step_actions(self, gs: GameState, opponent: GameState):
        """End-of-opp-turn flash: Tishana's Tidebinder if in hand and there's a
        triggered/activated ability worth countering on opp's board.
        """
        tide = next((c for c in gs.zones.hand if c.name == "Tishana's Tidebinder"), None)
        if not tide:
            return
        if not gs.mana_pool.can_cast("2U", 3):
            return
        # Heuristic: cast if opp has high-value permanent (Riddler, Bringer, Spider-Man,
        # Overlord, Sapling Nursery, planeswalker)
        from data.card import Tag
        opp_perms = [c for c in opponent.zones.battlefield if not c.is_land()]
        valuable = [c for c in opp_perms
                    if c.name in ("Quantum Riddler", "Bringer of the Last Gift",
                                  "Superior Spider-Man", "Overlord of the Balemurk",
                                  "Sapling Nursery", "Earthbender Ascension",
                                  "Stormchaser's Talent", "Artist's Talent",
                                  "Monument to Endurance", "Frostcliff Siege")
                    or "Planeswalker" in (c.type_line or "")]
        if not valuable:
            return
        gs.mana_pool.pay("2U", 3)
        gs.zones.hand.remove(tide)
        gs.zones.battlefield.append(tide)
        gs._log(f"  [Tidebinder flash] strip abilities of {valuable[0].name}")
        # Approximate: strip abilities of biggest valuable target (per engine_pitfalls memory)
        target = valuable[0]
        if hasattr(target, 'tags'):
            target.tags = set()   # strip
