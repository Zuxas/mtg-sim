"""
apl/aware_match_apl.py -- AwareMatchAPL: timing-aware base for Standard match APLs

Extends MatchAPL with:
  - Pre-combat priority window (kill ninjutsu enablers, blink targets)
  - Post-attackers priority window (Kaito prevention)
  - Trigger ordering (stack ETBs in value-maximizing order)
  - Trade intelligence (CMC comparison, beatdown vs control role)
  - Bluff mana (hold up counter mana to represent interaction)
  - Mana-awareness attack decisions (don't walk into open mana)

Usage: subclass AwareMatchAPL instead of MatchAPL for Standard decks.
The engine calls the new hooks via run_match if available (hasattr checks).
"""

from __future__ import annotations
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.match_apl import MatchAPL


# ---------------------------------------------------------------------------
# Opponent threat model registry
# Tells our APL what interaction the opponent archetype likely holds.
# "density" = how many interaction spells are in a typical 75.
# ---------------------------------------------------------------------------
OPP_THREAT_MODEL: dict[str, dict] = {
    # Instant removal density, counter density, pump density, min mana to represent
    # Sources: guide database reads 2026-05-04 (RIW Hobbies, Decktionary, TCGPlayer, metafy.gg)
    "izzetprowessstandard": {"removal": 4, "counters": 4, "pump": 2, "rep_mana": 1},
    # MonoGreen: Snakeskin Veil {G} is the main pump/protection
    "monogreenlandfall":    {"removal": 0, "counters": 0, "pump": 2, "rep_mana": 1},
    "selesnyalandfall":     {"removal": 2, "counters": 0, "pump": 2, "rep_mana": 1},  # Erode={W}, Snakeskin Veil={G}
    "selesnyaouroboroid":   {"removal": 1, "counters": 0, "pump": 2, "rep_mana": 1},
    "golgarimidrange":      {"removal": 6, "counters": 0, "pump": 0, "rep_mana": 2},
    "golgaricontrol":       {"removal": 6, "counters": 0, "pump": 0, "rep_mana": 2},
    "golgarikona":          {"removal": 4, "counters": 0, "pump": 0, "rep_mana": 2},
    # Spellementals: control/tempo. No pump. Heavy counters: Annul, Spell Pierce, Spell Snare, Disdainful Stroke, Bounce Off.
    # Holds 2 mana for instant-speed counters/sweepers. Sunderflock = big board reset.
    "izzetspellementals":   {"removal": 3, "counters": 6, "pump": 0, "rep_mana": 2},
    # Izzet Lessons: 3 removal (Combustion Technique, Firebending Lesson, Iroh's Demo),
    # 6 counters (Three Steps Ahead, It'll Quench Ya, Spell Pierce, Negate, Flashfreeze, Spell Snare)
    "izzetlessons":         {"removal": 3, "counters": 6, "pump": 0, "rep_mana": 2},
    "azoriusmomo":          {"removal": 4, "counters": 2, "pump": 0, "rep_mana": 2},
    "azoriustempo":         {"removal": 2, "counters": 4, "pump": 0, "rep_mana": 1},
    "azoriusblink":         {"removal": 2, "counters": 0, "pump": 0, "rep_mana": 2},
    "jeskaicontrol":        {"removal": 4, "counters": 4, "pump": 0, "rep_mana": 2},
    # Dimir Midrange: Requiting Hex {1B} instant removal + Spell Snare {U} counter
    "dimirmidrangestd":     {"removal": 6, "counters": 2, "pump": 0, "rep_mana": 2},
    "dimirexcruciator":     {"removal": 4, "counters": 2, "pump": 0, "rep_mana": 2},
    "izzetmaestro":         {"removal": 3, "counters": 3, "pump": 2, "rep_mana": 1},
    "sultaicontrol":        {"removal": 6, "counters": 2, "pump": 0, "rep_mana": 2},
    # Low-interaction archetypes
    "monoredaggro":         {"removal": 4, "counters": 0, "pump": 2, "rep_mana": 1},
    "monogreenaggro":       {"removal": 0, "counters": 0, "pump": 3, "rep_mana": 1},
    "borosaggrostandard":   {"removal": 4, "counters": 0, "pump": 0, "rep_mana": 1},
    "borosdragons":         {"removal": 2, "counters": 2, "pump": 0, "rep_mana": 2},
    # Discard aggro: taps out every turn; Bloodghast/Flamewake recurr; no instant interaction
    "mardudiscard":         {"removal": 0, "counters": 0, "pump": 0, "rep_mana": 0},
    "rakdosdiscard":        {"removal": 0, "counters": 0, "pump": 0, "rep_mana": 0},
    "borosdiscard":         {"removal": 0, "counters": 0, "pump": 0, "rep_mana": 0},
    "simiccub":             {"removal": 0, "counters": 2, "pump": 3, "rep_mana": 1},
    "selesnyarhythm":       {"removal": 1, "counters": 0, "pump": 2, "rep_mana": 1},
    # PT Lorwyn Eclipsed dominant archetypes (2026-05-04) -- from actual decklists
    # Simic Rhythm: no main-deck removal (Seam Rip in SB only); 1 Bounce Off SB
    "simicrhythm":          {"removal": 0, "counters": 0, "pump": 0, "rep_mana": 0},
    # Bant Rhythm: 3x Seam Rip {W} MAIN DECK -- enchantment that exiles MV<=2 permanents
    # rep_mana=1: needs {W} to activate Seam Rip (and Abandoned Air Temple pump {3W})
    "bantrhythm":           {"removal": 3, "counters": 0, "pump": 0, "rep_mana": 1},
    "fivecolorrhythm":      {"removal": 1, "counters": 0, "pump": 0, "rep_mana": 1},
    # Sultai Reanimator: Disdainful Stroke SB, Deceit main (bounce); holds no mana (taps out to combo)
    "sultaireanimator":     {"removal": 1, "counters": 1, "pump": 0, "rep_mana": 0},
    # New archetypes added 2026-05-04
    # Temur Lute: Three Steps Ahead + Negate + Annul + Flashfreeze + Spell Pierce; holds 2 mana
    "temurlute":            {"removal": 2, "counters": 5, "pump": 0, "rep_mana": 2},
    "temurlutestd":         {"removal": 2, "counters": 5, "pump": 0, "rep_mana": 2},
    # Bant Airbending: taps out; no main-deck removal; Disdainful Stroke only in SB
    "bantairbending":       {"removal": 0, "counters": 1, "pump": 0, "rep_mana": 0},
    # bantrhythm: see PT Lorwyn Eclipsed section above (3x Seam Rip main deck)
    # Sultai Control: Deceit as primary interaction ({2UB}); holds 4 mana when Deceit in hand
    "sultaicontrol":        {"removal": 1, "counters": 0, "pump": 0, "rep_mana": 4},
    # Jeskai Oculus (current Standard): Torch the Tower {R} + Spell Pierce {U}; holds 1 mana
    "jeskaioculus":         {"removal": 4, "counters": 2, "pump": 0, "rep_mana": 1},
    # Temur Omniscience / Bant Omniscience / Simic Omni: all combo, hold counters
    "temuromniscience":     {"removal": 0, "counters": 4, "pump": 0, "rep_mana": 2},
    "bantomniscience":      {"removal": 0, "counters": 4, "pump": 0, "rep_mana": 2},
    "simicomniscience":     {"removal": 0, "counters": 4, "pump": 0, "rep_mana": 2},
    # Four Color variants
    "fourcolorcontrol":     {"removal": 4, "counters": 4, "pump": 0, "rep_mana": 2},
    "fourcolorelemental":   {"removal": 2, "counters": 4, "pump": 0, "rep_mana": 2},
}

