"""apl/izzet_prowess_standard_match.py -- Izzet Prowess Standard match APL.

PT SOS 2026 field share: 31.4% (151/481 players). WR: 49.8%.
Deck: tempo-aggro using prowess triggers and cheap noncreature spells.

Key engines:
  Slickshot Show-Off ({1}{R}): flying, haste, +2/+0 per noncreature spell cast
  Colorstorm Stallion ({1}{U}{R}): haste, ward 1, grows with instants/sorceries
  Eddymurk Crab ({5}{U}{U} - discounted): flash, ETB bounce a creature
    -> costs {1} less per instant/sorcery in GY; with 5+ spells = {U}{U}
    -> key end-step play: flash in, bounce their Badgermole Cub (wipes counters)
  Burst Lightning ({R}): 2 damage to any target (4 main) — primary removal
  Boomerang Basics ({1}{U}): bounce any permanent back to hand
  Three Steps Ahead ({U} Spree): +{1}{U} = counter a spell (main 2x)
  Stormchaser's Talent ({U}): enchantment, Level 1 creates 1/1 Otter with prowess
  Slickshot Show-Off + Stormchaser's Talent + Burst Lightning = kill T3-4 goldfish

Timing priorities:
  1. Main phase: cast Burst Lightning on Landfall threats before they grow
  2. Counter: Three Steps Ahead or Spell Pierce (post-board) on key Landfall pieces
  3. End step: flash in Eddymurk Crab to bounce Badgermole Cub (wipes its counters)
  4. Attack: Slickshot (flying, pumped by spells) often unblockable
  5. Hold 1 mana pre-combat to represent counter (bluff mana)
  6. Combat: bounce a blocker with Boomerang Basics/Eddymurk to push damage
"""
from apl.aware_match_apl import AwareMatchAPL
from apl.izzet_prowess_standard import IzzetProwessAPL
from engine.game_state import GameState
from engine.match_state import safe_toughness


