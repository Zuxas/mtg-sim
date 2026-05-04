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
    "mardudiscard":         {"removal": 2, "counters": 0, "pump": 0, "rep_mana": 1},
    "rakdosdiscard":        {"removal": 2, "counters": 0, "pump": 0, "rep_mana": 1},
    "simiccub":             {"removal": 0, "counters": 2, "pump": 3, "rep_mana": 1},
    "selesnyarhythm":       {"removal": 1, "counters": 0, "pump": 2, "rep_mana": 1},
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
        for card in gs.zones.hand:
            spec = self.MATCH_REMOVAL.get(card.name)
            if spec and card.name not in self.MATCH_BOUNCE and \
               card.name not in self.MATCH_WIPES:
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
