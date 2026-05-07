"""
apl/azorius_high_noon_standard_match.py -- Azorius High Noon (Prison-Tempo) match APL

Zevin Faust's UW prison-tempo deck. Top 8 PT SOS 2026, 9-1 / 21st PT Lorwyn Eclipsed.
The deck is NOT Bant Airbending. The deck is NOT Azorius Tempo. It is Azorius High Noon.

ENGINE (per Zevin's guide):
  Core 4 cards form a soft lock:
    1. High Noon         — both players limited to 1 spell per turn cycle
    2. Voice of Victory  — opponent can't cast spells DURING YOUR TURN
    3. Aven Interrupter  — exiles a spell off the stack (opp may recast +{2})
    4. Aang, Swift Savior— exiles a spell or creature off the stack/board

  With High Noon + Voice in play: opponent can cast exactly 1 spell per turn
  on THEIR main phase. Aven and Aang counter that single spell, leaving the
  opponent unable to act for entire turn cycles. Aang flips into a 5/5 reach
  trample finisher; High Noon's {4}{R}, sac: 5 damage gives reach to close.

SEQUENCING (Zevin's stated lines):
  T1: Untapped land (Starting Town T1-T3 / Hallowed Fountain / Floodfarm Verge)
  T2: High Noon (or Floodpits Drowner end-of-opponent's-turn)
  T3: Aven Interrupter (with Spell Snare backup vs blue decks)
  T4: Seam Rip / Get Lost holding up Aang or Aven
  T5+: Voice of Victory + High Noon active = full lock

POSTBOARD (vs blue/control):
  Cast High Noon LATE (T5+) so you don't lock yourself out before establishing.
  Cast Voice + pass with Aven/Aang up — opponent can't answer at instant speed.

MANA HOLDBACK:
  Almost always pass with 2 mana up (Aven + Aang both flash, Spell Snare {U}).
  The deck rarely tap-outs — its threats are reactive flash creatures.

MULLIGAN:
  Keep most 2-landers, mull most 5-landers.
  When bottoming, KEEP Starting Town (any-color for High Noon activation reach).
  Hands need: 1+ untapped W on T1, 2W+1U on T3 for Aven Interrupter.
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL


# ── Core lock pieces ────────────────────────────────────────────────────────
HIGH_NOON     = "High Noon"
VOICE         = "Voice of Victory"
AVEN          = "Aven Interrupter"
AANG          = "Aang, Swift Savior"

# ── Other creatures / threats ──────────────────────────────────────────────
FLOODPITS     = "Floodpits Drowner"
SKYCOACH      = "Skycoach Conductor"
RIDDLER       = "Quantum Riddler"
BEZA          = "Beza, the Bounding Spring"

# ── Removal / spells ────────────────────────────────────────────────────────
AVATARS_WRATH = "Avatar's Wrath"
GET_LOST      = "Get Lost"
SPELL_SNARE   = "Spell Snare"
SEAM_RIP      = "Seam Rip"
AIRBENDER_ASC = "Airbender Ascension"

# ── SB cards ────────────────────────────────────────────────────────────────
ANNUL         = "Annul"
DISDAINFUL    = "Disdainful Stroke"
FLASHFREEZE   = "Flashfreeze"
GHOST_VACUUM  = "Ghost Vacuum"
PETRIFIED_HAM = "Petrified Hamlet"
PYRRHIC       = "Pyrrhic Strike"
SPECTACULAR   = "Spectacular Tactics"

# Cards we hold up at instant speed (always reserve mana for these)
FLASH_THREATS = {AVEN, AANG, SKYCOACH, FLOODPITS, RIDDLER}

# Cards we want in play for the lock to be active
LOCK_PIECES = {HIGH_NOON, VOICE}


class AzoriusHighNoonMatchAPL(AwareMatchAPL):
    name = "Azorius High Noon"
    ARCHETYPE = "control"   # tempo-control hybrid; control archetype tag for SB matching

    # Mana to hold up for Spell Snare ({U}) + flash threat ({1}{W}{U} for Aang)
    COUNTER_COST  = 1
    COUNTER_CARDS = {SPELL_SNARE, ANNUL, DISDAINFUL, FLASHFREEZE}

    MATCH_REMOVAL = {
        GET_LOST:      ("1W",  None),  # destroy creature/enchantment/PW
        SEAM_RIP:      ("W",   2),     # exile cmc<=2 nonland permanent (SB)
        AVATARS_WRATH: ("2WW", None),  # mass airbend (sorcery, no flash)
        PYRRHIC:       ("2W",  4),     # destroy creature (SB)
    }
    MATCH_EXILE  = {SEAM_RIP, AANG, AVEN, AVATARS_WRATH}
    MATCH_BOUNCE = set()

    SB_PLANS = {
        # Per Zevin's guide. OUTs and INs match his sideboard mapping.
        "aggro": (
            # vs Cub / Landfall: airbend wipes + counters
            [AVATARS_WRATH, AVATARS_WRATH, DISDAINFUL, DISDAINFUL, SEAM_RIP],
            [VOICE, VOICE, VOICE, VOICE, "Ajani, Outland Chaperone"],
        ),
        "ramp": (
            # vs Landfall (Selesnya/Mono Green): same as aggro but no Voice cuts
            [AVATARS_WRATH, AVATARS_WRATH, DISDAINFUL, DISDAINFUL, "Tishana's Tidebinder"],
            [HIGH_NOON, HIGH_NOON, HIGH_NOON, HIGH_NOON, VOICE],
        ),
        "combo": (
            # vs Lessons: GY hate + extra exile + counters
            [GHOST_VACUUM, GHOST_VACUUM, "Soul-Guide Lantern", DISDAINFUL, ANNUL],
            [FLOODPITS, FLOODPITS, FLOODPITS, FLOODPITS, AVATARS_WRATH],
        ),
        "control": (
            # vs Control: drop Avatar/Seam Rip/Floodpits, bring counters + threats
            [DISDAINFUL, DISDAINFUL, ANNUL, ANNUL, "Glen Elendra Guardian"],
            [AVATARS_WRATH, AVATARS_WRATH, SEAM_RIP, SEAM_RIP, FLOODPITS],
        ),
        "tempo": (
            # vs Izzet Prowess / Spellementals
            [DISDAINFUL, FLASHFREEZE, FLASHFREEZE, ANNUL, SPECTACULAR],
            [AVATARS_WRATH, AVATARS_WRATH, SEAM_RIP, AIRBENDER_ASC, RIDDLER],
        ),
    }

    # ── Mulligan: 2-3 lands ideal, must have at least 1 W on 1, 1 U on 3 ───
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 4:
            return False
        # Need access to W on T1 (Floodfarm/Starting Town/Hallowed/basic Plains)
        # Need a lock piece OR a flash threat to enable the plan
        has_lock = any(c.name in LOCK_PIECES for c in hand)
        has_flash = any(c.name in FLASH_THREATS for c in hand)
        return (has_lock or has_flash) or mulligans >= 2

    def bottom(self, hand, n):
        # Per Zevin: NEVER bottom Starting Town if you can help it
        priority_keep = {"Starting Town", HIGH_NOON, AANG, AVEN, VOICE}
        bottoms = []
        # Bottom excess lands first (keep 3-4)
        lands = sorted([c for c in hand if c.is_land()],
                       key=lambda c: (c.name in priority_keep, c.name))
        if len(lands) > 4:
            bottoms.extend(lands[:len(lands) - 4])
        # Then high-CMC cards we can't cast yet
        spells = sorted([c for c in hand if not c.is_land() and c not in bottoms
                         and c.name not in priority_keep],
                        key=lambda c: -getattr(c, 'cmc', 0))
        bottoms.extend(spells)
        return bottoms[:n]

    # ── Mana holdback: almost always pass with mana up for flash interaction ──
    def reserve_mana(self, gs: GameState, opponent: GameState):
        # Reserve enough for Aang ({1}{W}{U} = 3) when on the play with threat in hand
        # Reserve {U} for Spell Snare when opponent has a 2-drop in hand
        has_aang  = any(c.name == AANG for c in gs.zones.hand)
        has_aven  = any(c.name == AVEN for c in gs.zones.hand)
        has_snare = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        has_floodpits = any(c.name == FLOODPITS for c in gs.zones.hand)

        # Postboard vs control: hold High Noon until T5+, reserve more mana
        is_control = (opponent is not None and self._opp_is_control(opponent))

        if has_aang and has_aven:
            gs.mana_reserve = 3   # both in hand: hold 3 to flash either
        elif has_aang or has_aven or has_floodpits:
            gs.mana_reserve = 2   # one flash threat: hold 2 minimum
        elif has_snare:
            gs.mana_reserve = 1
        elif is_control and gs.turn >= 4:
            gs.mana_reserve = 2   # always hold mana vs control
        else:
            gs.mana_reserve = 0

    def _opp_is_control(self, opponent: GameState) -> bool:
        if opponent is None:
            return False
        ctrl_cards = {"No More Lies", "Counterspell", "Lightning Helix",
                      "Wan Shi Tong, Librarian", "Day of Judgment"}
        all_cards = (list(opponent.zones.battlefield)
                     + list(getattr(opponent.zones, 'hand', []))
                     + list(getattr(opponent.zones, 'library', []))[:10])
        return sum(1 for c in all_cards if c.name in ctrl_cards) >= 2

    def _opp_is_creature_deck(self, opponent: GameState) -> bool:
        if opponent is None:
            return False
        opp_creatures = sum(1 for c in opponent.zones.battlefield
                            if c.has(Tag.CREATURE) and not c.is_land())
        return opp_creatures >= 2

    # ── Pre-combat: kill mana dorks / engines before they swing ──────────────
    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        if opponent is None:
            return
        opp_threats = [c for c in opponent.zones.battlefield
                       if c.has(Tag.CREATURE) and not c.is_land()
                       and not getattr(c, 'tapped', False)]
        if not opp_threats:
            return

        # Aang FIRST when opp has a 3+ power threat: airbend (exile) the biggest
        # one before they declare attackers. Better than Floodpits-tap for big
        # creatures since Floodpits only taps once.
        biggest = max(opp_threats, key=lambda c: safe_power(c))
        if safe_power(biggest) >= 3:
            for card in list(gs.zones.hand):
                if card.name == AANG and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs._match_opp = opponent
                    gs.cast_spell(card)
                    gs._log(f"  [pre-combat] Aang -> airbend {biggest.name}")
                    return

        # Otherwise Floodpits Drowner: tap their biggest threat or mana dork
        for card in list(gs.zones.hand):
            if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs._match_opp = opponent
                gs.cast_spell(card)
                return

    # ── End of opponent's turn: flash in Floodpits to stun upkeep ────────────
    def end_step_actions(self, gs: GameState, opponent: GameState):
        """
        Per Zevin: 'turn 2 upkeep Drowner is an excellent response to a turn 2
        Badgermole Cub, keeping the [creature] from making mana for 2 entire turns.'
        Flash Floodpits at end of opponent's turn -> stun counter prevents next
        untap step. Same logic for Skycoach Conductor (also flash).

        ALSO: Aven Interrupter — flash at end of opp's turn when their key
        engine pieces (Stormchaser's Talent, Slickshot Show-Off, Monument,
        etc.) are still in hand. Aven's ETB exiles their highest-priority
        hand card. This is the deck's primary anti-spell-engine line.
        """
        if opponent is None:
            return

        # Aven Interrupter — fire FIRST when opp has a key engine threat in hand.
        # Aven's ETB will pull it out before they can deploy it next turn.
        AVEN_PRIORITY_TARGETS = {"Stormchaser's Talent", "Slickshot Show-Off",
                                  "Monument to Endurance", "Artist's Talent",
                                  "Earthbender Ascension", "Sapling Nursery",
                                  "Mightform Harmonizer", "Ouroboroid",
                                  "Lumbering Worldwagon", "Surrak, Elusive Hunter",
                                  "Mossborn Hydra", "Felidar Retreat",
                                  "Icetill Explorer", "Kaito, Bane of Nightmares"}
        opp_has_priority = any(c.name in AVEN_PRIORITY_TARGETS
                                for c in opponent.zones.hand)
        if opp_has_priority:
            for card in list(gs.zones.hand):
                if card.name == AVEN and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs._match_opp = opponent
                    gs.cast_spell(card)
                    gs._log("  [end-step] Aven Interrupter -> exile priority threat")
                    return

        # Floodpits Drowner: flash to stun a threat
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()
                         and not getattr(c, 'tapped', False)]
        if opp_creatures:
            for card in list(gs.zones.hand):
                if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  [end-step] Floodpits Drowner -> stun")
                    return
            # Skycoach Conductor: flash to chip + prepared copy
            for card in list(gs.zones.hand):
                if card.name == SKYCOACH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  [end-step] Skycoach Conductor")
                    return

        # Aang: flash to airbend a threat off the board
        if opp_creatures:
            for card in list(gs.zones.hand):
                if card.name == AANG and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  [end-step] Aang -> airbend a creature")
                    return

    # ── Post-attackers instant: Floodpits / Aang to push damage through ──────
    def post_attackers_instant(self, gs, opponent, attackers):
        if opponent is None or not attackers:
            return
        # Tap their best blocker with Floodpits to clear the path
        opp_blockers = [c for c in opponent.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'tapped', False)]
        if opp_blockers:
            for card in list(gs.zones.hand):
                if card.name == FLOODPITS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    return

    # ── Main phase: priority order per Zevin's stated lines ──────────────────
    def main_phase_match(self, gs: GameState, opponent: GameState):
        if opponent is not None:
            gs._match_opp = opponent
        self._opp_gs = opponent

        self._play_land_if_able(gs)
        gs.tap_lands()

        # Postboard High Noon timing per guide:
        # vs control matchups, hold High Noon until T5+ (don't lock yourself out)
        is_control = self._opp_is_control(opponent)
        is_creature_matchup = self._opp_is_creature_deck(opponent)

        # ── 1. T2 High Noon (preboard / vs creature decks) ──────────────────
        if not is_control or gs.turn >= 5:
            for card in list(gs.zones.hand):
                if card.name == HIGH_NOON and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    # Don't cast if we've already got one
                    if not any(c.name == HIGH_NOON for c in gs.zones.battlefield):
                        gs.cast_spell(card)
                        break

        # ── 2. Avatar's Wrath if creature board is threatening ──────────────
        # Original: 3+ creatures. New: 3+ creatures OR (2+ creatures with one
        # at power >= 3). Landfall decks ramp into single big bodies (Mightform
        # Harmonizer, Lumbering Worldwagon) where waiting for 3 creatures means
        # we're already dead.
        if is_creature_matchup:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if c.has(Tag.CREATURE) and not c.is_land()]
            opp_cr_count = len(opp_creatures)
            has_big = any(safe_power(c) >= 3 for c in opp_creatures)
            should_wipe = opp_cr_count >= 3 or (opp_cr_count >= 2 and has_big)
            if should_wipe:
                for card in list(gs.zones.hand):
                    if card.name == AVATARS_WRATH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # ── 3. Get Lost on big threats ──────────────────────────────────────
        if opponent is not None:
            big_threats = [c for c in opponent.zones.battlefield
                           if c.has(Tag.CREATURE) and not c.is_land()
                           and safe_power(c) >= 3]
            if big_threats:
                for card in list(gs.zones.hand):
                    if card.name == GET_LOST and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # ── 4. Voice of Victory (lock piece) ────────────────────────────────
        # Per Zevin: 'wait until you have 5 mana + High Noon in play, then cast
        # Voice and pass with Aven/Aang up'
        high_noon_active = any(c.name == HIGH_NOON for c in gs.zones.battlefield)
        if high_noon_active and gs.mana_pool.total() >= 5:
            for card in list(gs.zones.hand):
                if card.name == VOICE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # ── 5. Beza on T4 if behind on board ────────────────────────────────
        if gs.turn >= 4 and gs.life <= 18:
            for card in list(gs.zones.hand):
                if card.name == BEZA and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # ── 6. Quantum Riddler for card advantage ───────────────────────────
        if gs.turn >= 5 and gs.mana_pool.total() >= 5:
            for card in list(gs.zones.hand):
                if card.name == RIDDLER and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # ── 6b. Quantum Riddler Warp ({1}{U}, exiles next EOT) ──────────────
        # If hardcast not affordable but Warp is, deploy as 2-mana flash 4/6
        # for tempo (exiles at next end step). Especially valuable T2-T4
        # before we can hardcast for the empty-hand draw bonus.
        if gs.mana_pool.can_cast("1U", 2):
            for card in list(gs.zones.hand):
                if card.name == RIDDLER:
                    if gs.cast_spell_warp(card):
                        break

        # ── 7. Airbender Ascension (sorcery-speed, fine to main-phase) ──────
        for card in list(gs.zones.hand):
            if card.name == AIRBENDER_ASC and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                if not any(c.name == AIRBENDER_ASC for c in gs.zones.battlefield):
                    gs.cast_spell(card)
                    break

        # NOTE: Aang, Aven, Floodpits, Skycoach, Spell Snare are FLASH and held
        # for end_step_actions / pre_combat_instant / post_attackers_instant
        # windows. Do NOT main-phase them unless mana would otherwise be wasted
        # AND we have no flash threat in hand.

        # Cast remaining flash threats only if we'd otherwise float mana
        # AND it's a good window (e.g. opp tapped out, or T2 with no other plays)
        if gs.mana_pool.total() >= 2 and not any(c.name in self.COUNTER_CARDS
                                                  for c in gs.zones.hand):
            # No counters held; might as well dump mana into a flash creature
            for name in (AVEN, AANG, SKYCOACH, FLOODPITS, RIDDLER):
                for card in list(gs.zones.hand):
                    if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

    # ── Attackers: send everyone, hold back manlands if vulnerable ──────────
    def declare_attackers(self, gs, opponent):
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        return my_creatures

    # ── Blockers: prioritize fliers vs fliers, deathtouch (Glen Elendra) ────
    def declare_blockers(self, gs, opponent, attackers):
        from engine.keywords import KWTag
        if not attackers:
            return {}
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'tapped', False)
                        and not getattr(c, 'summoning_sickness', False)]
        if not my_creatures:
            return {}
        # Prefer fliers blocking fliers; ground bodies block ground
        flying_atk = [a for a in attackers if KWTag.FLYING in a.tags]
        ground_atk = [a for a in attackers if KWTag.FLYING not in a.tags]
        flying_blk = [c for c in my_creatures if KWTag.FLYING in c.tags]
        ground_blk = [c for c in my_creatures if KWTag.FLYING not in c.tags
                      or KWTag.REACH in c.tags]

        assignments = {}
        avail_flying = sorted(flying_blk, key=lambda c: -safe_toughness(c))
        avail_ground = sorted(ground_blk, key=lambda c: -safe_toughness(c))
        for atk in sorted(flying_atk, key=lambda c: -safe_power(c)):
            if avail_flying:
                assignments[id(atk)] = [avail_flying.pop(0)]
        for atk in sorted(ground_atk, key=lambda c: -safe_power(c)):
            if avail_ground:
                assignments[id(atk)] = [avail_ground.pop(0)]
        return assignments

    def _play_land_if_able(self, gs: GameState):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Per Zevin: prioritize Starting Town for any-color High Noon activation
        priority_order = ["Starting Town", "Hallowed Fountain", "Floodfarm Verge",
                          "Island", "Plains", "Abandoned Air Temple",
                          "Multiversal Passage", "Restless Anchorage"]
        for name in priority_order:
            for c in lands:
                if c.name == name:
                    gs.play_land(c)
                    return
        gs.play_land(lands[0])