# Creatures whose combat damage or attack trigger enables a powerful follow-up.
# Kill these BEFORE combat (pre-combat priority window) if possible.
# Key: creature name  Value: why it matters (doc only)
DANGEROUS_ATTACKERS = {
    "Kaito, Bane of Nightmares",   # ninjutsu enabler if unblocked
    "Spyglass Siren",              # ninjutsu enabler (evasive)
    "Floodpits Drowner",           # ninjutsu enabler
    "Dream Beavers",               # ninjutsu enabler
    "Kaito Shizuki",               # ninjutsu enabler
    "Gran-Gran",                   # loot on attack/unblocked = Monument to Endurance trigger; primary kill target vs Izzet Lessons
    "Icetill Explorer",            # chains fetch land landfall triggers (4 per turn); remove before engine fires
    "Traveling Chocobo",           # landfall doubler; attack trigger gives +1/+1 to all creatures per land
}

# Permanents with valuable ETBs that should be killed NOW (not after they bounce/blink).
# Use exile-quality removal on these when available.
BLINK_BAIT = {
    "Ouroboroid",             # ETB: self-mill + graveyard payoff
    "Badgermole Cub",         # ETB: landfall value
    "Evendo, Waking Haven",   # ETB: token maker
    "Gene Pollinator",        # ETB: draw
    "Quantum Riddler",        # ETB: scry+draw
    "Kona, Rescue Beastie",   # ETB: recur a creature
    "Mightform Harmonizer",   # ETB/tap: combo kill piece (Harmonizer + Leatherhead = instant lethal)
    "Earthbender Ascension",  # continuous trample enabler; remove before landfall chains grow
    "Proft's Eidetic Memory", # Jeskai Oculus draw engine: whenever creature with counter attacks = draw
    "Brightglass Gearhulk",   # {3UU} Dimir mirror-breaker; ETB searches for removal; must exile
    "Doc Aurlock, Grizzled Genius", # Bant Airbending: reduces Avatar costs; remove before Appa/Aang land
    "Bristly Bill, Spine Sower",    # Selesnya engine "glue"; removes it and their counter synergy stalls
    "Felidar Retreat",              # Selesnya/Bant post-board token engine; generates tokens on each land
    "Traveling Chocobo",            # Selesnya landfall doubler alongside Icetill; exile before engine fires
    "Craterhoof Behemoth",          # ETB: gives ALL creatures +X/+X trample; instant lethal with 5+ creatures
    "Mockingbird",                  # Copies another creature you control; exile to deny double ETB value
    "Bringer of the Last Gift",     # Sultai Reanimator target; MUST exile or they recur it infinitely
    "Superior Spider-Man",          # Enters as copy of Bringer = recursive ETB loop; exile both
    # Nature's Rhythm is a SORCERY ({X}{G}{G}) -- puts creature directly to battlefield; NOT a permanent
    # DO NOT add to BLINK_BAIT (resolves immediately, can't be exiled on stack without a counter)
    "Formidable Speaker",           # Sultai Reanimator: ETB discard->tutor creature; {1}{T}: untap permanent
}


