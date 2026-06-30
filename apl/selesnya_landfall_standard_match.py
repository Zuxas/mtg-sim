"""
apl/selesnya_landfall_standard_match.py -- Selesnya Landfall match APL (Standard / PT SOS 2026)

Based on Christoffer Larsen / Nathan Steuer lists (Top 2, PT SOS 2026).
PT WR: 63.81% overall. Beats Prowess 62.9%, Mono-Green 65.4%.

Key engine:
  Badgermole Cub ({1}{G}): landfall +1/+1 counter — grows every turn, NEVER trade
  Mightform Harmonizer ({2}{G}{G}): landfall doubles target creature's power until EoT
  Erode ({W} instant): destroy any creature/PW, they get a basic land
  Snakeskin Veil ({G} instant): +1/+1 counter + hexproof — counter their removal
  Bushwhack ({G} sorcery, modal): "target creature +2/+2 + trample until EoT" in combat
  Lumbering Worldwagon ({2}{G}): power = lands you control, fetches basics on ETB/attack
  Surrak, Elusive Hunter ({2}{G}): uncounterable, trample, triggers on being targeted
  Kutzil, Malamet Exemplar ({1}{G}{W}): opponents can't cast spells on your turn
    → play Kutzil BEFORE Erode to lock out Snakeskin Veil responses

Timing priorities:
  1. Pre-combat: Erode their best blocker (or Kutzil if available → then Erode)
  2. Attack with everyone EXCEPT Badgermole Cub into a profitable trade
  3. Trigger Mightform Harmonizer: double the creature with most counters
  4. Combat trick: Bushwhack (+2/+2 trample) to break a bad block
  5. End step: nothing flash-worthy in main deck
  6. Respond: Snakeskin Veil when they target our key creature
"""
from data.card import Tag
from apl.aware_match_apl import AwareMatchAPL, BLINK_BAIT
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness

BADGERMOLE   = "Badgermole Cub"
HARMONIZER   = "Mightform Harmonizer"
ELVES        = "Llanowar Elves"
CHOCOBO      = "Sazh's Chocobo"
ASCENSION    = "Earthbender Ascension"
SURRAK       = "Surrak, Elusive Hunter"
WORLDWAGON   = "Lumbering Worldwagon"
ERODE        = "Erode"
BUSHWHACK    = "Bushwhack"
SNAKESKIN    = "Snakeskin Veil"
KUTZIL       = "Kutzil, Malamet Exemplar"
ESCAPE_TUNN  = "Escape Tunnel"
BA_SING_SE   = "Ba Sing Se"
FABLED_PASS  = "Fabled Passage"

# Creatures we never want to trade (too much invested value)
PROTECT_ALWAYS = {BADGERMOLE, HARMONIZER}

# Fetch lands that trigger landfall when sacrificed — play these first
FETCH_LANDS = {FABLED_PASS, ESCAPE_TUNN}


