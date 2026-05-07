"""
apl/dimir_midrange_jermey_match.py -- Jermey's Dimir Midrange match APL

Strategy split:

  vs GREEN (Simic/Bant/Selesnya Rhythm, Selesnya Landfall, Ouroboroid, Gruul Aggro):
    - Removal FIRST. Kill mana producers before they snowball.
    - Floodpits Drowner ETB stuns their mana dork (Llanowar Elves, Gene Poll, Badgermole).
    - Tishana's Tidebinder strips the mana dork's abilities / counters landfall triggers.
    - Kaito is the last priority -- a 3/4 on an empty board beats them; into a pumped
      Badgermole board it dies immediately. Stabilize first, then planeswalker.

  vs IZZET LESSONS:
    - Ninjutsu Kaito on T3 via Spyglass Siren or Azure Beastbinder.
    - Kaito as a creature has hexproof -- Lessons can't Tragic Trajectory or burn it.
    - Once Kaito sticks, you draw cards and they can't interact at sorcery speed.
    - Skip kill spells T3 if you have the ninjutsu line; take the card advantage instead.

  vs EVERYTHING ELSE (Izzet Prowess, Spellementals, control, midrange):
    - Standard curve: Siren -> Tidebinder/Floodpits -> Kaito.
    - Removal on threats, counter on key spells, Kaito on 4.
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

SIREN        = "Spyglass Siren"
TISHANA      = "Tishana's Tidebinder"
FLOODPITS    = "Floodpits Drowner"
KAITO        = "Kaito, Bane of Nightmares"
AZURE        = "Azure Beastbinder"          # legacy: not in current build, kept for code paths
ENDURING     = "Enduring Curiosity"
LOCH_MARE    = "Loch Mare"                  # legacy
MULTIVERSAL  = "Multiversal Passage"
INTO_FLOOD   = "Into the Flood Maw"         # legacy
PHANTOM      = "Phantom Interference"
REQUITING    = "Requiting Hex"
SHOOT        = "Shoot the Sheriff"
BITTER       = "Bitter Triumph"
LONG_GOODBYE = "Long Goodbye"
QARSI        = "Qarsi Revenant"             # legacy
CECIL        = "Cecil, Dark Knight"
SPELL_SNARE  = "Spell Snare"                # legacy

# v2 build additions (RC DC prep)
DEEP_BAT     = "Deep-Cavern Bat"            # 1B 1/1 flash flying lifelink, ETB: exile from opp hand
FAEBLOOM     = "Faebloom Trick"             # 2U instant, 2x 1/1 flying tokens + tap target
MALCOLM      = "Malcolm, Alluring Scoundrel"  # 1U flash flying 2/1, draws on hit
SUNSET_SAB   = "Sunset Saboteur"            # 1B 4/1 menace ward-discard
FOUNTAINPORT = "Fountainport"               # utility land, value engine

# v3 build additions (Rat-flavor variant)
HEARTLESS    = "Heartless Act"              # 1B instant, destroy creature with no counters
STAB         = "Stab"                       # B instant, -2/-2 (kills T<=2)
SPIDER_SENSE = "Spider-Sense"               # 1U or U via web-slinging, counters instant/sorcery/trigger
LORD_SKITTER = "Lord Skitter, Sewer King"   # 2B 3/3 legendary, GY exile + rat tokens at combat
RAVEN_EAGLE  = "Raven Eagle"                # 2B 2/3 flying, GY exile + clue + drain on 2nd draw
MOCKINGBIRD  = "Mockingbird"                # XU flash flying, copies a creature with cmc<=X

# Linden UB Bounce hybrid (2026-05-07): bounce-engine extension
STORMCHASER   = "Stormchaser's Talent"        # U Class, ETB Otter; lvl 2 {3U} GY return; lvl 3 {5U} Otter per I/S
BOOMERANG     = "Boomerang Basics"            # U sorcery, bounce nonland; draw if you owned it (cantrip on self-bounce)
QUANTUM_RIDDLER = "Quantum Riddler"           # 3UU 4/6 flying flash; Warp {1U}; empty-hand draw bonus (Warp not sim-modeled)
FLITTERWING   = "Flitterwing Nuisance"        # U flying 2/2 with -1/-1 counter; {2U} pay-to-draw on combat
DECEIT        = "Deceit"                      # 4U/B U/B 5/5; Evoke U/B U/B for bounce or hand strip
GET_OUT       = "Get Out"                     # UU instant, counter creature/enchantment OR self-bounce 1-2

# Bounce targets you WANT to re-trigger when bouncing your own permanent
# (each cast triggers another ETB or value moment)
BOUNCE_RECAST_TARGETS = {STORMCHASER, "Tinybones Joins Up", "Momentum Breaker",
                          "Nowhere to Run", DEEP_BAT, FLOODPITS, FAEBLOOM}

# Mana producers — stun/strip these first vs green
MANA_DORK_NAMES = {
    "Llanowar Elves", "Gene Pollinator", "Badgermole Cub",
    "Leyline Weaver", "Spider Manifestation", "Elvish Mystic",
    "Birds of Paradise",
}

# Ninjutsu enablers — small evasive/unblockable attackers
NINJUTSU_ENABLERS = {SIREN, AZURE}

GREEN_ARCHETYPES = {
    "aggro", "ramp",  # AwareMatchAPL archetype strings
}
# Detected by opponent's deck composition in _vs_green()

# Kaito ninjutsu cost: {1}{U}{B} = 3 mana (vs full cost 4)
KAITO_NINJUTSU_CMC = 3


class JermeyDimirMatchAPL(AwareMatchAPL):
    name = "Jermey Dimir Midrange"
    ARCHETYPE = "tempo"

    COUNTER_COST  = 1
    COUNTER_CARDS = {PHANTOM, INTO_FLOOD, SPELL_SNARE, SPIDER_SENSE}

    MATCH_REMOVAL = {
        REQUITING:    ("UB",  None),
        SHOOT:        ("1B",  None),
        BITTER:       ("1B",  None),
        LONG_GOODBYE: ("B",   2),
        HEARTLESS:    ("1B",  None),  # destroy creature with no counters
        STAB:         ("B",   2),     # -2/-2; kills T<=2 baseline
    }
    MATCH_BOUNCE = {INTO_FLOOD}
    MATCH_EXILE  = set()

    # Actual sideboard: Annul, Bitter Triumph, Day of Black Sun, Disdainful Stroke,
    # Duress, Essence Scatter, Kaito Cunning Infiltrator, Requiting Hex,
    # Soul-Guide Lantern x2, Spell Pierce, Spider-Sense, Strategic Betrayal,
    # The Unagi of Kyoshi Island, Wan Shi Tong Librarian
    SB_PLANS = {
        "aggro": (
            # vs Green aggro/ramp: board wipe, exile, steal
            ["Day of Black Sun", "Strategic Betrayal", "Duress",
             "Disdainful Stroke", "The Unagi of Kyoshi Island"],
            [ENDURING, MULTIVERSAL, PHANTOM, LOCH_MARE, QARSI],
        ),
        "ramp": (
            # vs Green ramp: Disdainful Stroke counters their finishers,
            # Day of Black Sun cleans up their wide boards
            ["Day of Black Sun", "Disdainful Stroke", "Strategic Betrayal",
             "Duress", "The Unagi of Kyoshi Island"],
            [ENDURING, MULTIVERSAL, PHANTOM, LOCH_MARE, INTO_FLOOD],
        ),
        "combo": (
            # vs Izzet Lessons: GY hate, counters, Duress their Monument
            ["Soul-Guide Lantern", "Soul-Guide Lantern", "Annul",
             "Duress", "Spider-Sense"],
            [LOCH_MARE, MULTIVERSAL, LONG_GOODBYE, BITTER, SHOOT],
        ),
        "control": (
            # vs Control: hand disruption, Wan Shi Tong for card advantage
            ["Duress", "Disdainful Stroke", "Essence Scatter",
             "Kaito, Cunning Infiltrator", "Wan Shi Tong, Librarian"],
            [LONG_GOODBYE, LOCH_MARE, QARSI, INTO_FLOOD, PHANTOM],
        ),
        "tempo": (
            # vs Izzet Prowess/Spellementals: counters, Disdainful Stroke
            ["Annul", "Spell Pierce", "Disdainful Stroke",
             "Spider-Sense", "Essence Scatter"],
            [ENDURING, MULTIVERSAL, LOCH_MARE, LONG_GOODBYE, BITTER],
        ),
    }

    # ── Opponent meta-read ──────────────────────────────────────────────────
    _GREEN_CARDS = {
        "Llanowar Elves", "Gene Pollinator", "Badgermole Cub", "Leyline Weaver",
        "Nature's Rhythm", "Ouroboroid", "Craterhoof Behemoth", "Brightglass Gearhulk",
        "Spider Manifestation",
    }
    _LESSONS_CARDS = {
        "Monument to Endurance", "Gran-Gran, Scourge of Spirits", "Artist's Talent",
        "Show and Tell",
    }
    _AIRBENDING_CARDS = {
        "Bant Airbending", "Sage of the Skies", "Conduit of Worlds",
        "Abandoned Air Temple",
    }
    # Azorius High Noon (Zevin Faust UW Prison-Tempo) detection
    # Distinct enough that ANY one of these in opp's deck = vs HN
    _HIGH_NOON_CARDS = {
        "High Noon", "Voice of Victory", "Aven Interrupter",
        "Aang, Swift Savior", "Skycoach Conductor", "Avatar's Wrath",
    }
    _HN_LOCK_PIECES = {"High Noon", "Voice of Victory"}        # priority counter targets
    _HN_THREATS     = {"Aven Interrupter", "Aang, Swift Savior"}  # priority kill targets
    # Izzet Prowess detection — Slickshot is uniquely Prowess (Spellementals
    # shares Eddymurk but doesn't run Slickshot)
    _PROWESS_CARDS = {
        "Slickshot Show-Off", "Stormchaser's Talent", "Colorstorm Stallion",
        "Burst Lightning", "Boomerang Basics", "Flow State",
    }
    _PROWESS_THREATS = {"Slickshot Show-Off", "Colorstorm Stallion"}  # Tishana strips these

    def _vs_green(self, opponent: GameState) -> bool:
        if opponent is None:
            return False
        all_cards = (list(opponent.zones.battlefield)
                     + list(getattr(opponent.zones, 'hand', []))
                     + list(getattr(opponent.zones, 'library', []))[:10])
        return sum(1 for c in all_cards if c.name in self._GREEN_CARDS) >= 3

    def _vs_lessons(self, opponent: GameState) -> bool:
        if opponent is None:
            return False
        all_cards = (list(opponent.zones.battlefield)
                     + list(getattr(opponent.zones, 'hand', []))
                     + list(getattr(opponent.zones, 'library', []))[:10])
        return sum(1 for c in all_cards if c.name in self._LESSONS_CARDS) >= 2

    def _vs_high_noon(self, opponent: GameState) -> bool:
        """True if opponent is Azorius High Noon (Zevin Faust prison-tempo).
        High Noon and Voice of Victory are both nearly unique to this archetype."""
        if opponent is None:
            return False
        all_cards = (list(opponent.zones.battlefield)
                     + list(getattr(opponent.zones, 'hand', []))
                     + list(getattr(opponent.zones, 'library', []))[:15])
        return sum(1 for c in all_cards if c.name in self._HIGH_NOON_CARDS) >= 2

    def _vs_prowess(self, opponent: GameState) -> bool:
        """True if opponent is Izzet Prowess (Slickshot Show-Off shell).
        Distinguishes from Spellementals: Prowess runs Slickshot + Burst Lightning;
        Spellementals runs Sunderflock + Hearth Elemental and no Slickshot."""
        if opponent is None:
            return False
        all_cards = (list(opponent.zones.battlefield)
                     + list(getattr(opponent.zones, 'hand', []))
                     + list(getattr(opponent.zones, 'library', []))[:15])
        # Slickshot is the strongest signal — exclusive to Prowess
        has_slickshot = any(c.name == "Slickshot Show-Off" for c in all_cards)
        prowess_count = sum(1 for c in all_cards if c.name in self._PROWESS_CARDS)
        return has_slickshot or prowess_count >= 3

    def _vs_airbending(self, opponent: GameState) -> bool:
        """True if opponent is a flying-heavy deck (Bant Airbending, etc.)."""
        if opponent is None:
            return False
        from engine.keywords import KWTag
        all_cards = (list(opponent.zones.battlefield)
                     + list(getattr(opponent.zones, 'hand', []))
                     + list(getattr(opponent.zones, 'library', []))[:10])
        # Named airbending cards OR many fliers on board
        named = sum(1 for c in all_cards if c.name in self._AIRBENDING_CARDS)
        fliers_on_board = sum(1 for c in opponent.zones.battlefield
                              if KWTag.FLYING in getattr(c, 'tags', set())
                              and not c.is_land())
        return named >= 1 or fliers_on_board >= 2

    # ── Mulligan ───────────────────────────────────────────────────────────
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        has_threat = any(c.name in {SIREN, FLOODPITS, KAITO, AZURE} for c in hand)
        has_removal = any(c.name in {REQUITING, SHOOT, BITTER, TISHANA} for c in hand)
        return (has_threat or has_removal) or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    # ── Mana holdback ──────────────────────────────────────────────────────
    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_floodpits = any(c.name == FLOODPITS for c in gs.zones.hand)
        opp_has_dorks = (opponent is not None and any(
            c.name in MANA_DORK_NAMES and not getattr(c, 'tapped', False)
            for c in opponent.zones.battlefield
        ))
        if has_floodpits and opp_has_dorks and self._vs_green(opponent):
            # Hold {1}{U} = 2 mana to flash Floodpits during their upkeep
            gs.mana_reserve = 2
        elif opponent and self._vs_lessons(opponent):
            gs.mana_reserve = 1   # hold 1 for counter / Into the Flood Maw
        else:
            gs.mana_reserve = 0

    # ── End-step flash: Deep-Cavern Bat (hand exile), Floodpits, Malcolm ─────
    def end_step_actions(self, gs: GameState, opponent: GameState):
        """
        End-of-opp-turn flashes:
          1. Deep-Cavern Bat: hand-exile their key card (Monument/HN/big threat)
             before they can play it next turn. Fires whenever opp has 2+ cards.
          2. Floodpits: stun a mana dork pre-upkeep (vs green only).
          3. Malcolm Alluring Scoundrel: flash deploy as a 2/1 flying threat.
        """
        if opponent is None:
            return

        # 1. Deep-Cavern Bat — fire if opp has nonland cards in hand
        opp_hand_nonlands = [c for c in opponent.zones.hand if not c.is_land()]
        if len(opp_hand_nonlands) >= 1:
            for card in list(gs.zones.hand):
                if card.name == DEEP_BAT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs._match_opp = opponent
                    gs.cast_spell(card)
                    gs._log(f"  [end-step] Deep-Cavern Bat -> exile from opp hand "
                            f"({len(opp_hand_nonlands)} nonlands)")
                    return

        # 2. Floodpits to stun mana dork (vs green)
        if self._vs_green(opponent):
            opp_dorks = [c for c in opponent.zones.battlefield
                         if c.name in MANA_DORK_NAMES
                         and not getattr(c, 'tapped', False)]
            if opp_dorks:
                for card in list(gs.zones.hand):
                    if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs._target_mana_dork = True
                        gs.cast_spell(card)
                        gs._target_mana_dork = False
                        gs._log("  [end-step flash] Floodpits -> stun mana dork")
                        return

        # 3. Malcolm: flash 2/1 flying threat with card-advantage trigger
        for card in list(gs.zones.hand):
            if card.name == MALCOLM and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs._log("  [end-step] Malcolm Alluring Scoundrel deployed")
                return

    # ── Kaito -2: double-stun their biggest threat ─────────────────────────
    def _kaito_minus2(self, gs: GameState, opponent: GameState):
        """
        Kaito, Bane of Nightmares -2: tap target creature, put 2 stun counters.
        2 stun counters = misses 2 untap steps. vs green this is 2 turns of silence
        on their biggest threat. Fire once when Kaito enters or early in main phase.
        """
        if opponent is None:
            return
        kaito_on_bf = next((c for c in gs.zones.battlefield if c.name == KAITO), None)
        if kaito_on_bf is None:
            return
        if getattr(kaito_on_bf, '_minus2_used', False):
            return  # already used this turn

        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()
                         and not getattr(c, 'tapped', False)]
        if not opp_creatures:
            return

        # Target biggest threat (vs green: biggest creature, vs others: same)
        target = max(opp_creatures, key=lambda c: safe_power(c))
        target.tapped = True
        target._stun_counter = True
        # Two stun counters = 2 missed untap steps (proxy via attribute count)
        target._stun_count = getattr(target, '_stun_count', 0) + 2
        kaito_on_bf._minus2_used = True
        gs._log(f"  [Kaito -2] double-stun {target.name} (2 untap steps missed)")

    # ── Loch Mare tap ability: {2}{U}, remove 2 counters, tap creature ─────
    def _loch_mare_tap(self, gs: GameState, opponent: GameState):
        """
        Loch Mare {2}{U}: remove 2 -1/-1 counters, tap target creature.
        Each activation costs 3 mana and removes 2 counters (1.5 activations total).
        High value vs green: tap their biggest threat before it attacks.
        """
        if opponent is None:
            return
        loch = next((c for c in gs.zones.battlefield if c.name == LOCH_MARE), None)
        if loch is None:
            return
        counters = getattr(loch, 'counters', 0) or 0
        if counters >= -1:   # needs at least 2 negative counters to remove
            return
        if gs.mana_pool.total() < 3:
            return

        opp_threats = [c for c in opponent.zones.battlefield
                       if c.has(Tag.CREATURE) and not c.is_land()
                       and not getattr(c, 'tapped', False)]
        if not opp_threats:
            return

        target = max(opp_threats, key=lambda c: safe_power(c))
        target.tapped = True
        loch.counters = counters + 2   # remove 2 counters
        gs.mana_pool.pay("2U", 3)
        gs._log(f"  [Loch Mare] tap {target.name} ({loch.counters} counters remain)")

    # ── Kill a specific target ─────────────────────────────────────────────
    def _kill_target(self, gs: GameState, target) -> bool:
        """Try to kill target creature with removal spells. Returns True if killed."""
        toughness = safe_toughness(target)
        for card in list(gs.zones.hand):
            if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                continue
            if card.name == LONG_GOODBYE and toughness <= 2:
                gs.cast_spell(card)
                return True
            if card.name in {REQUITING, SHOOT, BITTER}:
                gs.cast_spell(card)
                return True
        return False

    # ── Pre-combat: remove mana producers before they attack/trigger ───────
    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        if opponent is None:
            return
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        # Always kill mana dorks before combat if possible
        for c in opp_creatures:
            if c.name in MANA_DORK_NAMES:
                if self._kill_target(gs, c):
                    gs._log(f"  [pre-combat] killed mana dork {c.name}")
                    return

    # ── Ninjutsu Kaito ─────────────────────────────────────────────────────
    def _try_ninjutsu_kaito(self, gs: GameState, opponent: GameState) -> bool:
        """
        Ninjutsu Kaito via an unblocked attacker for {1}{U}{B} = 3 mana.
        Returns True if executed.
        """
        kaito_in_hand = next((c for c in gs.zones.hand if c.name == KAITO), None)
        if kaito_in_hand is None:
            return False
        if gs.mana_pool.total() < KAITO_NINJUTSU_CMC:
            return False

        # Need an enabling creature on battlefield, not summoning sick, not tapped
        enabler = next(
            (c for c in gs.zones.battlefield
             if c.name in NINJUTSU_ENABLERS
             and not getattr(c, 'summoning_sickness', False)
             and not getattr(c, 'tapped', False)),
            None,
        )
        if enabler is None:
            return False

        # Execute ninjutsu: return enabler to hand, put Kaito onto battlefield
        gs.zones.battlefield.remove(enabler)
        gs.zones.hand.append(enabler)
        gs.zones.hand.remove(kaito_in_hand)
        gs.zones.battlefield.append(kaito_in_hand)
        kaito_in_hand.summoning_sickness = False   # ninjutsu grants no summoning sickness
        gs.mana_pool.pay("1UB", KAITO_NINJUTSU_CMC)

        # Fire ETB handler
        from engine.card_handlers_verified import ETB_EFFECTS
        handler = ETB_EFFECTS.get(KAITO)
        if handler:
            handler(gs, kaito_in_hand)

        gs._log(f"  [ninjutsu] {enabler.name} -> Kaito, Bane of Nightmares (cost {KAITO_NINJUTSU_CMC})")
        return True

    # ── Main phase ─────────────────────────────────────────────────────────
    def main_phase_match(self, gs: GameState, opponent: GameState):
        if opponent is not None:
            gs._match_opp = opponent
        self._opp_gs = opponent

        self._play_land_if_able(gs)
        gs.tap_lands()

        vs_high_noon  = self._vs_high_noon(opponent)
        vs_prowess    = self._vs_prowess(opponent)
        vs_green      = self._vs_green(opponent)
        vs_lessons    = self._vs_lessons(opponent)
        vs_airbending = self._vs_airbending(opponent)

        # ── Always: Kaito -2 and Loch Mare tap fire every main phase ──────
        self._kaito_minus2(gs, opponent)
        self._loch_mare_tap(gs, opponent)

        # ── AZORIUS HIGH NOON: priority kill on lock pieces & Aven/Aang ───
        # Zevin's deck wins by chaining High Noon + Voice + Aven exiles.
        # Counter HN/Voice with Spell Snare; kill Aven/Aang with Bitter
        # Triumph or Requiting Hex; race with Kaito (hexproof body that
        # ignores their flash interaction).
        if vs_high_noon and opponent is not None:
            # 1. Priority kill: Aven Interrupter / Aang on board (they exile
            #    our cards). Aven is 3/3 (Outlaw, immune to Shoot the Sheriff)
            #    so use Bitter Triumph or Requiting Hex.
            opp_threats_on_bf = [c for c in opponent.zones.battlefield
                                 if not c.is_land() and c.name in self._HN_THREATS]
            for target in opp_threats_on_bf:
                if self._kill_target(gs, target):
                    gs._log(f"  [vs HN] killed lock-threat {target.name}")
                    break
            # 2. Bounce High Noon / Voice with Into the Flood Maw if visible
            opp_lock_on_bf = [c for c in opponent.zones.battlefield
                              if c.name in self._HN_LOCK_PIECES]
            if opp_lock_on_bf:
                lock = opp_lock_on_bf[0]
                for card in list(gs.zones.hand):
                    if card.name == INTO_FLOOD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs._bounce_target_name = lock.name
                        gs.cast_spell(card)
                        gs._bounce_target_name = None
                        gs._log(f"  [vs HN] bounce {lock.name} via Into the Flood Maw")
                        break
            # 3. Ninjutsu Kaito ASAP — hexproof body that ignores Aang/Aven exile
            if gs.turn >= 3:
                if self._try_ninjutsu_kaito(gs, opponent):
                    self._cast_all_castable(gs)
                    return
            # 4. Floodpits Drowner: stun their flash threats (Aang/Aven/Floodpits)
            opp_flash_threats = [c for c in opponent.zones.battlefield
                                 if not c.is_land()
                                 and c.has(Tag.CREATURE)
                                 and not getattr(c, 'tapped', False)
                                 and c.name in (self._HN_THREATS | {"Floodpits Drowner",
                                                                     "Skycoach Conductor"})]
            if opp_flash_threats:
                for card in list(gs.zones.hand):
                    if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break
            # 5. Deploy threats: Spyglass Siren (flash, ninjutsu enabler),
            #    Deep-Cavern Bat (hand exile), Tishana, Cecil, Sunset Saboteur,
            #    Enduring Curiosity, then hardcast Kaito if affordable
            for name in (SIREN, DEEP_BAT, TISHANA, CECIL, SUNSET_SAB, ENDURING):
                for card in list(gs.zones.hand):
                    if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break
            # 6. Hardcast Kaito if no ninjutsu enabler but mana available
            for card in list(gs.zones.hand):
                if card.name == KAITO and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # ── IZZET PROWESS: kill on sight, Slickshot is 1/2 baseline ──────
        # Largest field share at PT SOS (24.5%). Their plan: T2 Slickshot
        # ({1}{R} 1/2 flying haste, +2/+0 per noncreature spell) or
        # Stormchaser's Talent, T3 Colorstorm + cantrip stack, T4-5 lethal
        # via pumped fliers + burn. KEY: Slickshot is 1/2 base, so Long
        # Goodbye ({1}{B} -- can't be countered, kills <=3 CMC) takes it
        # out pre-pump. Tishana strips ABILITIES (counter the prowess
        # trigger or the levelup trigger -- can't counter the spell itself).
        elif vs_prowess and opponent is not None:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]

            # 1. PRIORITY: Long Goodbye ({1}{B} = 2 mana, can't be countered)
            #    on Slickshot. Kills 1/2 base or up to 3-mana threats. NOT
            #    {B} as I once mis-noted -- it's a 2-mana instant.
            slickshots = [c for c in opp_creatures if c.name == "Slickshot Show-Off"
                          and safe_toughness(c) <= 2]
            if slickshots:
                target = slickshots[0]
                long_goodbye = next((c for c in gs.zones.hand
                                      if c.name == LONG_GOODBYE
                                      and gs.mana_pool.can_cast(c.mana_cost, c.cmc)), None)
                if long_goodbye:
                    gs.cast_spell(long_goodbye)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  [vs Prowess] Long Goodbye on Slickshot Show-Off (T{safe_toughness(target)})")

            # 2. Tishana strips abilities of any remaining Slickshot/Stallion
            #    (now-1/2 vanilla blocker, no flying)
            opp_threats_on_bf = [c for c in opponent.zones.battlefield
                                 if not c.is_land() and c.has(Tag.CREATURE)
                                 and c.name in self._PROWESS_THREATS]
            if opp_threats_on_bf:
                tishana_in_hand = any(c.name == TISHANA for c in gs.zones.hand)
                if tishana_in_hand:
                    for card in list(gs.zones.hand):
                        if card.name == TISHANA and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                            gs.cast_spell(card)
                            gs._log(f"  [vs Prowess] Tishana strips {opp_threats_on_bf[0].name}")
                            break

            # 3. Bitter Triumph / Shoot the Sheriff / Requiting Hex on whatever
            #    remains (Colorstorm Stallion is 3/3 base, harder to kill cheap)
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            if opp_creatures:
                target = max(opp_creatures, key=lambda c: safe_power(c))
                if self._kill_target(gs, target):
                    gs._log(f"  [vs Prowess] killed {target.name} (P{safe_power(target)})")

            # 3. Floodpits Drowner: tap + stun on remaining threat
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)
                             and not getattr(c, 'tapped', False)]
            if opp_creatures:
                for card in list(gs.zones.hand):
                    if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

            # 4. Bounce Stormchaser's Talent if visible (they grow as enchantment)
            stormchaser_on_bf = [c for c in opponent.zones.battlefield
                                 if c.name == "Stormchaser's Talent"]
            if stormchaser_on_bf:
                for card in list(gs.zones.hand):
                    if card.name == INTO_FLOOD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs._bounce_target_name = "Stormchaser's Talent"
                        gs.cast_spell(card)
                        gs._bounce_target_name = None
                        break

            # 5. Deploy threats — Spyglass Siren (flash, ninjutsu enabler),
            #    Deep-Cavern Bat (hand exile a Stock Up etc), Cecil, Sunset
            #    Saboteur (4-power menace race), Enduring (CA), Kaito hardcast
            for name in (SIREN, DEEP_BAT, CECIL, SUNSET_SAB, ENDURING, KAITO):
                for card in list(gs.zones.hand):
                    if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # ── IZZET LESSONS: ninjutsu Kaito T3, hold Tishana for Monument ───
        elif vs_lessons and opponent is not None:
            monument_on_board = any(c.name == "Monument to Endurance"
                                    for c in opponent.zones.battlefield)
            # Tishana strips Monument of all abilities — fire immediately when it's on board
            if monument_on_board:
                for card in list(gs.zones.hand):
                    if card.name == TISHANA and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        gs._log("  [vs Lessons] Tishana strips Monument to Endurance")
                        break
            # Ninjutsu Kaito on T3+ — hexproof body dodges their interaction
            if gs.turn >= 3:
                if self._try_ninjutsu_kaito(gs, opponent):
                    self._cast_all_castable(gs)
                    return
            # Into the Flood Maw bounces Monument if Tishana unavailable
            if monument_on_board:
                for card in list(gs.zones.hand):
                    if card.name == INTO_FLOOD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        # Override bounce target to Monument
                        gs._bounce_target_name = "Monument to Endurance"
                        gs.cast_spell(card)
                        gs._bounce_target_name = None
                        break

        # ── BANT AIRBENDING: kill fliers, contest with Faebloom + Malcolm ───
        elif vs_airbending and opponent is not None:
            from engine.keywords import KWTag
            opp_fliers = [c for c in opponent.zones.battlefield
                          if KWTag.FLYING in getattr(c, 'tags', set()) and not c.is_land()]
            # Faebloom Trick: 2x 1/1 flyer tokens + tap their best flier (great here)
            if opp_fliers:
                for card in list(gs.zones.hand):
                    if card.name == FAEBLOOM and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        gs._log("  [vs Airbending] Faebloom Trick: 2 fliers + tap")
                        break
            # Kill biggest flier with removal (Bitter Triumph / Shoot the Sheriff
            # / Requiting Hex). Long Goodbye covers small fliers cheaply.
            if opp_fliers:
                biggest_flier = max(opp_fliers, key=lambda c: safe_power(c))
                if self._kill_target(gs, biggest_flier):
                    gs._log(f"  [vs Airbending] killed flier {biggest_flier.name}")
            # Deploy threats — flying-relevant first (Malcolm 2/1 flying flash,
            # Deep-Cavern Bat 1/1 flying lifelink, Tishana strip)
            for name in (SIREN, DEEP_BAT, TISHANA, FLOODPITS, CECIL,
                         MALCOLM, RAVEN_EAGLE, ENDURING, KAITO):
                for card in list(gs.zones.hand):
                    if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # ── GREEN: removal first, stun their mana production ──────────────
        elif vs_green and opponent is not None:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if c.has(Tag.CREATURE) and not c.is_land()]

            # 1. Kill mana producers first
            gs._target_mana_dork = True
            for c in sorted(opp_creatures,
                            key=lambda c: (0 if c.name in MANA_DORK_NAMES else 1,
                                           -safe_power(c))):
                if self._kill_target(gs, c):
                    break

            # 2. Tishana strips mana dork abilities
            for card in list(gs.zones.hand):
                if card.name == TISHANA and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

            # 3. Into the Flood Maw: bounce counter-laden creatures (resets all counters)
            for card in list(gs.zones.hand):
                if card.name == INTO_FLOOD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

            gs._target_mana_dork = False

            # 4. Floodpits held for end-step unless no dorks alive
            opp_dorks_alive = any(c.name in MANA_DORK_NAMES and not getattr(c, 'tapped', False)
                                  for c in opponent.zones.battlefield)
            if not opp_dorks_alive:
                for card in list(gs.zones.hand):
                    if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

            # 5. Deploy threats. Kaito last — only when we can survive
            opp_power = sum(safe_power(c) for c in opponent.zones.battlefield
                            if c.has(Tag.CREATURE) and not c.is_land())
            my_toughness = sum(safe_toughness(c) for c in gs.zones.battlefield
                               if c.has(Tag.CREATURE) and not c.is_land())
            # After Kaito -2, biggest threat is stunned — safer to deploy
            kaito_minus2_fired = any(getattr(c, '_minus2_used', False)
                                     for c in gs.zones.battlefield if c.name == KAITO)
            deploy_kaito = opp_power <= my_toughness or kaito_minus2_fired
            for name in (SIREN, DEEP_BAT, CECIL, SUNSET_SAB, RAVEN_EAGLE,
                         LORD_SKITTER, ENDURING):
                for card in list(gs.zones.hand):
                    if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break
            if deploy_kaito:
                for card in list(gs.zones.hand):
                    if card.name == KAITO and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        else:
            # ── STANDARD: curve normally ───────────────────────────────────
            # T1 enchantments first (Stormchaser's Talent for Otter engine,
            # Tinybones Joins Up for discard + legendary mill trigger).
            # Then 1-mana creatures, then 2-mana flash, then up the curve.
            for name in (STORMCHASER, "Tinybones Joins Up", SIREN, CECIL,
                         FLITTERWING, DEEP_BAT, FLOODPITS, TISHANA,
                         "Momentum Breaker", "Nowhere to Run",
                         SUNSET_SAB, RAVEN_EAGLE, LORD_SKITTER,
                         MOCKINGBIRD, ENDURING, KAITO, QUANTUM_RIDDLER):
                for card in list(gs.zones.hand):
                    if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # ── Bounce-engine fallback (runs after every branch) ─────────────────
        # These cards aren't in the per-matchup deploy lists. Try them
        # opportunistically once the matchup-specific deploys finish.

        # 1. Stormchaser's Talent / Tinybones / Boomerang / Quantum Riddler
        #    pickup (in case the matchup-branch didn't deploy them).
        for name in (STORMCHASER, "Tinybones Joins Up", FLITTERWING):
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # 2. Quantum Riddler Warp: if hardcast not possible but Warp
        #    cost ({1}{U}) is, cast as 2-mana 4/6 flier (exiles next EOT).
        for card in list(gs.zones.hand):
            if card.name == QUANTUM_RIDDLER and gs.mana_pool.can_cast("1U", 2):
                if gs.cast_spell_warp(card):
                    break

        # 3. Boomerang Basics: opportunistic bounce (target opp threat or
        #    self-bounce a re-triggerable enchantment for cantrip).
        self._try_boomerang_basics(gs, opponent)

        # 4. Stormchaser's Talent level activation (sorcery speed).
        self._try_stormchaser_levelup(gs)

        self._cast_all_castable(gs)

    # ── Boomerang Basics targeting ───────────────────────────────────────────
    def _try_boomerang_basics(self, gs: GameState, opponent):
        """Cast Boomerang Basics if we have one and a good target.
        Priority:
          1. Bounce an opp creature that's threatening us (highest power)
          2. Bounce one of our own enchantment/creature ETBs for re-trigger
             (must own it -- draws a card via Boomerang's own text)
        """
        boomerang = next((c for c in gs.zones.hand
                         if c.name == BOOMERANG and gs.mana_pool.can_cast(c.mana_cost, c.cmc)),
                        None)
        if boomerang is None or opponent is None:
            return

        # Priority 1: bounce opp's biggest creature if we have one threatening
        opp_threats = [c for c in opponent.zones.battlefield
                       if c.has(Tag.CREATURE) and not c.is_land()
                       and safe_power(c) >= 3]
        if opp_threats:
            # Letting engine pick target is fine; just cast it
            try:
                gs.cast_spell(boomerang)
                gs._log(f"  [Boomerang] bounce opp threat (biggest P{max(safe_power(c) for c in opp_threats)})")
                return
            except Exception:
                pass

        # Priority 2: self-bounce a re-triggerable enchantment for cantrip + re-ETB
        my_recast_targets = [c for c in gs.zones.battlefield
                             if c.name in BOUNCE_RECAST_TARGETS]
        if my_recast_targets:
            try:
                gs.cast_spell(boomerang)
                gs._log(f"  [Boomerang] self-bounce {my_recast_targets[0].name} for cantrip + re-trigger")
                return
            except Exception:
                pass

    # ── Stormchaser's Talent level activation ────────────────────────────────
    def _try_stormchaser_levelup(self, gs: GameState):
        """Activate Stormchaser's Talent levels at sorcery speed:
          Level 2 ({3}{U}): return I/S from GY to hand
          Level 3 ({5}{U}): each I/S cast creates a 1/1 prowess Otter
        Level 3 is the bigger payoff -- each Boomerang Basics, Bitter Triumph,
        Faebloom Trick, etc. = another Otter.
        """
        sct = next((c for c in gs.zones.battlefield
                   if c.name == STORMCHASER), None)
        if sct is None:
            return
        level = getattr(sct, '_class_level', 1)
        # Try Level 3 first if we're at level 2 and have {5}{U}
        if level >= 2:
            if gs.mana_pool.can_cast("5U", 6):
                try:
                    gs.mana_pool.pay_cost("5U", 6)
                    sct._class_level = 3
                    gs._log("  [Stormchaser] level 3 -- each I/S now creates an Otter")
                    return
                except Exception:
                    pass
        # Otherwise try Level 2 if we have {3}{U}
        if level == 1 and gs.mana_pool.can_cast("3U", 4):
            try:
                gs.mana_pool.pay_cost("3U", 4)
                sct._class_level = 2
                gs._log("  [Stormchaser] level 2")
            except Exception:
                pass

    # ── Attackers: always include ninjutsu enablers ─────────────────────────
    def declare_attackers(self, gs: GameState, opponent: GameState):
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]

        if not my_creatures:
            return []

        opp = opponent
        vs_lessons = self._vs_lessons(opp)
        kaito_in_hand = any(c.name == KAITO for c in gs.zones.hand)

        # vs Lessons: send enabler to create ninjutsu window next turn
        if vs_lessons and kaito_in_hand:
            enablers = [c for c in my_creatures if c.name in NINJUTSU_ENABLERS]
            if enablers:
                return enablers   # attack only with the enabler to set up ninjutsu

        return super().declare_attackers(gs, opponent)

    # ── Blockers ────────────────────────────────────────────────────────────
    def declare_blockers(self, gs: GameState, opponent: GameState, attackers):
        if not attackers:
            return {}
        from engine.keywords import KWTag
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'tapped', False)
                        and not getattr(c, 'summoning_sickness', False)]
        if not my_creatures:
            return {}

        # Deathtouch blockers (Cecil, Qarsi) kill anything they block — assign
        # them to biggest power attackers first to maximise trade-up value
        dt_blockers  = [c for c in my_creatures if KWTag.DEATHTOUCH in c.tags]
        reg_blockers = [c for c in my_creatures if KWTag.DEATHTOUCH not in c.tags]

        sorted_atk = sorted(attackers, key=lambda c: -safe_power(c))
        avail_dt   = list(dt_blockers)
        avail_reg  = sorted(reg_blockers, key=lambda c: -safe_toughness(c))

        assignments = {}
        for atk in sorted_atk:
            if avail_dt:
                blk = avail_dt.pop(0)
            elif avail_reg:
                blk = avail_reg.pop(0)
            else:
                break
            assignments[id(atk)] = [blk]
        return assignments

    def _play_land_if_able(self, gs: GameState):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