class IzzetProwessStandardMatchAPL(AwareMatchAPL, IzzetProwessAPL):
    ARCHETYPE = "tempo"

    # Hold 1 mana pre-combat: represents Three Steps Ahead counter mode ({U}+{1}{U})
    COUNTER_COST  = 1
    COUNTER_CARDS = {"Three Steps Ahead", "Spell Pierce"}   # Spell Pierce is sideboard

    # Flash creatures we deploy at end of opponent's turn
    FLASH_THREATS = {"Eddymurk Crab"}   # flash, ETB bounces their creature

    # Actual removal suite in this deck
    MATCH_REMOVAL = {
        "Burst Lightning":   ("R",    2),    # 2 damage — kills ≤2 toughness (4 main)
        "Boomerang Basics":  ("1U",   None), # bounce any — returns to hand
        "Eddymurk Crab":     ("UU",   None), # ETB bounce — returns to hand (flash)
        "Fire Magic":        ("R",    2),    # sideboard burn ≤2
        "Get Out":           ("R",    4),    # sideboard exile ≤4
        "Sear":              ("1R",   4),    # sideboard burn ≤4
        "Slagstorm":         ("1RR",  3),    # sideboard wipe ≤3
    }
    MATCH_WIPES   = {"Slagstorm"}
    MATCH_EXILE   = {"Get Out"}
    MATCH_BOUNCE  = {"Boomerang Basics", "Eddymurk Crab"}  # return to hand

    # Creatures to kill specifically pre-combat (Prowess's own pre_combat window)
    BLINK_TARGETS = {
        "Badgermole Cub",       # grows each land drop — kill while still small
        "Mightform Harmonizer", # doubling engine — must die immediately
        "Sazh's Chocobo",       # grows with lands
        "Llanowar Elves",       # cuts off T2 Badgermole Cub mana
    }

    def pre_combat_instant(self, gs, opponent):
        """Kill Landfall's engine pieces before they can attack or double."""
        from data.card import Tag
        from engine.match_state import safe_toughness
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        for name in ("Badgermole Cub", "Mightform Harmonizer",
                     "Sazh's Chocobo", "Llanowar Elves"):
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c, prefer_exile=False):
                        gs._log(f"  [pre-combat] killed {c.name} (T{safe_toughness(c)})")
                        return

    # Landfall key threats — counter these at any CMC
    _COUNTER_PRIORITY = {
        "Badgermole Cub",
        "Mightform Harmonizer",
        "Earthbender Ascension",
        "Sazh's Chocobo",
        "Lumbering Worldwagon",
        "Kutzil, Malamet Exemplar",
    }

    SB_PLANS = {
        "aggro": (
            ["2 Sear", "1 Slagstorm", "2 Get Out"],
            ["2 Three Steps Ahead", "2 Flow State", "1 Stock Up"],
        ),
        "control": (
            ["2 Spell Pierce", "3 Ral, Crackling Wit"],
            ["2 Burst Lightning", "2 Boomerang Basics", "1 Flow State"],
        ),
        "combo": (
            ["2 Spell Pierce", "2 Soul-Guide Lantern"],
            ["2 Boomerang Basics", "1 Flow State", "1 Burst Lightning"],
        ),
        "ramp": (
            ["2 Spell Pierce", "3 Ral, Crackling Wit"],
            ["2 Burst Lightning", "2 Boomerang Basics", "1 Flow State"],
        ),
        "tempo": (
            ["2 Spell Pierce", "2 Get Out", "1 Slagstorm"],
            ["2 Three Steps Ahead", "2 Boomerang Basics", "1 Flow State"],
        ),
    }

    # Plot cost for Slickshot Show-Off: {1}{R}
    PLOT_COST     = "1R"
    PLOT_CMC      = 2
    PLOTTED_ZONE  = "__prowess_plotted__"   # attribute name on gs

    def _plotted(self, gs):
        """Return the list of plotted (exiled) cards on this game state."""
        if not hasattr(gs, self.PLOTTED_ZONE):
            setattr(gs, self.PLOTTED_ZONE, [])
        return getattr(gs, self.PLOTTED_ZONE)

    def _opp_erode_count(self) -> int:
        """Estimate how many Erode-style removal spells opponent can cast this turn."""
        opp = getattr(self, '_opp_gs', None)
        if opp is None:
            return 0
        # Each 1 untapped white land = 1 potential Erode
        return self._opp_untapped_lands()

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """
        Match-aware main phase with Plot mechanic:

        1. Cast plotted Slickshot from exile on the turn opponent is tapped out
           — chain all noncreature spells immediately for maximum pump damage
        2. If opponent has open mana (potential Erode):
           a. If {1}{R} available and no counter: Plot Slickshot instead of casting
              (exile it now, cast free next turn when opponent commits their mana)
           b. If no Plot mana: sandbag (hold in hand, cast bait spells)
        3. Account for 2-Erode scenario: if opponent has 2+ untapped lands,
           even casting from exile risks getting Eroded twice — wait for 0 untapped
        """
        from apl.izzet_prowess_standard import IzzetProwessAPL
        from data.card import Tag, Tag as _Tag
        from engine.keywords import KWTag

        self._opp_gs = opponent
        self._match_cast_removal(gs, opponent)

        KEY_THREATS    = {"Slickshot Show-Off", "Colorstorm Stallion"}
        opp_untapped   = self._opp_untapped_lands()
        opp_has_removal = self._opp_likely_has_instant()
        have_counter   = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)

        # ── Step 1: Execute plotted Slickshot if timing is right ──────────
        plotted = self._plotted(gs)
        castable_from_exile = [
            c for c in plotted
            if getattr(c, 'plotted_on_turn', 0) < gs.turn
        ]

        if castable_from_exile:
            # Timing check: cast from exile only when opponent is tapped out
            # OR when we can make lethal regardless of Erode
            opp_erodes_available = opp_untapped   # each untapped land = potential Erode
            safe_to_execute = (
                opp_erodes_available == 0           # truly tapped out
                or (opp_erodes_available == 1 and have_counter)  # 1 Erode, we have counter
            )

            eligible_with_plot = (
                [c for c in gs.zones.battlefield
                 if not c.is_land() and c.has(Tag.CREATURE)
                 and not getattr(c, 'summoning_sickness', False)
                 and not getattr(c, 'tapped', False)]
                + castable_from_exile  # would enter with haste
            )
            lethal_with_plot = self._lethal_this_turn(gs, opponent, eligible_with_plot)

            if safe_to_execute or lethal_with_plot:
                for card in castable_from_exile:
                    plotted.remove(card)
                    # Cast for free — enter battlefield with haste
                    card.summoning_sickness = False
                    card.tapped = False
                    if hasattr(card, 'turn_entered'):
                        card.turn_entered = gs.turn
                    gs.zones.battlefield.append(card)
                    gs.spells_cast_this_turn += 1
                    gs._log(f"  [plot-execute] cast {card.name} from exile for free "
                            f"(opp has {opp_untapped} untapped, turn {gs.turn})")

                # ── Chain noncreature spells for MAXIMUM pump ─────────────
                # Slickshot gets +2/+0 per noncreature spell — dump everything.
                # Order: cheap cantrips first (draw fuel), then burn (removal + pump)
                changed = True
                while changed:
                    changed = False
                    for card in sorted(list(gs.zones.hand),
                                       key=lambda c: getattr(c, 'cmc', 0)):
                        if not card.is_land() and not card.has(Tag.CREATURE):
                            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                                gs.cast_spell(card)
                                changed = True
                                break
                return  # done with this turn's main phase

        # ── Lethal check: can we kill without the Plot ────────────────────
        eligible_now = [c for c in gs.zones.battlefield
                        if not c.is_land() and c.has(Tag.CREATURE)
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        lethal = self._lethal_this_turn(gs, opponent, eligible_now)

        # ── Step 2: Plot vs Sandbag vs Cast normally ──────────────────────
        slickshotS_in_hand = [c for c in gs.zones.hand if c.name in KEY_THREATS]
        have_bait = any(c for c in gs.zones.hand
                        if not c.is_land()
                        and c.name not in KEY_THREATS
                        and (not c.has(Tag.CREATURE) or getattr(c, 'cmc', 0) <= 1))

        wants_to_hold = (
            gs.turn >= 3
            and opp_has_removal            # archetype model says they run removal
            and opp_untapped >= 1          # even 1 untapped = potential Erode ({W}=1)
            and not lethal
            and not have_counter
            and have_bait
        )

        if wants_to_hold and slickshotS_in_hand:
            # Try to PLOT rather than just sandbag — costs {1}{R} but guarantees
            # the bomb next turn as a free sorcery-speed cast
            for card in list(slickshotS_in_hand):
                if gs.mana_pool.can_cast(self.PLOT_COST, self.PLOT_CMC):
                    gs.mana_pool.pay(self.PLOT_COST, self.PLOT_CMC)
                    gs.zones.hand.remove(card)
                    card.plotted_on_turn = gs.turn
                    self._plotted(gs).append(card)
                    gs.spells_cast_this_turn += 1   # Plot is a spell action
                    gs._log(f"  [plot] {card.name} plotted for free cast next turn "
                            f"(opp has {opp_untapped} untapped)")

            # Cast remaining hand as bait (draws out removal, pumps prowess)
            held_after_plot = {c.name for c in self._plotted(gs)}
            bait_hand = [c for c in list(gs.zones.hand) if c.name not in held_after_plot]
            # Temporarily remove already-plotted cards from consideration
            all_held = [c for c in list(gs.zones.hand) if c.name in KEY_THREATS]
            for c in all_held:
                gs.zones.hand.remove(c)
            IzzetProwessAPL.main_phase(self, gs)
            for c in all_held:
                if c not in self._plotted(gs):  # only restore if not plotted
                    gs.zones.hand.append(c)

        elif wants_to_hold and not slickshotS_in_hand:
            # Nothing to plot but still want to sandbag (Colorstorm etc.)
            held = [c for c in list(gs.zones.hand) if c.name in KEY_THREATS]
            for c in held:
                gs.zones.hand.remove(c)
            IzzetProwessAPL.main_phase(self, gs)
            for c in held:
                gs.zones.hand.append(c)
            gs._log(f"  [sandbag] holding {[c.name for c in held]} "
                    f"(opp {opp_untapped} untapped, no Plot mana)")
        else:
            IzzetProwessAPL.main_phase(self, gs)

    def respond_to_spell(self, gs: GameState, opponent, spell):
        """
        Counter key Landfall threats. Use Three Steps Ahead or Spell Pierce.
        Priority targets (any CMC): Badgermole Cub, Harmonizer, Earthbender Ascension.
        Generic spells: only counter if CMC >= 3.
        """
        if spell:
            spell_name = getattr(spell, 'name', '')
            spell_cmc  = getattr(spell, 'cmc', 0)
            is_priority = spell_name in self._COUNTER_PRIORITY
            if not is_priority and spell_cmc < 3:
                return None

        for card in gs.zones.hand:
            if card.name in self.COUNTER_CARDS:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    return card
        return None

    def end_step_actions(self, gs: GameState, opponent: GameState):
        """
        At end of opponent's turn, flash in Eddymurk Crab if:
        1. We have enough spells in GY to cast it cheaply
        2. Opponent has a high-value creature to bounce (especially Badgermole Cub)
        """
        # Check Eddymurk Crab in hand
        crab = next((c for c in gs.zones.hand if c.name == "Eddymurk Crab"), None)
        if not crab:
            return

        # Calculate discount: {1} less per instant/sorcery in graveyard
        from data.card import Tag
        spells_in_gy = sum(1 for c in gs.zones.graveyard
                           if c.has(Tag.INSTANT) or c.has(Tag.SORCERY))
        discount = min(spells_in_gy, 5)  # caps at 5 (UU minimum)
        effective_cmc = max(2, crab.cmc - discount)

        if gs.mana_pool.total() < effective_cmc:
            return   # can't afford it

        # Only flash in if opponent has a good ETB-bounce target
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return

        # Prioritize bouncing Badgermole Cub (loses all its counters!)
        from apl.selesnya_landfall_standard_match import BADGERMOLE, HARMONIZER
        valuable_targets = [c for c in opp_creatures
                            if c.name in {BADGERMOLE, HARMONIZER}]
        if not valuable_targets:
            # Generic case: bounce anything big enough
            biggest = max(opp_creatures, key=lambda c: safe_toughness(c))
            if safe_toughness(biggest) < 3:
                return   # not worth the crab

        # Cast Eddymurk Crab at flash speed (approximate cost as generic mana)
        gs.tap_lands()
        # Build a generic mana cost string matching the effective cmc
        generic_cost = "U" * min(effective_cmc, 2)  # pay UU minimum
        if not gs.mana_pool.can_cast(generic_cost, effective_cmc):
            return
        gs.mana_pool.pay(generic_cost, effective_cmc)

        bounce_target = (valuable_targets or opp_creatures)[0]
        # Most valuable: Badgermole Cub (wipes accumulated counters)
        if any(c.name == BADGERMOLE for c in valuable_targets):
            bounce_target = next(c for c in valuable_targets if c.name == BADGERMOLE)

        opponent.zones.battlefield.remove(bounce_target)
        opponent.zones.hand.append(bounce_target)   # back to hand, counters lost
        gs.zones.hand.remove(crab)
        gs.zones.battlefield.append(crab)
        gs._log(f"  [end step] Eddymurk Crab (flash): bounce {bounce_target.name} "
                f"to hand (loses all counters)")

    def combat_trick(self, gs: GameState, opponent: GameState,
                     attackers: list, blocker_assignments: dict):
        """Bounce a blocker with Boomerang Basics to push Slickshot damage through."""
        from engine.match_state import safe_power
        assign_map = {id(k): v for k, v in blocker_assignments.items()} \
                     if blocker_assignments else {}

        for atk in attackers:
            blks = assign_map.get(id(atk), [])
            if not blks:
                continue
            # Bounce a blocker to let our attacker through (especially Slickshot)
            atk_name = getattr(atk, 'name', '')
            if atk_name == "Slickshot Show-Off" or safe_power(atk) >= 3:
                for card in list(gs.zones.hand):
                    if card.name == "Boomerang Basics":
                        if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                            gs.mana_pool.pay(card.mana_cost, card.cmc)
                            gs.zones.hand.remove(card)
                            gs.zones.graveyard.append(card)
                            blocker = blks[0]
                            if blocker in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(blocker)
                                opponent.zones.hand.append(blocker)
                            assign_map[id(atk)] = []
                            gs._log(f"  Combat trick: Boomerang Basics bounces "
                                    f"{blocker.name}, {atk.name} hits face")
                            return