class SelesnyaLandfallStandardMatchAPL(AwareMatchAPL):
    name        = "Selesnya Landfall"
    ARCHETYPE   = "aggro"
    COUNTER_COST  = 0         # no counters, tap out freely
    COUNTER_CARDS = set()
    FLASH_THREATS = set()     # no flash threats in main deck

    # Erode is instant-speed removal — fired by _match_cast_removal and pre-combat
    MATCH_REMOVAL = {
        ERODE: ("W", None),   # destroys any creature or planeswalker
    }
    MATCH_WIPES        = set()
    MATCH_EXILE        = set()          # Erode destroys, doesn't exile
    MATCH_GRANTS_LAND  = {ERODE}       # Erode: opponent fetches a basic on resolution

    # Sideboard plans from mtg.cardsrealm guide + PT SOS data
    SB_PLANS = {
        "aggro": (
            # vs Gruul Aggro / Mirror: Sheltered by Ghosts + Seam Rip + Surrak
            # Dyadrine too slow vs racing decks; Felidar Retreat cut (SB pivot)
            ["Sheltered by Ghosts", "Sheltered by Ghosts", "Seam Rip",
             "Surrak, Elusive Hunter", "Surrak, Elusive Hunter"],
            ["Dyadrine, Synthesis Amalgam", "Dyadrine, Synthesis Amalgam",
             "Felidar Retreat", "Lumbering Worldwagon", "Icetill Explorer"],
        ),
        "control": (
            # vs Azorius Control / Jeskai: Frenzied Baloth (hexproof) + Surrak + Requisition Raid
            # Cut Snakeskin Veil (their removal is exile-based) and Titanic Growth
            ["Frenzied Baloth", "Frenzied Baloth", "Surrak, Elusive Hunter",
             "Surrak, Elusive Hunter", "Requisition Raid"],
            ["Snakeskin Veil", "Snakeskin Veil", "Titanic Growth",
             "Titanic Growth", "Dyadrine, Synthesis Amalgam"],
        ),
        "combo": (
            # vs Izzet Lessons / Graveyard: Rest in Peace + Requisition Raid + Surrak
            ["Rest in Peace", "Rest in Peace", "Requisition Raid",
             "Surrak, Elusive Hunter", "Surrak, Elusive Hunter"],
            ["Sazh's Chocobo", "Tifa Lockhart",
             "Dyadrine, Synthesis Amalgam", "Lumbering Worldwagon", "Icetill Explorer"],
        ),
        "tempo": (
            # vs Izzet Prowess / tempo: Sheltered + Surrak; cut slow engine pieces
            ["Sheltered by Ghosts", "Sheltered by Ghosts", "Seam Rip",
             "Surrak, Elusive Hunter", "Mossborn Hydra", "Mossborn Hydra"],
            ["Dyadrine, Synthesis Amalgam", "Dyadrine, Synthesis Amalgam",
             "Lumbering Worldwagon", "Icetill Explorer",
             "Keen-Eyed Curator", "Erode"],
        ),
        "ramp": (
            # vs Mono Green Landfall / mirror: Sheltered + Seam Rip to disrupt their engine
            ["Sheltered by Ghosts", "Sheltered by Ghosts", "Seam Rip",
             "Surrak, Elusive Hunter", "Mossborn Hydra", "Mossborn Hydra"],
            ["Dyadrine, Synthesis Amalgam", "Dyadrine, Synthesis Amalgam",
             "Felidar Retreat", "Lumbering Worldwagon",
             "Icetill Explorer", "Keen-Eyed Curator"],
        ),
    }

    # ------------------------------------------------------------------
    # Mulligan / bottom
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands   = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in {BADGERMOLE, CHOCOBO, ELVES})
        if lands == 0 or lands > 5:
            return False
        return (threats >= 1 and lands >= 2) or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    # ------------------------------------------------------------------
    # Land play — fetch lands first for double landfall
    # ------------------------------------------------------------------

    def reserve_mana(self, gs, opponent):
        """Hold 1 land for Erode when we have it in hand."""
        has_erode = any(c.name == ERODE for c in gs.zones.hand)
        gs.mana_reserve = 1 if has_erode else 0

    def _play_best_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Prefer fetch lands: they trigger landfall twice
        # (once when they enter, once when the fetched basic enters)
        fetches = [c for c in lands if c.name in FETCH_LANDS]
        basics  = [c for c in lands if c.name not in FETCH_LANDS]
        land = (fetches or basics)[0]
        gs.play_land(land)
        self._fire_landfall_triggers(gs)   # trigger 1: land enters

        # Fabled Passage / Escape Tunnel — sac to fetch a basic (trigger 2)
        if land.name in FETCH_LANDS and land in gs.zones.battlefield:
            gs.zones.battlefield.remove(land)
            gs.zones.graveyard.append(land)
            # Find a basic to fetch
            basics_in_lib = [c for c in gs.zones.library if c.is_land()
                             and c.name not in FETCH_LANDS]
            if basics_in_lib:
                fetched = basics_in_lib[0]
                gs.zones.library.remove(fetched)
                gs.zones.battlefield.append(fetched)
                fetched.tapped = True
                fetched.turn_entered = gs.turn
                self._fire_landfall_triggers(gs)   # trigger 2: basic enters
                gs._log(f"  {land.name}: sac → fetch {fetched.name} (2nd landfall)")

    def _fire_landfall_triggers(self, gs):
        """Apply landfall ETB effects for Badgermole Cub and Harmonizer."""
        for c in gs.zones.battlefield:
            if c.name == BADGERMOLE:
                try:
                    p = int(c.power) + 1
                    t = int(c.toughness) + 1
                    c.power     = str(p)
                    c.toughness = str(t)
                except (ValueError, TypeError):
                    pass
            elif c.name == HARMONIZER:
                # Doubles the creature with the most counters / highest power
                creatures = [x for x in gs.zones.battlefield
                             if x.has(Tag.CREATURE) and x is not c and not x.is_land()]
                if creatures:
                    target = max(creatures, key=lambda x: (
                        getattr(x, 'counters', 0), safe_power(x)))
                    try:
                        target.power = str(int(target.power) * 2)
                    except (ValueError, TypeError):
                        pass

    # ------------------------------------------------------------------
    # Main phase
    # ------------------------------------------------------------------

    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._opp_gs = opponent
        self._play_best_land(gs)
        gs.tap_lands()

        # If Kutzil is in hand and we have enough mana, play it BEFORE Erode
        # so opponent can't respond with Snakeskin Veil to our removal
        for card in list(gs.zones.hand):
            if card.name == KUTZIL:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  Kutzil: opponents locked out of spells this turn")
                    break

        # Erode their best threat pre-combat (fires standard removal logic)
        self._match_cast_removal(gs, opponent)

        # Deploy curve cheapest-first — prioritize Elves T1, Badgermole/Chocobo T2
        changed = True
        while changed:
            changed = False
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE)
                        and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if castable:
                spell = min(castable, key=lambda c: getattr(c, 'cmc', 0))
                if gs.cast_spell(spell):
                    if spell.name == ASCENSION:
                        # Earthbender Ascension ETB: tutor + play a basic = extra landfall
                        basics = [x for x in gs.zones.library if x.is_land()
                                  and x.name not in FETCH_LANDS]
                        if basics:
                            land = basics[0]
                            gs.zones.library.remove(land)
                            gs.zones.battlefield.append(land)
                            land.turn_entered = gs.turn
                            self._fire_landfall_triggers(gs)
                    changed = True

        # Cast non-creature spells (Bushwhack in ramp mode to find land)
        for card in list(gs.zones.hand):
            if not card.is_land() and not card.has(Tag.CREATURE):
                if card.name == BUSHWHACK:
                    # Use ramp mode pre-combat (save +2/+2 for combat trick)
                    # Only use land-fetch mode if we're land-light
                    my_lands = sum(1 for c in gs.zones.battlefield if c.is_land())
                    if my_lands <= 3:
                        if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                            gs.cast_spell(card)
                elif gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)

        # Ba Sing Se earthbend: {2}{G}{T} (sorcery speed) exiles and returns
        # 2 lands — each re-entry triggers landfall. Use AFTER threats are deployed
        # so we have creatures to pump with Mightform Harmonizer.
        harmonizer_up = any(c.name == HARMONIZER for c in gs.zones.battlefield
                            if not c.is_land())
        if harmonizer_up:
            ba_sing = next((c for c in gs.zones.battlefield
                            if c.name == BA_SING_SE
                            and not getattr(c, 'tapped', False)), None)
            if ba_sing and gs.mana_pool.total() >= 3:
                # Pay {2}{G} for earthbend activation — deduct from pool
                gs.mana_pool.pay("2G", 3)
                ba_sing.tapped = True
                earthbend_targets = [c for c in gs.zones.battlefield
                                     if c.is_land() and c is not ba_sing][:2]
                for land in earthbend_targets:
                    # Exile and immediately return tapped — triggers landfall
                    gs.zones.battlefield.remove(land)
                    gs.zones.battlefield.append(land)
                    land.tapped = True
                    self._fire_landfall_triggers(gs)
                    gs._log(f"  Ba Sing Se earthbend: {land.name} re-enters (landfall)")

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    # ------------------------------------------------------------------
    # Declare attackers — protect Badgermole Cub from bad trades
    # ------------------------------------------------------------------

    # Selesnya protects its snowball engine pieces from even trades. The base
    # AwareMatchAPL.declare_attackers honours PROTECT_FROM_TRADE.
    PROTECT_FROM_TRADE = PROTECT_ALWAYS

    def declare_attackers(self, gs: GameState, opponent: GameState) -> list:
        # Mightform Harmonizer doubling fires on attack BEFORE we evaluate combat.
        self._fire_landfall_triggers(gs)
        # Delegate to the calibrated base heuristic (2026-06-29). The previous
        # body here was a DUPLICATE of the same universal-best-blocker bug fixed
        # in aware_match_apl.py: it applied the opp's single biggest creature as a
        # blocker for EVERY attacker, holding Selesnya's whole board back against
        # one large Prowess creature. Fixing both seats moved Selesnya-vs-Prowess
        # from 52.7% (Prowess seat only) to ~60% (PT truth 62.9%). PROTECT_ALWAYS
        # (Badgermole Cub / Mightform Harmonizer) is preserved via
        # PROTECT_FROM_TRADE so those engine pieces still never trade.
        return super().declare_attackers(gs, opponent)

    # ------------------------------------------------------------------
    # Combat trick: Bushwhack (+2/+2 + trample) to save an attacker
    # or push lethal through
    # ------------------------------------------------------------------

    def combat_trick(self, gs: GameState, opponent: GameState,
                     attackers: list, blocker_assignments: dict):
        assign_map = {id(k): v for k, v in blocker_assignments.items()} \
                     if blocker_assignments else {}

        # --- Trick 1: Escape Tunnel sac → landfall → Mightform Harmonizer doubles ---
        # Escape Tunnel: sac to fetch a basic (instant speed, no restriction).
        # The fetched basic enters tapped, triggering landfall.
        # If Mightform Harmonizer is in play, this doubles an attacker's power
        # AFTER blockers are declared — opponent can't respond.
        harmonizer = next((c for c in gs.zones.battlefield
                           if c.name == HARMONIZER and not c.is_land()), None)
        tunnel = next((c for c in gs.zones.battlefield
                       if c.name == ESCAPE_TUNN), None)
        if harmonizer and tunnel and attackers:
            # Find the attacker with the most power (best doubling target)
            target_atk = max(attackers, key=lambda c: safe_power(c))
            # Sac Escape Tunnel → fetch basic → landfall
            gs.zones.battlefield.remove(tunnel)
            gs.zones.graveyard.append(tunnel)
            basics = [c for c in gs.zones.library if c.is_land()]
            if basics:
                new_land = basics[0]
                gs.zones.library.remove(new_land)
                gs.zones.battlefield.append(new_land)
                new_land.tapped     = True
                new_land.turn_entered = gs.turn
                # Landfall: Badgermole Cub gets counter + Harmonizer fires once.
                # _fire_landfall_triggers handles the Harmonizer doubling internally.
                # Do NOT also manually double target_atk — that would be 4x total.
                self._fire_landfall_triggers(gs)
                gs._log(f"  Escape Tunnel -> landfall -> Harmonizer doubles "
                        f"{target_atk.name} (via _fire_landfall_triggers)")
            return  # used our trick

        # --- Trick 2: Bushwhack +2/+2 trample to save a dying attacker ---
        for atk in attackers:
            blks = assign_map.get(id(atk), [])
            if not blks:
                continue
            total_blk_p = sum(safe_power(b) for b in blks)
            atk_t       = safe_toughness(atk)

            if total_blk_p >= atk_t:
                # Bushwhack is a SORCERY -- cannot be cast during combat.
                # Removed from combat_trick; use Snakeskin Veil (instant) instead.
                pass

        # --- Trick 3: Snakeskin Veil as pump to save a dying attacker ---
        for atk in attackers:
            blks = assign_map.get(id(atk), [])
            if not blks:
                continue
            total_blk_p = sum(safe_power(b) for b in blks)
            atk_t       = safe_toughness(atk)
            if total_blk_p >= atk_t and atk.name in PROTECT_ALWAYS:
                veil = next((c for c in gs.zones.hand if c.name == SNAKESKIN), None)
                if veil and gs.mana_pool.can_cast(veil.mana_cost, veil.cmc):
                    gs.mana_pool.pay(veil.mana_cost, veil.cmc)
                    gs.zones.hand.remove(veil)
                    gs.zones.graveyard.append(veil)
                    try:
                        atk.power     = str(int(atk.power) + 1)
                        atk.toughness = str(int(atk.toughness) + 1)
                    except (ValueError, TypeError):
                        pass
                    gs._log(f"  Snakeskin Veil: +1/+1 hexproof on {atk.name}")
                    return

    # ------------------------------------------------------------------
    # Respond to removal with Snakeskin Veil on our key creature
    # ------------------------------------------------------------------

    def respond_to_spell(self, gs: GameState, opponent: GameState, spell):
        """
        When opponent casts removal, protect our most valuable creature
        with Snakeskin Veil (+1/+1 + hexproof).
        'Most valuable' = Badgermole Cub (most counters) or Harmonizer.
        """
        from engine.stack import classify_card, InteractionType
        if spell:
            itype = classify_card(spell)
            if itype not in (InteractionType.REMOVAL, InteractionType.BURN):
                return None  # not targeting our creatures

        # Find Snakeskin Veil in hand
        veil = next((c for c in gs.zones.hand if c.name == SNAKESKIN), None)
        if veil and gs.mana_pool.can_cast(veil.mana_cost, veil.cmc):
            # Find our most valuable target (Badgermole Cub first)
            my_creatures = [c for c in gs.zones.battlefield
                            if c.has(Tag.CREATURE) and not c.is_land()]
            if not my_creatures:
                return None
            # Priority: protect Badgermole Cub, then Harmonizer, then biggest
            for name in (BADGERMOLE, HARMONIZER):
                if any(c.name == name for c in my_creatures):
                    return veil
            # Fallback: protect our biggest creature
            return veil

        return None

    # ------------------------------------------------------------------
    # Pre-combat priority: Erode their best blocker before combat
    # (inherited from AwareMatchAPL via _kill_with_removal)
    # ------------------------------------------------------------------

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        """Erode their largest creature before it can block."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return

        # Kill their biggest blocker to clear the path
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) >= 2:
            if self._kill_with_removal(gs, opponent, target, prefer_exile=False):
                gs._log(f"  [pre-combat] Erode kills {target.name}")

    # ------------------------------------------------------------------
    # Trigger ordering: Mightform Harmonizer doubles most-countered creature
    # ------------------------------------------------------------------

    def order_triggers(self, gs: GameState, triggers: list) -> list:
        """
        When Mightform Harmonizer and Badgermole Cub both trigger on land drop,
        resolve Badgermole Cub's counter first (so Harmonizer doubles the
        already-incremented power).
        """
        def trigger_priority(t):
            name = getattr(t, 'source_name', '') or ''
            if BADGERMOLE in name:    return 0   # counter first
            if HARMONIZER in name:    return 1   # doubling second
            return 2
        return sorted(triggers, key=trigger_priority)