class AwareMatchAPL(MatchAPL):
    """
    Timing-aware MatchAPL base class.

    Subclasses declare:
      COUNTER_COST  : int  — mana to hold up as bluff (0 = tap out freely)
      COUNTER_CARDS : set  — actual counterspell names in this deck
      BLINK_TARGETS : set  — their permanents we want exiled (not bounced)

    The engine calls pre_combat_instant() and post_attackers_instant()
    via hasattr checks if they exist on the APL. AwareMatchAPL defines
    both so any subclass gets them for free.
    """

    COUNTER_COST:  int = 0       # 0 = no bluffing (aggro); 2 = hold Spell Pierce mana
    COUNTER_CARDS: set = set()   # names of actual counters in this deck
    BLINK_TARGETS: set = set()   # override per deck if needed

    # R1 priority-stack opt-in (design 1.5). DEFAULT OFF on the base class so the
    # 37 non-control Standard decks return to the bit-identical legacy gate-OFF
    # path. R1 is scoped to a real control subclass that OPTS IN by setting
    # WANTS_PRIORITY_STACK = True (see apl/uw_control_modern_match.py). The
    # priority_action implementation stays on the base: it is inert when the gate
    # is off (engine._priority_stack_enabled returns False, so run_priority_stack
    # is never entered) and is inherited for free by the opted-in subclass.
    # Payment happens from real untapped/reserved mana in
    # engine.priority_stack._pay_for_counter (via tap_lands honoring mana_reserve).
    WANTS_PRIORITY_STACK = False

    # ---------------------------------------------------------------------------
    # Mana awareness helpers
    # ---------------------------------------------------------------------------

    def _opp_model(self) -> dict:
        key = getattr(self, "_opp_key", "")
        return OPP_THREAT_MODEL.get(key, {"removal": 2, "counters": 1, "pump": 1, "rep_mana": 2})

    def _opp_interaction_density(self) -> int:
        m = self._opp_model()
        return m["removal"] + m["counters"] + m["pump"]

    def _opp_likely_has_instant(self) -> bool:
        """True when opponent plausibly has an instant they can cast."""
        m = self._opp_model()
        return (self._opp_untapped_lands() >= m["rep_mana"]
                and self._opp_hand_size() >= 1
                and self._opp_interaction_density() >= 3)

    def _opp_likely_has_pump(self) -> bool:
        m = self._opp_model()
        return (self._opp_untapped_lands() >= 1
                and self._opp_hand_size() >= 1
                and m["pump"] >= 2)

    def _opp_likely_has_counter(self) -> bool:
        m = self._opp_model()
        return (self._opp_untapped_lands() >= m["rep_mana"]
                and self._opp_hand_size() >= 1
                and m["counters"] >= 2)

    # ---------------------------------------------------------------------------
    # Trade intelligence
    # ---------------------------------------------------------------------------

    def _trade_value(self, mine: Card, theirs: Card) -> float:
        """
        Positive = trade favors us. Negative = trade hurts us.
        Based on CMC comparison (proxy for card value) plus role.
        """
        my_cmc   = getattr(mine,   'cmc', 0)
        opp_cmc  = getattr(theirs, 'cmc', 0)
        base     = opp_cmc - my_cmc   # positive = their creature costs more

        # Penalty if we're trading into a BLINK_BAIT — they'll just replay it
        if theirs.name in (BLINK_BAIT | self.BLINK_TARGETS):
            base -= 2   # trade becomes worse: they get the ETB again

        # Bonus if we're the control and removing a threat is good
        if self.ARCHETYPE == "control":
            base += 1

        # Penalty if we're the beatdown and losing an attacker slows us down
        my_dmg  = getattr(self, "_match_dmg", 0)
        opp_dmg = self._opp_damage_dealt()
        if my_dmg > opp_dmg:       # we're winning the race
            base -= 1.5            # don't slow ourselves down

        return base

    def _i_am_beatdown(self) -> bool:
        """True if we're the faster / more aggressive deck."""
        my_dmg  = getattr(self, "_match_dmg", 0)
        opp_dmg = self._opp_damage_dealt()
        # Also check if opponent has more creatures on board (we're behind)
        opp     = getattr(self, "_opp_gs", None)
        if opp is None:
            return self.ARCHETYPE in ("aggro", "tempo")
        opp_creatures = sum(1 for c in opp.zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE))
        my_creatures  = sum(1 for c in (getattr(self, "_my_gs", None) or opp).zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE))
        return my_dmg >= opp_dmg and my_creatures >= opp_creatures

    # ---------------------------------------------------------------------------
    # Pre-combat priority window (NEW ENGINE HOOK)
    # Called by match_engine BEFORE active player declares attackers.
    # The DEFENDING player uses this window.
    # ---------------------------------------------------------------------------

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        """
        Defender's priority window during Begin Combat step.
        Use this to:
          - Kill a creature before it can attack (ninjutsu prevention)
          - Kill a permanent before it can be blinked in response to removal
          - Use exile removal on BLINK_BAIT before opponent can Into the Flood Maw
        """
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return

        # Priority 1: Kill ninjutsu enablers before they attack
        for creature in opp_creatures:
            if creature.name in DANGEROUS_ATTACKERS:
                if self._kill_with_removal(gs, opponent, creature, prefer_exile=True):
                    gs._log(f"  [pre-combat] killed ninjutsu enabler {creature.name}")
                    return

        # Priority 2: Kill BLINK_BAIT with exile removal
        # (regular removal gets bounced by Into the Flood Maw)
        blink_targets = [c for c in opp_creatures
                         if c.name in (BLINK_BAIT | self.BLINK_TARGETS)]
        if blink_targets:
            target = max(blink_targets, key=lambda c: getattr(c, 'cmc', 0))
            if self._kill_with_removal(gs, opponent, target, prefer_exile=True):
                gs._log(f"  [pre-combat] exiled {target.name} before blink window")
                return

    # ---------------------------------------------------------------------------
    # Post-attackers priority window (NEW ENGINE HOOK)
    # Called by match_engine AFTER active player declares attackers,
    # BEFORE blockers are declared.
    # The DEFENDING player uses this window.
    # ---------------------------------------------------------------------------

    def post_attackers_instant(self, gs: GameState, opponent: GameState,
                                attackers: list[Card]):
        """
        After seeing who's attacking, kill unblocked evasion creatures
        before they can ninjutsu Kaito (or trigger other attack effects).
        Also use instant removal on high-value attackers if profitable.
        """
        # Find attackers with no natural blocker (we can't profitably block)
        my_blockers = [c for c in gs.zones.battlefield
                       if not c.is_land() and c.has(Tag.CREATURE)
                       and not getattr(c, 'summoning_sickness', False)]

        for atk in attackers:
            # Check if this attacker is a ninjutsu enabler (must die before damage)
            if atk.name in DANGEROUS_ATTACKERS:
                if self._kill_with_removal(gs, opponent, atk, prefer_exile=False):
                    gs._log(f"  [post-attackers] killed {atk.name} before ninjutsu")
                    return

            # Check if we can block it at all
            can_block = any(safe_power(b) >= safe_toughness(atk)
                            or safe_power(atk) <= safe_toughness(b)
                            for b in my_blockers)
            if not can_block:
                # Unblockable — use removal if the attacker is high value
                atk_cmc = getattr(atk, 'cmc', 0)
                if atk_cmc >= 3:
                    if self._kill_with_removal(gs, opponent, atk, prefer_exile=False):
                        gs._log(f"  [post-attackers] removed unblockable {atk.name}")
                        return

    # ---------------------------------------------------------------------------
    # Core removal dispatcher
    # ---------------------------------------------------------------------------

    def _kill_with_removal(self, gs: GameState, opponent: GameState,
                            target: Card, prefer_exile: bool = False) -> bool:
        """
        Try to kill `target` using a card from hand.
        prefer_exile=True: try exile removal first (counters Into the Flood Maw response).
        Returns True if removal was cast.
        """
        from engine.stack import classify_card, InteractionType

        hand = list(gs.zones.hand)
        # Sort: prefer exile if requested
        if prefer_exile:
            hand = sorted(hand, key=lambda c: 0 if c.name in self.MATCH_EXILE else 1)

        for card in hand:
            spec = self.MATCH_REMOVAL.get(card.name)
            if not spec:
                continue
            if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                continue

            # Ward check: if target has ward, the spell costs extra mana.
            # Ward cost is encoded as "ward N" in oracle text.
            ward_cost = 0
            oracle = (getattr(target, 'oracle_text', '') or '').lower()
            import re as _re
            m = _re.search(r'ward \{(\d+)\}', oracle)
            if m:
                ward_cost = int(m.group(1))
            if ward_cost > 0:
                # Check if we can afford the extra ward tax
                extra_mana_needed = card.cmc + ward_cost
                if gs.mana_pool.total() < extra_mana_needed:
                    continue  # can't pay ward — skip this removal

            _cost, max_tgh = spec
            if max_tgh is not None and safe_toughness(target) > max_tgh:
                continue

            # Pay and kill
            gs.mana_pool.pay(card.mana_cost, card.cmc)
            gs.zones.hand.remove(card)
            gs.zones.graveyard.append(card)
            gs.noncreature_spells_this_turn += 1

            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                if card.name in self.MATCH_EXILE:
                    opponent.zones.exile.append(target)
                elif card.name in getattr(self, 'MATCH_BOUNCE', set()):
                    # Bounce: return to owner's hand (temporary, not permanent removal)
                    opponent.zones.hand.append(target)
                else:
                    opponent.zones.graveyard.append(target)

            # Some removal grants the opponent a basic land on resolution.
            # Erode: "Its controller may search library for a basic land."
            if card.name in getattr(self, 'MATCH_GRANTS_LAND', set()):
                basics = [c for c in opponent.zones.library if c.is_land()]
                if basics:
                    land = basics[0]
                    opponent.zones.library.remove(land)
                    opponent.zones.battlefield.append(land)
                    land.turn_entered = getattr(opponent, 'turn', 1)
                    gs._log(f"  {card.name}: opponent fetches {land.name}")

            gs._log(f"  {card.name} -> kills {target.name}")
            return True

        return False

    # ---------------------------------------------------------------------------
    # Overridden: declare_attackers with trade intelligence
    # ---------------------------------------------------------------------------

    def _lethal_this_turn(self, gs: GameState, opponent: GameState,
                           candidates: list) -> bool:
        """
        True if attacking with all candidates can kill the opponent this turn.
        Accounts for:
          - Each creature's current power
          - Prowess pump: +1/+0 per noncreature spell in hand (for prowess creatures)
          - Trample: excess damage goes through even with blockers
          - Flying: unblockable if opponent has no flying/reach
        Does NOT account for combat tricks from the opponent.
        """
        from engine.keywords import KWTag
        opp_life = opponent.life

        # Count noncreature spells in hand for prowess pump
        pump_spells = sum(1 for c in gs.zones.hand
                          if not c.is_land() and not c.has(Tag.CREATURE))

        opp_blockers = [c for c in opponent.zones.battlefield
                        if not c.is_land() and c.has(Tag.CREATURE)
                        and not getattr(c, 'tapped', False)]
        opp_has_flyer = any(KWTag.FLYING in b.tags or KWTag.REACH in b.tags
                            for b in opp_blockers)
        total_opp_block_power = sum(safe_power(b) for b in opp_blockers)

        total_damage = 0
        for atk in candidates:
            base_p = safe_power(atk)
            # Prowess creatures get pumped by spells cast this turn + spells in hand
            if KWTag.PROWESS in atk.tags:
                base_p += pump_spells + getattr(gs, 'noncreature_spells_this_turn', 0)
            # Flying: can't be blocked unless opp has flyers
            if KWTag.FLYING in atk.tags and not opp_has_flyer:
                total_damage += base_p  # unblockable
            elif KWTag.TRAMPLE in atk.tags and opp_blockers:
                # Trample: assign minimum to blockers, rest goes through
                total_damage += max(0, base_p - total_opp_block_power)
                total_opp_block_power = max(0, total_opp_block_power - base_p)
            elif not opp_blockers:
                total_damage += base_p
            else:
                # Ground attacker vs ground blockers — some damage may be absorbed
                # Conservative: assume best blocker soaks all damage
                best_blk = max(opp_blockers, key=lambda b: safe_toughness(b))
                if base_p > safe_toughness(best_blk):
                    total_damage += base_p - safe_toughness(best_blk)

        # Add burn spells we can fire pre-combat or post-combat
        # (defensive getattr -- APLs that don't define MATCH_BOUNCE/MATCH_WIPES
        # crashed here pre-2026-05-10; see line 355 for the existing pattern)
        _bounce = getattr(self, 'MATCH_BOUNCE', set())
        _wipes  = getattr(self, 'MATCH_WIPES',  set())
        for card in gs.zones.hand:
            spec = self.MATCH_REMOVAL.get(card.name)
            if spec and card.name not in _bounce and \
               card.name not in _wipes:
                _, max_tgh = spec
                if max_tgh is None or max_tgh >= 20:  # face burn
                    pass  # could add, but conservative

        return total_damage >= opp_life

    def declare_attackers(self, gs: GameState, opponent: GameState) -> list[Card]:
        attackers = super().declare_attackers(gs, opponent)
        if not attackers:
            return attackers

        # ── Lethal check: if we can kill them this turn, send everything ──
        # Get all eligible creatures, not just the filtered set
        from engine.keywords import KWTag
        all_eligible = [c for c in gs.zones.battlefield
                        if not c.is_land() and c.has(Tag.CREATURE)
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        if all_eligible and self._lethal_this_turn(gs, opponent, all_eligible):
            gs._log(f"  [lethal] attacking with all {len(all_eligible)} creatures "
                    f"— calculated lethal vs {opponent.life} life")
            return all_eligible

        opp_blockers = [c for c in opponent.zones.battlefield
                        if not c.is_land() and not getattr(c, 'tapped', False)]

        filtered = []
        for atk in attackers:
            # Find the best blocker for this attacker
            best_blk = None
            for blk in opp_blockers:
                if safe_power(blk) > 0:
                    if best_blk is None or safe_power(blk) > safe_power(best_blk):
                        best_blk = blk

            if best_blk is None:
                # No blocker — free damage, always go
                filtered.append(atk)
                continue

            atk_tough = safe_toughness(atk)
            blk_power = safe_power(best_blk)

            if blk_power >= atk_tough:
                # Our attacker dies (trade or dies alone)
                blk_tough  = safe_toughness(best_blk)
                atk_power  = safe_power(atk)
                if atk_power >= blk_tough:
                    # True trade — evaluate value
                    value = self._trade_value(atk, best_blk)
                    if value >= 0:
                        filtered.append(atk)   # trade is neutral-or-favorable
                    # else: skip the trade (their creature is cheaper / blink-bait)
                else:
                    # Dies alone — skip unless we're desperate
                    my_dmg  = getattr(gs, "damage_dealt", 0)
                    opp_dmg = self._opp_damage_dealt()
                    if opp_dmg > my_dmg + 8:   # we're way behind, push anyway
                        filtered.append(atk)
            else:
                # Attacker survives or is unblockable-ish — go
                filtered.append(atk)

        # Don't walk a high-value threat into open counter mana
        if self._opp_likely_has_counter() and len(filtered) > 1:
            # Hold back the most expensive creature to protect from a counter
            by_cmc = sorted(filtered, key=lambda c: -getattr(c, 'cmc', 0))
            key_threat = by_cmc[0]
            # Only hold if the threat CMC >= counter threshold
            if getattr(key_threat, 'cmc', 0) >= 3:
                filtered = [c for c in filtered if c is not key_threat]

        return filtered

    # ---------------------------------------------------------------------------
    # Overridden: declare_blockers with pump awareness
    # ---------------------------------------------------------------------------

    def declare_blockers(self, gs: GameState, opponent: GameState,
                          attackers: list[Card]) -> dict:
        from engine.match_state import optimal_blocking

        my_creatures = [c for c in gs.zones.battlefield
                        if not c.is_land()
                        and not getattr(c, 'tapped', False)]

        # If opponent likely has pump, adjust effective toughness of attackers
        # by +2 when evaluating blocks (don't trade into a pump)
        if self._opp_likely_has_pump():
            # Use conservative blocking — only block if we survive even after +2
            conservative = []
            for atk in attackers:
                atk_power = safe_power(atk) + 2   # assume they pump
                for blk in my_creatures:
                    if safe_toughness(blk) > atk_power:
                        conservative.append((atk, blk))
                        break
            # Build assignment dict from conservative pairs.
            # Use id() keys — Card objects are not hashable.
            assignments = {}
            used = set()
            for atk, blk in conservative:
                if id(blk) not in used:
                    assignments[id(atk)] = [blk]
                    used.add(id(blk))
            return assignments

        # Default: optimal blocking
        opp_power = sum(safe_power(c) for c in opponent.zones.battlefield
                        if not c.is_land()
                        and not getattr(c, 'summoning_sickness', False))
        attacker_clock = max(1, -(-gs.life // opp_power)) if opp_power > 0 else 99
        return optimal_blocking(my_creatures, attackers, gs.life, attacker_clock)

    # ---------------------------------------------------------------------------
    # Bluff mana: hold up counter mana pre-combat
    # ---------------------------------------------------------------------------

    def reserve_mana(self, gs: GameState, opponent: GameState):
        """
        Called by the engine BEFORE tap_lands() each turn.
        Set gs.mana_reserve to the number of lands to leave untapped.
        Those lands stay physically untapped and _tap_for_response picks
        them up during the opponent's response windows.

        Default: hold back COUNTER_COST lands if we have counters in hand.
        Subclasses override for deck-specific logic (e.g. hold Plains for Erode).
        """
        if self.COUNTER_CARDS and self.COUNTER_COST > 0:
            # Only hold up if we actually have a counter available
            has_counter = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
            gs.mana_reserve = self.COUNTER_COST if has_counter else 0
        else:
            gs.mana_reserve = 0

    # ---------------------------------------------------------------------------
    # R1 priority-stack hook (design 1.5)
    # ---------------------------------------------------------------------------

    def priority_action(self, my_gs, opp_gs, stack):
        """Decide whether to counter the top object on `stack`.

        Returns (counter_card, target_uid) to cast a counter, or None to pass.

        The decision logic is LIFTED from engine.counter_resolver
        (COUNTER_VALIDITY / _spell_value / _PRIORITY_COUNTER_TARGETS) so the
        on-stack path uses the same threat assessment as the legacy synchronous
        window. Payment is NOT performed here -- engine.priority_stack pays from
        the responder's ACTUAL untapped/reserved mana (tap_lands honoring
        mana_reserve); this method only checks affordability before committing.

        ZERO random(): pure board-state + hand inspection.
        """
        items = getattr(stack, "items", None)
        if not items:
            return None

        # Per-run ownership reset. Each run_priority_stack builds a NEW Stack
        # object, so comparing the live reference with `is` detects a fresh run
        # without the id()-reuse hole (a freed Stack's address can be reused by
        # the next run; holding the reference keeps the address live).
        if getattr(self, "_r1_stack_ref", None) is not stack:
            self._r1_stack_ref = stack
            self._r1_owned = set()

        top = items[-1]
        # Never respond to an already-countered object (pointless) or to one of
        # MY OWN objects on the stack (don't counter my own counter). Ownership
        # is tracked by the card-object ids I have placed on this stack; within a
        # correctly-reset run every such card is alive, so the ids are stable.
        if getattr(top, "countered", False):
            return None
        if id(getattr(top, "card", None)) in self._r1_owned:
            return None

        spell = getattr(top, "card", None)
        if spell is None:
            return None

        counter = self._r1_choose_counter(my_gs, spell)
        if counter is None:
            return None

        # Record the card I am about to put on the stack so I don't later try to
        # counter it myself (priority_stack assigns it the next uid; we identify
        # it by object identity, which is stable for the life of the run).
        self._r1_owned.add(id(counter))
        return (counter, getattr(top, "uid", -1))

    def _r1_choose_counter(self, my_gs, spell):
        """Pick the cheapest legal, value-positive, affordable counter in hand.

        Mirrors engine.counter_resolver.try_counter_spell's selection: cheapest
        valid counter first (preserve flex), value gate (counter cost <= spell
        value unless the spell is a priority target), affordability against real
        untapped lands. Returns a card or None.
        """
        from engine.counter_resolver import (
            COUNTER_VALIDITY, _spell_value, _PRIORITY_COUNTER_TARGETS,
        )

        spell_val = _spell_value(spell)
        candidates = []
        for c in my_gs.zones.hand:
            entry = COUNTER_VALIDITY.get(c.name)
            if entry is None:
                continue
            validity_fn, base_cmc = entry
            if not validity_fn(spell):
                continue
            candidates.append((c, base_cmc))

        if not candidates:
            return None

        # Cheapest counter first (preserve flexible counters for bigger targets).
        candidates.sort(key=lambda x: x[1])

        for counter, counter_cmc in candidates:
            # Value gate: only over-spend on a flagged priority target.
            if (spell.name not in _PRIORITY_COUNTER_TARGETS
                    and counter_cmc > spell_val):
                continue
            if self._r1_can_afford(my_gs, counter):
                return counter
        return None

    @staticmethod
    def _r1_can_afford(my_gs, counter):
        """True if `counter` is plausibly castable from real untapped mana.

        Checks the current pool first; if that is short, estimates the mana that
        tap_lands would add from physically-untapped lands (reserved lands stay
        untapped into the opponent's turn -- design Seam D). This is a generic
        estimate matching the loose affordability used elsewhere in the engine;
        if it over-estimates, priority_stack._pay_for_counter fails the real pay
        and the window is simply treated as a pass."""
        pool = my_gs.mana_pool
        cmc = int(getattr(counter, "cmc", 0) or 0)
        if pool.can_cast(getattr(counter, "mana_cost", "") or "", cmc):
            return True
        untapped = [l for l in my_gs.zones.lands_on_battlefield()
                    if not getattr(l, "tapped", False)]
        return (pool.total() + len(untapped)) >= cmc

    def main_phase(self, gs: GameState):
        """
        Overridden main phase with bluff-mana awareness.
        If COUNTER_COST > 0, don't tap below that threshold pre-combat.

        If the subclass has no CURVE (i.e. it delegates casting to a goldfish APL
        via multi-inheritance), fall back to calling super().main_phase() so the
        goldfish APL's turn loop fires correctly, then just apply the bluff-mana
        post-processing (we can't easily intercept individual cast calls).
        """
        curve = getattr(self, 'CURVE', None)
        if not curve:
            # No explicit curve — let the goldfish APL handle casting.
            # We can't enforce per-card bluff-mana here, but the counter-mana
            # hold-up happens at the engine level via respond_to_spell.
            # Just delegate fully to the next main_phase in MRO.
            super_cls = None
            for cls in type(self).__mro__:
                if cls is AwareMatchAPL:
                    continue
                if 'main_phase' in cls.__dict__:
                    super_cls = cls
                    break
            if super_cls:
                super_cls.main_phase(self, gs)
            return

        lands = [c for c in gs.zones.hand if c.is_land()]
        if lands and not gs.land_played:
            gs.play_land(lands[0])
        gs.tap_lands()

        available = gs.mana_pool.total()
        reserve   = self.COUNTER_COST if self.COUNTER_CARDS else 0

        # Cast spells in curve order, keeping COUNTER_COST mana as bluff
        for name in curve:
            for card in list(gs.zones.hand):
                if card.name == name:
                    cost = getattr(card, 'cmc', 0)
                    if available - cost >= reserve:
                        if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                            gs.cast_spell(card)
                            available -= cost
                            break

        # Dump remaining mana only if we have no counter to represent
        if not self.COUNTER_CARDS:
            for card in sorted(list(gs.zones.hand),
                                key=lambda c: getattr(c, 'cmc', 0)):
                if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)

    # ---------------------------------------------------------------------------
    # Trigger ordering (NEW ENGINE HOOK)
    # Called when multiple triggers are about to go on the stack simultaneously.
    # ---------------------------------------------------------------------------

    def order_triggers(self, gs: GameState, triggers: list) -> list:
        """
        Order simultaneous triggers for maximum value.
        Default: highest-value triggers last (resolve last = evaluate first).

        Examples:
          Enduring Innocence + Novice Inspector ETBs:
            → Inspector trigger LAST so we draw a card AFTER the Treasure exists
              (the draw might find something we can cast with the Treasure mana)
          Badgermole Cub + land drop:
            → Land drop trigger resolves first so Cub counter is on before drawing
        """
        # Subclasses override this with deck-specific trigger ordering.
        # Default: no reordering (engine assigns in controller order).
        return triggers

    # ---------------------------------------------------------------------------
    # End step: flash threats, draw-go
    # ---------------------------------------------------------------------------

    def end_step_actions(self, gs: GameState, opponent: GameState):
        """
        At end of opponent's turn, deploy flash threats or use draw-go mana.
        Subclasses populate FLASH_THREATS with card names.
        """
        flash_cards = getattr(self, 'FLASH_THREATS', set())
        for card in list(gs.zones.hand):
            if card.name in flash_cards:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.tap_lands()
                    gs.cast_spell(card)
                    gs._log(f"  [end step] flash in {card.name}")
                    return

    # ---------------------------------------------------------------------------
    # Opponent-aware mulligan logic
    # ---------------------------------------------------------------------------

    # Ramp card names that enable T1-T2 acceleration (critical vs fast Rhythm decks)
    _RAMP_CARDS = {
        "Llanowar Elves", "Badgermole Cub", "Leyline Weaver",
        "Spider Manifestation", "Gene Pollinator", "Elvish Mystic",
        "Arbor Elf", "Arboreal Grazer",
    }
    # Rhythm archetypes that curve out so fast a T1 ramp is mandatory
    _RHYTHM_KEYS = {"simicrhythm", "bantrhythm", "fivecolorrhythm", "selesnyarhythm"}
    # Control archetypes where fishing for perfect hands backfires
    _CONTROL_KEYS = {
        "izzetlessons", "izzetspellementals", "azoriusmomo",
        "jeskaicontrol", "jeskaioculus", "azoriustempo",
    }

    def keep_vs_opp(self, hand: list, mulligans: int, on_play: bool,
                    opp_archetype: str) -> bool:
        """
        Opponent-aware keep decision. Adjusts thresholds based on matchup:
          - vs Rhythm (fast ramp): need T1 ramp or mull aggressively
          - vs combo (Sultai Reanimator): need clock OR disruption
          - vs control: any 2-lander is fine, don't fish for perfect hands
          - default: call the subclass keep() without opponent awareness
        """
        if len(hand) <= 4:
            return True   # always keep at 4 or fewer cards

        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False

        # vs Rhythm: mull without T1 ramp unless already mulliganed twice
        if opp_archetype in self._RHYTHM_KEYS:
            has_ramp = any(c.name in self._RAMP_CARDS for c in hand)
            return has_ramp or mulligans >= 2

        # vs Sultai Reanimator (combo): need fast clock OR disruption
        if opp_archetype == "sultaireanimator":
            has_clock = any(not c.is_land() and getattr(c, 'cmc', 99) <= 2
                            for c in hand)
            has_disruption = any(c.name in {"Duress", "Thoughtseize", "Negate",
                                            "Spell Pierce", "Annul"}
                                 for c in hand)
            return has_clock or has_disruption or mulligans >= 2

        # vs control: any functional 2-lander is fine (don't fish)
        if opp_archetype in self._CONTROL_KEYS:
            has_play = any(not c.is_land() for c in hand)
            return lands >= 2 and has_play

        # Default: generic land-count heuristic (DON'T re-dispatch to self.keep -
        # that creates an infinite loop because self.keep routes back to keep_vs_opp
        # via _opp_key. Bug fixed 2026-05-10 -- prior version recursed.)
        return self._keep_generic_fallback(hand)

    def _keep_generic_fallback(self, hand: list) -> bool:
        """Generic mulligan fallback: 2-5 lands, at least 1 nonland."""
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        return any(not c.is_land() for c in hand)

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        """
        Override: call keep_vs_opp when _opp_key is set (match_engine wires it).
        Falls back to generic land-count heuristic for goldfish/unknown opponents.
        Re-entrancy guard prevents the keep <-> keep_vs_opp ping-pong fixed 2026-05-10.
        """
        if getattr(self, "_in_keep_dispatch", False):
            return self._keep_generic_fallback(hand)
        opp_key = getattr(self, "_opp_key", "")
        if opp_key:
            self._in_keep_dispatch = True
            try:
                return self.keep_vs_opp(hand, mulligans, on_play, opp_key)
            finally:
                self._in_keep_dispatch = False
        # Generic fallback: 2-5 lands, at least 1 nonland
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        return any(not c.is_land() for c in hand)
