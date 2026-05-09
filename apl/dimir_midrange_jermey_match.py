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

    # Manlands: a 2-lander with manlands plays better than the count suggests
    _MANLANDS = {"Restless Reef", "Soulstone Sanctuary",
                 "Multiversal Passage", "Starting Town"}

    # Mulligan: pilot rules per dimir-jermey-v2-sb-guide-rc-dc.md
    #   - NO 1-landers ever (snap mull)
    #   - 2-lander with low curve (all <=2 CMC nonlands) keep all day
    #   - 7-card all-reactive (no creature) usually mull, manlands lean keep
    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        """Dimir Midrange mulligan rules (overrides AwareMatchAPL default).

        Reject:
          - 0-1 lands (snap mull, no exception)
          - 6+ lands
          - All 5+ CMC nonlands (no early plays)
          - 7-card all-reactive hand (0 creatures, 0 manlands) -- need
            pressure or a manland to threaten

        Conditional:
          - 2-lander: keep iff at least 1 nonland is <=3 CMC and at
            least 1 creature OR a manland on board path
          - 3-4 lander: keep iff at least 1 creature OR Kaito with a
            2-drop OR has a manland
        """
        if len(hand) <= 4:
            return True   # London mull floor

        lands = [c for c in hand if c.is_land()]
        nonlands = [c for c in hand if not c.is_land()]
        n_lands = len(lands)

        # Hard rejects
        if n_lands <= 1 or n_lands >= 6:
            return False
        if not nonlands:
            return False

        # All 5+ CMC reject
        cheap_nonlands = [c for c in nonlands if (getattr(c, 'cmc', 99) or 99) <= 4]
        if not cheap_nonlands:
            return False

        creatures = [c for c in nonlands if c.has(Tag.CREATURE)]
        has_manland = any(c.name in self._MANLANDS for c in lands)

        # All-reactive 7-card hand (no creature, no manland): mull
        if len(hand) == 7 and not creatures and not has_manland:
            return False

        # 2-lander: needs early-curve play AND (creature or manland)
        if n_lands == 2:
            has_early = any((getattr(c, 'cmc', 99) or 99) <= 3 for c in nonlands)
            return has_early and (bool(creatures) or has_manland)

        # 3-4 lander with stuff: keep
        # 5-lander: keep iff have a 2-drop creature
        if n_lands == 5:
            has_two_drop = any((getattr(c, 'cmc', 99) or 99) <= 2 and c.has(Tag.CREATURE)
                               for c in nonlands)
            return has_two_drop

        # 3-4 lander default: keep
        return True

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
    # Counter cards we hold up mana for (pilot rule: tempo deck wins by
    # turning 1-2 mana counters into eating opp's 3+ mana spells).
    _HOLDUP_COUNTERS = {
        SPELL_SNARE,           # {U} -- hits CMC=2 (most removal + 2-drops)
        PHANTOM,               # {U} Spree, counter mode {1}{U}
        "Negate",              # {1}{U} noncreature
        "Spell Pierce",        # {U} noncreature unless paid 2
        "Disdainful Stroke",   # {1}{U} CMC>=4
        "Essence Scatter",     # {1}{U} creature
        "Spider-Sense",        # {1}{U} insta/sorcery/triggered (Web-slinging {U})
        "Annul",               # {U} artifact/enchantment
    }

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_floodpits = any(c.name == FLOODPITS for c in gs.zones.hand)
        opp_has_dorks = (opponent is not None and any(
            c.name in MANA_DORK_NAMES and not getattr(c, 'tapped', False)
            for c in opponent.zones.battlefield
        ))

        # Count counters in hand (each one wants 1-2 mana held up)
        counters_in_hand = [c for c in gs.zones.hand
                            if c.name in self._HOLDUP_COUNTERS]
        has_counter = bool(counters_in_hand)

        # Total lands available (need to reserve only if we have spare)
        n_lands = sum(1 for c in gs.zones.battlefield if c.is_land()
                      and not getattr(c, 'tapped', False))

        if has_floodpits and opp_has_dorks and self._vs_green(opponent):
            # Hold {1}{U} = 2 mana to flash Floodpits during their upkeep
            gs.mana_reserve = 2
        elif has_counter and n_lands >= 3:
            # Hold up enough for the cheapest counter we have
            min_cmc = min(int(getattr(c, 'cmc', 1) or 1)
                          for c in counters_in_hand)
            # Cap reserve at 2 so we still develop board (don't sit on
            # 4 mana doing nothing)
            gs.mana_reserve = min(min_cmc, 2)
        elif opponent and self._vs_lessons(opponent):
            gs.mana_reserve = 1   # hold 1 for Into the Flood Maw fallback
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
    # Opp removal cards Kaito should fear (will kill the planeswalker)
    _KAITO_THREAT_REMOVAL = {
        "Bitter Triumph", "Long Goodbye", "Get Lost",
        "Sheltered by Ghosts", "Vanish into Eternity",
        "Hopeless Nightmare", "Lightning Helix",
        "Shoot the Sheriff", "Requiting Hex",
    }

    def _kaito_minus2(self, gs: GameState, opponent: GameState):
        """
        Kaito -2: tap target creature + 2 stun counters.

        Pilot rule: -2 is rarely correct. Default is to PRESERVE loyalty
        for the hexproof-on-your-turn body and the +0 surveil-draw line.
        Only fire -2 when ONE of the following holds:

        (a) Kaito is going to die on opp's turn anyway -- spend the
            loyalty before they steal it (opp board can outdamage
            current loyalty, OR opp has known PW-killing removal in hand)
        (b) We're so far ahead that loyalty is fungible (life lead 8+,
            or empty opp board with us at healthy life)
        (c) Game-ending threat must be locked: opp creature would lethal
            us next turn AND we can't otherwise remove it

        Otherwise: skip the -2 and prefer +0 (draw) or +1 (emblem) lines.
        """
        if opponent is None:
            return
        kaito_on_bf = next((c for c in gs.zones.battlefield if c.name == KAITO), None)
        if kaito_on_bf is None:
            return
        if getattr(kaito_on_bf, '_minus2_used', False):
            return  # already used this turn

        opp_creatures_all = [c for c in opponent.zones.battlefield
                             if c.has(Tag.CREATURE) and not c.is_land()]
        opp_creatures = [c for c in opp_creatures_all
                         if not getattr(c, 'tapped', False)]
        if not opp_creatures:
            return

        # ── Gate: should we even -2 this turn? ──
        loyalty = getattr(kaito_on_bf, 'loyalty', 3) or 3

        # (a) Kaito dying check: opp's untapped power vs loyalty,
        # plus removal-in-hand check (opp can target the PW directly).
        opp_attack_power = sum(safe_power(c) for c in opp_creatures)
        opp_removal_in_hand = sum(
            1 for c in opponent.zones.hand
            if c.name in self._KAITO_THREAT_REMOVAL
        )
        kaito_dying = (opp_attack_power >= loyalty) or (opp_removal_in_hand >= 1)

        # (b) Clearly-ahead check: big life lead OR clear board + healthy life
        life_lead = gs.life - opponent.life
        empty_opp_board = len(opp_creatures_all) == 0
        clearly_ahead = (life_lead >= 8) or (empty_opp_board and gs.life >= 12)

        # (c) Must-lock check: opp has a creature that can lethal us next
        # turn AND we have no removal in hand for it.
        biggest_threat_power = max((safe_power(c) for c in opp_creatures), default=0)
        my_removal_in_hand = any(
            c.name in {LONG_GOODBYE, REQUITING, SHOOT, BITTER}
            and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            for c in gs.zones.hand
        )
        must_lock = (biggest_threat_power >= gs.life) and not my_removal_in_hand

        if not (kaito_dying or clearly_ahead or must_lock):
            return  # default: preserve loyalty, don't -2

        # ── Fire -2 ──
        target = max(opp_creatures, key=lambda c: safe_power(c))
        target.tapped = True
        target._stun_counter = True
        # Two stun counters = 2 missed untap steps (proxy via attribute count)
        target._stun_count = getattr(target, '_stun_count', 0) + 2
        kaito_on_bf._minus2_used = True
        # Reduce loyalty by 2
        if hasattr(kaito_on_bf, 'loyalty') and kaito_on_bf.loyalty is not None:
            kaito_on_bf.loyalty = max(0, kaito_on_bf.loyalty - 2)
        reason = ("kaito-dying" if kaito_dying else
                  ("ahead" if clearly_ahead else "must-lock"))
        gs._log(f"  [Kaito -2] double-stun {target.name} ({reason}, loyalty->{getattr(kaito_on_bf, 'loyalty', '?')})")

    # ── Kaito +1: emblem "Ninjas you control get +1/+1" ───────────────────
    def _kaito_plus_one(self, gs: GameState, opponent: GameState):
        """
        Kaito +1: 'You get an emblem with "Ninjas you control get +1/+1."'

        SIM APPROXIMATION: the emblem buff itself is NOT wired in combat
        -- `gs._ninja_emblem = True` is set as a marker but nothing reads
        it. The real value modelled here is loyalty banking: +1 increases
        Kaito's loyalty, which means he survives longer (more attacks,
        more +0 draws on subsequent turns). When the engine adds combat
        Ninja-buff support, this will become a true emblem activation.

        Pilot rule (option B from the Kaito tree): when we have a 2nd Kaito
        in hand, +1 Kaito1 to bank loyalty and set up the swing → ninjutsu
        Kaito2 over Kaito1 line.

        Fire when:
          (a) Kaito on board this turn AND (-2 not used) AND (+0 not used)
          (b) We have 2nd Kaito in hand OR we have other Ninjas
              (note: emblem buff is NOT applied in current engine; see above)
          (c) We're not in a desperate position (life lead OK, opp board
              not threatening lethal next turn)
        """
        if opponent is None:
            return
        kaito_on_bf = next((c for c in gs.zones.battlefield if c.name == KAITO), None)
        if kaito_on_bf is None:
            return
        if getattr(kaito_on_bf, '_minus2_used', False):
            return
        if getattr(kaito_on_bf, '_zero_used_turn', -1) == gs.turn:
            return
        if getattr(kaito_on_bf, '_plus1_used_turn', -1) == gs.turn:
            return

        # Need a Ninja to buff (Kaito2 in hand for ninjutsu chain, or
        # other Ninjas/ninjutsu-capable creatures on board)
        kaito_in_hand = any(c.name == KAITO for c in gs.zones.hand)
        # Floodpits is a Merfolk not Ninja, but Spyglass Siren creates
        # tokens; ninjutsu lines benefit from emblem on any future Ninja.
        ninjas_on_bf = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and 'ninja' in (getattr(c, 'type_line', '') or '').lower()]
        if not kaito_in_hand and not ninjas_on_bf:
            return  # nothing to buff

        # Don't +1 in desperate position -- -2 lock or +0 draw might be
        # more urgent. Skip if opp board pressure is meaningful.
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()
                         and not getattr(c, 'tapped', False)]
        opp_attack_power = sum(safe_power(c) for c in opp_creatures)
        if opp_attack_power >= gs.life - 4:
            return  # too risky -- prefer -2 or removal

        # Fire +1 -- bank loyalty
        kaito_on_bf._plus1_used_turn = gs.turn
        if hasattr(kaito_on_bf, 'loyalty') and kaito_on_bf.loyalty is not None:
            kaito_on_bf.loyalty += 1
        # Track emblem state on GameState so future Ninja casts can buff
        gs._ninja_emblem = True
        gs._log(f"  [Kaito +1] emblem 'Ninjas +1/+1' "
                f"(loyalty -> {getattr(kaito_on_bf, 'loyalty', '?')})")

    # ── Kaito +0: surveil 2, draw if opp lost life this turn ──────────────
    def _kaito_plus_zero(self, gs: GameState, opponent: GameState):
        """
        Kaito +0: 'Surveil 2. Then draw a card for each opponent who lost
        life this turn.' Default action when -2 isn't justified.

        Pilot rule: don't plan for the draw -- it's opportunistic. Fire
        +0 whenever Kaito is on board, an ability hasn't already been
        used this turn, and we're past the trivial cases.

        Surveil 2 is approximated as a no-op (sim doesn't model deck
        ordering). The draw fires if opp.life dropped from our turn
        start (combat damage, painlands tapped, etc.).
        """
        if opponent is None:
            return
        kaito_on_bf = next((c for c in gs.zones.battlefield if c.name == KAITO), None)
        if kaito_on_bf is None:
            return
        if getattr(kaito_on_bf, '_minus2_used', False):
            return  # we already used -2 this turn
        if getattr(kaito_on_bf, '_zero_used_turn', -1) == gs.turn:
            return  # already +0'd this turn

        loyalty = getattr(kaito_on_bf, 'loyalty', 3) or 3
        if loyalty <= 0:
            return

        # Mark used
        kaito_on_bf._zero_used_turn = gs.turn

        # Did opp lose life this turn? (combat, painlands, drain effects)
        opp_life_now = opponent.life
        opp_life_start = getattr(self, '_opp_life_at_turn_start', 20)
        opp_lost_life = opp_life_now < opp_life_start

        if opp_lost_life:
            # Draw a card (surveil 2 effect is approximated by the draw alone)
            if gs.zones.library:
                drawn = gs.zones.library.pop(0)
                gs.zones.hand.append(drawn)
                gs._log(f"  [Kaito +0] surveil 2 + draw {drawn.name} "
                        f"(opp lost {opp_life_start - opp_life_now} life)")
            else:
                gs._log("  [Kaito +0] surveil 2 (library empty, no draw)")
        else:
            gs._log("  [Kaito +0] surveil 2 (no draw -- opp life stable)")

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
    # Outlaw types Shoot the Sheriff CAN'T target (non-outlaw only)
    _OUTLAW_TYPES = {"assassin", "mercenary", "pirate", "rogue", "warlock"}

    def _kill_target(self, gs: GameState, target) -> bool:
        """Try to kill target creature/planeswalker with removal.

        Validity gates per Scryfall:
          - Requiting Hex     {B}  : creature with MV <= 2
          - Long Goodbye      {1B} : creature/PW with MV <= 3, uncounterable
          - Shoot the Sheriff {1B} : non-outlaw creature (any MV)
                              outlaws: Assassin, Mercenary, Pirate, Rogue, Warlock
          - Bitter Triumph    {1B} : any creature/PW (cost: 3 life or discard)

        Prefer narrowest legal removal (saves flex for harder targets).
        """
        target_cmc = getattr(target, 'cmc', 0) or 0
        target_types_lower = (getattr(target, 'type_line', '') or '').lower()
        is_outlaw = any(t in target_types_lower for t in self._OUTLAW_TYPES)
        is_planeswalker = "planeswalker" in target_types_lower

        # Build prioritized candidate list (narrowest legal first)
        for card in list(gs.zones.hand):
            if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                continue
            name = card.name

            # 1. Requiting Hex: narrowest, MV<=2 creature only (no PW)
            if name == REQUITING and target_cmc <= 2 and not is_planeswalker:
                gs.cast_spell(card)
                return True
            # 2. Long Goodbye: MV<=3, creature OR PW, uncounterable
            if name == LONG_GOODBYE and target_cmc <= 3:
                gs.cast_spell(card)
                return True
            # 3. Shoot the Sheriff: any MV creature, but NON-OUTLAW only
            if name == SHOOT and not is_planeswalker and not is_outlaw:
                gs.cast_spell(card)
                return True
            # 4. Bitter Triumph: any creature/PW (most flexible, saved last)
            if name == BITTER:
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

        # ── Snapshot opp life at start of my turn (for Kaito +0 draw) ──
        # The +0 ability draws iff opp lost life this turn. Snapshot once
        # per turn so we can detect mid-turn life loss via combat or
        # painlands/spell-cost damage.
        if getattr(self, '_kaito_life_snap_turn', -1) != gs.turn:
            self._opp_life_at_turn_start = (opponent.life if opponent else 20)
            self._kaito_life_snap_turn = gs.turn

        # ── Kaito ability priority: -2 (gated) > +0 (draw) > +1 (emblem) ──
        # Real pilot tree: prefer to LOCK threats (-2) when needed, DRAW
        # value (+0) when opp lost life, otherwise BANK loyalty (+1) for
        # the ninjutsu chain. Each method gates on its own preconditions.
        self._kaito_minus2(gs, opponent)
        self._loch_mare_tap(gs, opponent)
        self._kaito_plus_zero(gs, opponent)
        self._kaito_plus_one(gs, opponent)

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

            # ── PRIORITY 0 (T1-T3 only): Into the Flood Maw on opp's
            # earthbended-land creature OR biggest threat. Vs landfall /
            # rhythm / Ouroboroid the early-tempo bounce is huge --
            # resets counters, stops landfall pump, sets back their
            # mana sequence by a turn. After T3, the bounce loses
            # tempo value (they've already deployed key threats).
            if gs.turn <= 3:
                # Earthbended land = land that's also a creature on
                # opp's side. Fall back to opp's biggest creature.
                earthbended_lands = [c for c in opponent.zones.battlefield
                                     if c.is_land() and c.has(Tag.CREATURE)]
                # Otherwise pick highest-power non-land creature
                non_land_threats = [c for c in opp_creatures
                                    if getattr(c, 'power', None) is not None]
                target = None
                if earthbended_lands:
                    target = earthbended_lands[0]
                elif non_land_threats:
                    target = max(non_land_threats, key=safe_power)
                if target is not None:
                    for card in list(gs.zones.hand):
                        if card.name == INTO_FLOOD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                            gs._bounce_target_name = target.name
                            gs.cast_spell(card)
                            gs._bounce_target_name = None
                            gs._log(f"  [vs landfall/rhythm/ouro T{gs.turn}] "
                                    f"Into the Flood Maw -> {target.name} "
                                    f"({'earthbended land' if target.is_land() else 'biggest threat'})")
                            break

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

            # 3. Into the Flood Maw: late-game (post-T3) fallback bounce
            #    of counter-laden creatures (resets all counters).
            #    The early-priority bounce is handled in PRIORITY 0 above.
            if gs.turn > 3:
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

        # 5. Loch Mare activation (sorcery speed): {1}{U} remove counter -> draw
        self._try_loch_mare_draw(gs)

        # 6. Qarsi Revenant Renew (sorcery speed): {2}{B} from GY -> grant
        #    flying/deathtouch/lifelink to a creature
        self._try_qarsi_renew(gs)

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
        """Activate Stormchaser's Talent levels via engine.classes.level_up,
        which BOTH pays the cost AND fires the level effect (Level 2: return
        target instant/sorcery from GY to hand; Level 3: each I/S cast
        creates a 1/1 prowess Otter via class_on_spell_cast hook).

        Pre-fix (2026-05-08): this method set sct._class_level manually,
        which never fired the level-2/3 effects (they read card.counters,
        not _class_level). Recursion engine was effectively dead. This
        is the bug audit identified -- Stormchaser's Talent only Level 1
        Otter ETB was firing in sim.
        """
        from engine.classes import level_up
        sct = next((c for c in gs.zones.battlefield
                   if c.name == STORMCHASER), None)
        if sct is None:
            return
        # Try to advance level repeatedly until cost can't be paid.
        # level_up returns True on success. Two attempts max (Lvl 1->2, Lvl 2->3).
        for _ in range(2):
            if not level_up(sct, gs):
                break

    # ── Loch Mare activated ability ──────────────────────────────────────────
    def _try_loch_mare_draw(self, gs: GameState):
        """Activate Loch Mare: {1}{U}, remove a -1/-1 counter -> draw a card.
        Loch Mare enters with 3 -1/-1 counters (effective 1/2).
        Each activation removes a counter (effectively makes it bigger AND
        draws). At 0 counters left, no more activations possible.
        Stop after the first activation per turn so we don't dump all 3."""
        from data.card import Tag
        loch = next((c for c in gs.zones.battlefield
                    if c.name == "Loch Mare" and c.has(Tag.CREATURE)), None)
        if loch is None:
            return
        # Loch Mare enters with -3 counters; activations subtract more
        # (negative counters = -1/-1 stacked). So counters < 0 means
        # we still have -1/-1 counters to remove.
        # Convention: we used `card.counters -= 3` on ETB. Each draw
        # activation: counters += 1 (remove one -1/-1 counter).
        if (loch.counters or 0) >= 0:
            return  # No counters left to remove
        if not gs.mana_pool.can_cast("1U", 2):
            return
        try:
            gs.mana_pool.pay_cost("1U", 2)
            loch.counters += 1  # remove one -1/-1 counter
            gs.zones.draw(1)
            gs._log(f"  [Loch Mare] removed -1/-1 counter, drew a card "
                    f"(counters now {loch.counters})")
        except Exception:
            pass

    # ── Qarsi Revenant Renew (GY-cast) ───────────────────────────────────────
    def _try_qarsi_renew(self, gs: GameState):
        """Activate Qarsi Revenant Renew: {2}{B}, exile from graveyard ->
        target creature gains flying/deathtouch/lifelink counters.
        Sorcery speed only. We pick our largest creature without those
        keywords as the target."""
        from data.card import Tag
        from engine.keywords import KWTag
        from engine.match_state import safe_power
        qarsi = next((c for c in gs.zones.graveyard
                     if c.name == QARSI), None)
        if qarsi is None:
            return
        if not gs.mana_pool.can_cast("2B", 3):
            return
        # Target: our largest creature that doesn't already have all 3 keywords
        my_creatures = [c for c in gs.zones.battlefield
                       if c.has(Tag.CREATURE) and not c.is_land()
                       and not (KWTag.FLYING in c.tags
                                and KWTag.DEATHTOUCH in c.tags
                                and KWTag.LIFELINK in c.tags)]
        if not my_creatures:
            return
        target = max(my_creatures, key=safe_power)
        try:
            gs.mana_pool.pay_cost("2B", 3)
            gs.zones.graveyard.remove(qarsi)
            gs.zones.exile.append(qarsi)
            target.tags.add(KWTag.FLYING)
            target.tags.add(KWTag.DEATHTOUCH)
            target.tags.add(KWTag.LIFELINK)
            gs._log(f"  [Qarsi Renew] exile from GY, granted "
                    f"flying/DT/LL to {target.name}")
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
