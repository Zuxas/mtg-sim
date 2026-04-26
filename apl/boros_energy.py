"""
boros_energy.py — APL for Modern Boros Energy/Ocelot

VERIFIED card interactions (from oracle text):
  - Ragavan: haste, combat damage → Treasure + exile top card. Dash {1}{R}.
  - Ocelot Pride: first_strike, lifelink. END STEP: if you gained life, create
    1/1 Cat token. City's blessing: copy each token that entered this turn.
  - Ajani, Nacatl Pariah: ETB creates 2/1 Cat Warrior token. When 1+ other Cats
    you control die, exile Ajani → return transformed (planeswalker).
  - Guide of Souls: creature enters → gain 1 life + 1 energy.
    Attack trigger: pay 3E → +2/+2 and flying counter on attacker.
  - Goblin Bombardment: sac creature → 1 damage to any target.
  - Voice of Victory: Mobilize 2 (2x 1/1 tapped attacking Warriors, sac EOT).
  - Seasoned Pyromancer: ETB discard 2, draw 2. Per nonland discarded → 1/1 Elemental.
  - Ranger-Captain of Eos: {1}{W}{W} 3/3. ETB tutors a creature with MV ≤ 1 to hand,
    then shuffles. Sac ability (silence opp's noncreatures) is dead in goldfish.
  - Phlage: {1}{R}{W}. ETB/attack → 3 damage any target + gain 3 life.
    Sacrifice on ETB unless escaped. Escape {R}{R}{W}{W} + exile 5 from GY.
    Hard cast = 3-mana Lightning Helix that goes to GY for later escape.
    Escape = 4-mana 6/6 that deals 3 + stays on board.
  - Galvanic Discharge: get {E}{E}{E}, then pay any amount of {E} → that much damage
    to target creature/PW. Goldfish: target own creature, pay 0 → +3 energy net.
  - Thraben Charm: 2x creature count damage to target CREATURE / destroy enchantment /
    exile graveyards. All modes are dead in goldfish.
  - Static Prison: exile opponent's nonland permanent (can't cast in goldfish).
    Gives {E}{E} but requires a target.
  - Screaming Nemesis: 3/3 haste.
  - Lightning Bolt: 3 damage any target.
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

# Card name constants
RAGAVAN          = "Ragavan, Nimble Pilferer"
OCELOT_PRIDE     = "Ocelot Pride"
AJANI            = "Ajani, Nacatl Pariah"
GUIDE_OF_SOULS   = "Guide of Souls"
GOBLIN_BOMBARD   = "Goblin Bombardment"
VOICE_OF_VICTORY = "Voice of Victory"
SEASONED_PYRO    = "Seasoned Pyromancer"
RANGER_CAPTAIN   = "Ranger-Captain of Eos"
PHLAGE           = "Phlage, Titan of Fire's Fury"
SCREAMING_NEMESIS = "Screaming Nemesis"
GALVANIC         = "Galvanic Discharge"
STATIC_PRISON    = "Static Prison"
THRABEN_CHARM    = "Thraben Charm"
LIGHTNING_BOLT   = "Lightning Bolt"


class BorosEnergyAPL(BaseAPL):

    name = "Boros Energy"
    win_condition_damage = 20
    max_turns = 12

    # Per-game state (reset each game)
    _treasures = 0
    _gained_life_this_turn = False
    _tokens_entered_this_turn = 0

    # Cards that literally cannot be cast in goldfish (no valid target)
    DEAD_IN_GOLDFISH = {STATIC_PRISON, "Exorcise"}
    # Cards with very limited goldfish value (creature-only removal, no face)
    LOW_VALUE_GOLDFISH = {THRABEN_CHARM, GALVANIC}

    # ── Role-detection (Phase 1, 2026-04-25) + dispatch unification (Phase 2) ──
    # See harness/knowledge/tech/apl-role-refactor-2026-04-25.md.
    _roles_computed = False

    # SPECIAL_MECHANICS: cards with mechanics too unique to capture via
    # oracle-text patterns. Maps card name -> handler method name string
    # (resolved via getattr for subclass-overridability).
    #
    # Phase 2 simplification: dropped the per-card has_<flag> attr in
    # favor of `card_name in self._deck_names` membership checks.
    # Handlers self-gate on `phase` arg ("main", "main2", "combat", "end").
    #
    # Calling positions in main_phase / main_phase2 are individual (not
    # a single dispatch loop) to preserve canonical call ordering with
    # the role-driven loops -- the unified dispatch helper is used for
    # the new Voice combat-trigger case (Phase 2 stage 2). A future
    # Phase 3 could fully unify if drift bounds permit.
    SPECIAL_MECHANICS = {
        "Phlage, Titan of Fire's Fury": "_handle_phlage",
        "Ajani, Nacatl Pariah":         "_handle_ajani_etb",
        "Ocelot Pride":                 "_handle_ocelot_end_step",
        "Guide of Souls":               "_handle_guide_attack_pump",
        "Arena of Glory":               "_handle_arena_exert_haste",
        "Goblin Bombardment":           "_handle_bombardment_finish",
        "Seasoned Pyromancer":          "_handle_pyromancer_loot",
        "Voice of Victory":             "_handle_voice",  # Phase 2 stage 2
    }

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        # Stage 3 of role refactor: replaced `if any(c.name == RAGAVAN ...)`
        # with KWTag-based haste check. KWTag.HASTE is auto-populated by
        # tag_keywords() during deck load -- works in keep() before
        # _ensure_roles can run (keep() pre-dates GameState construction).
        # Picks up Ragavan, Monastery Swiftspear, Screaming Nemesis, and
        # any new haste 1- or 2-drop in a variant deck.
        from engine.keywords import KWTag
        lands = [c for c in hand if c.is_land()]
        creatures = [c for c in hand if c.has(Tag.CREATURE)]
        dead = [c for c in hand if c.name in self.DEAD_IN_GOLDFISH]
        low = [c for c in hand if c.name in self.LOW_VALUE_GOLDFISH]
        ones = [c for c in hand if c.has(Tag.ONE_DROP) and not c.is_land()]
        haste_threats = [c for c in hand
                         if c.has(Tag.CREATURE) and c.cmc <= 2
                         and KWTag.HASTE in c.tags]
        size = len(hand)

        if size <= 4: return True
        if len(lands) == 0: return False
        if len(lands) == 1 and size >= 6 and mulligans < 3: return False
        if len(lands) > 4: return False
        if not creatures and mulligans < 2: return False
        # Too many dead/low value = mull
        if len(dead) + len(low) >= 3 and mulligans < 2: return False

        # Was: if any(c.name == RAGAVAN for c in hand) and len(lands) >= 1
        if haste_threats and len(lands) >= 1: return True
        if len(lands) >= 2 and ones: return True
        if len(lands) >= 2 and len(creatures) >= 2: return True
        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        dead = [c for c in hand if c.name in self.DEAD_IN_GOLDFISH]
        low = [c for c in hand if c.name in self.LOW_VALUE_GOLDFISH]
        spells = sorted([c for c in hand if not c.is_land()
                         and c.name not in self.DEAD_IN_GOLDFISH
                         and c.name not in self.LOW_VALUE_GOLDFISH],
                        key=lambda c: -c.cmc)
        to_bottom = []
        to_bottom.extend(dead)
        to_bottom.extend(low)
        if len(lands) > 3:
            to_bottom.extend(lands[3:])
        for card in spells:
            if len(to_bottom) >= n: break
            if card.cmc >= 3 and card not in to_bottom:
                to_bottom.append(card)
        for card in spells:
            if len(to_bottom) >= n: break
            if card not in to_bottom:
                to_bottom.append(card)
        return to_bottom[:n]

    def _best_land(self, gs: GameState) -> Optional[Card]:
        lands = [c for c in gs.hand() if c.is_land()]
        if not lands: return None
        if len(lands) == 1: return lands[0]
        def score(c):
            n = c.name.lower()
            if n in ("arid mesa", "flooded strand", "marsh flats", "windswept heath"):
                return 0  # fetches first
            if n in ("sacred foundry",): return 1
            if n in ("arena of glory",): return 2
            if n in ("elegant parlor",): return 3
            if n in ("mountain", "plains"): return 4
            if n in ("dalkovan encampment",): return 5
            return 6
        return min(lands, key=score)

    # ------------------------------------------------------------------
    # Combat trigger simulation
    # ------------------------------------------------------------------

    def _simulate_combat_triggers(self, gs: GameState, num_attackers: int):
        """After combat: Ragavan treasure, Phlage bolt, Ocelot lifelink."""
        from engine.keywords import KWTag

        # Ragavan: each one that attacked creates a Treasure
        ragavans = sum(1 for c in gs.zones.creatures_on_battlefield()
                       if c.name == RAGAVAN
                       and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if ragavans > 0:
            self._treasures += ragavans
            gs._log(f"  Ragavan: +{ragavans} Treasure(s) ({self._treasures} total)")

        # Phlage attack trigger: escaped Phlage deals 3 damage + 3 life on attack
        phlages_attacking = sum(1 for c in gs.zones.creatures_on_battlefield()
                                if c.name == PHLAGE
                                and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if phlages_attacking > 0:
            dmg = 3 * phlages_attacking
            gs.damage_dealt += dmg
            gs.life += dmg
            self._gained_life_this_turn = True
            gs._log(f"  Phlage attack trigger: {dmg} dmg ({gs.damage_dealt} total), +{dmg} life")

        # Ocelot Pride has lifelink — any Ocelot that attacked gained us life
        ocelots_attacked = sum(1 for c in gs.zones.creatures_on_battlefield()
                               if c.name == OCELOT_PRIDE
                               and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if ocelots_attacked > 0:
            self._gained_life_this_turn = True

        # Phase 2 stage 2: dispatch any combat-phase SPECIAL_MECHANICS
        # handlers (Voice of Victory Mobilize today; future combat-phase
        # cards land here automatically when added to SPECIAL_MECHANICS).
        # Guarded by _roles_computed since _simulate_combat_triggers can
        # be called before _ensure_roles in some flows.
        if getattr(self, '_roles_computed', False):
            self._dispatch_special_mechanics(gs, phase='combat')

    def _simulate_guide_attack_trigger(self, gs: GameState):
        """Guide of Souls: when you attack, pay 3E → +2/+2 flying on an attacker."""
        from engine.keywords import KWTag
        guides_attacking = sum(1 for c in gs.zones.creatures_on_battlefield()
                               if c.name == GUIDE_OF_SOULS
                               and (not c.summoning_sickness or KWTag.HASTE in c.tags))
        if guides_attacking > 0 and gs.energy >= 3:
            # Find best attacker to pump
            attackers = [c for c in gs.zones.creatures_on_battlefield()
                         if not c.summoning_sickness or KWTag.HASTE in c.tags]
            if attackers:
                best = max(attackers, key=lambda c: c.effective_power())
                gs.energy -= 3
                best.counters += 2  # +2/+2
                gs._log(f"  Guide of Souls: paid 3E → +2/+2 flying on {best.name} "
                        f"(energy: {gs.energy})")

    def _simulate_end_step(self, gs: GameState):
        """End step: Ocelot Pride creates Cat token if we gained life."""
        ocelots = sum(1 for c in gs.zones.creatures_on_battlefield()
                      if c.name == OCELOT_PRIDE)
        if ocelots > 0 and self._gained_life_this_turn:
            for _ in range(ocelots):
                token = gs._make_token("Cat Token", "1", "1", "Creature — Cat")
                self._tokens_entered_this_turn += 1
                # Guide of Souls triggers on token entering: +1 life +1 energy
                guides = sum(1 for c in gs.zones.battlefield
                             if c.name == GUIDE_OF_SOULS)
                if guides:
                    gs.life += guides
                    gs.energy += guides
                    self._gained_life_this_turn = True  # life gain chains more Ocelots? No, already in end step
            gs._log(f"  Ocelot Pride: {ocelots} Cat token(s) (gained life this turn)")

    def _simulate_ajani_etb(self, gs: GameState):
        """Ajani ETB: create a 2/1 Cat Warrior token."""
        token = gs._make_token("Cat Warrior Token", "2", "1", "Creature — Cat Warrior")
        self._tokens_entered_this_turn += 1
        # Guide triggers on token entering
        guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
        if guides:
            gs.life += guides
            gs.energy += guides
            self._gained_life_this_turn = True
        gs._log(f"  Ajani ETB: 2/1 Cat Warrior token")

    def _bombardment_finish(self, gs: GameState):
        """Sacrifice creatures to Goblin Bombardment ONLY if lethal."""
        if not any(c.name == GOBLIN_BOMBARD for c in gs.zones.battlefield):
            return
        remaining = 20 - gs.damage_dealt
        if remaining <= 0: return
        sacrificeable = [c for c in gs.zones.creatures_on_battlefield()]
        # Only sac if we have enough creatures to deal lethal
        if len(sacrificeable) < remaining:
            return
        # Sort: tokens first, lowest power first
        sacrificeable.sort(key=lambda c: (0 if "Token" in c.name else 1, c.effective_power()))
        sacrificed = 0
        for creature in list(sacrificeable):
            if gs.damage_dealt >= 20: break
            if creature in gs.zones.battlefield:
                gs.zones.battlefield.remove(creature)
                gs.zones.graveyard.append(creature)
                gs.damage_dealt += 1
                sacrificed += 1
                # Cat dying may trigger Ajani transform
        if sacrificed:
            gs._log(f"  Bombardment: sac'd {sacrificed} ({gs.damage_dealt} total dmg)")

    # ------------------------------------------------------------------
    # Main phases
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        """Pre-combat: land, haste creatures, Arena of Glory, sac outlets,
        Ajani ETB, Guide attack pump, energy spells.

        Stage 4 of role refactor: haste loop and sac-outlet loop are
        role-driven (KWTag.HASTE / self.sac_outlets). Arena/Ajani/Guide
        are SPECIAL_MECHANICS handlers gated on has_<flag>. Galvanic
        stays name-keyed (Galvanic-specific +3-energy-net optimization).
        """
        from engine.keywords import KWTag
        self._ensure_roles(gs)

        # Reset per-turn tracking
        self._gained_life_this_turn = False
        self._tokens_entered_this_turn = 0

        # Treasure mana
        if self._treasures > 0:
            use = min(self._treasures, 3)
            gs.mana_pool.flex += use
            self._treasures -= use
            if use: gs._log(f"  Cracked {use} Treasure(s)")

        # 1. Land
        self._play_land_if_able(gs)

        # 2. Haste creatures pre-combat -- ROLE-DRIVEN (was: for name in
        #    (RAGAVAN, SCREAMING_NEMESIS)). Iterates hand for any creature
        #    with KWTag.HASTE; casts each whose mana is available. No
        #    break -- preserves OLD behavior of casting one of each haste
        #    name when mana allows (multiple-Ragavan case slightly more
        #    aggressive than OLD's per-name-break, acceptable per drift bounds).
        for card in list(gs.hand()):
            if (card.has(Tag.CREATURE) and KWTag.HASTE in card.tags
                    and gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs._log(f"  [PRE-COMBAT] {card.name} (haste, role-detected)")
                gs.cast_spell(card)

        # 3. Arena of Glory exert (SPECIAL_MECHANICS)
        if "Arena of Glory" in self._deck_names:
            self._handle_arena_exert_haste(gs, 'main')

        # 4. Sac outlets -- ROLE-DRIVEN (was: if card.name == GOBLIN_BOMBARD).
        #    Cast first sac outlet found castable. Picks up Bombardment plus
        #    any new sac outlet in a variant deck.
        for card in list(gs.hand()):
            if (card.name in self.sac_outlets
                    and gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs.cast_spell(card)
                break

        # 5. Ajani pre-combat (SPECIAL_MECHANICS) -- 2/1 token triggers Guide
        if "Ajani, Nacatl Pariah" in self._deck_names:
            self._handle_ajani_etb(gs, 'main')

        # 6. Guide of Souls attack trigger (SPECIAL_MECHANICS) -- pay 3E for +2/+2 flying
        if "Guide of Souls" in self._deck_names:
            self._handle_guide_attack_pump(gs, 'main')

        # 7. Galvanic Discharge — cast ALL for +3 energy each
        for card in list(gs.hand()):
            if card.name == GALVANIC and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                creatures = gs.zones.creatures_on_battlefield()
                if creatures:
                    gs.energy += 3
                    gs.cast_spell(card)
                    gs._log(f"  Galvanic: +3 energy ({gs.energy}), 0 dmg to own creature")

    def main_phase2(self, gs: GameState):
        """Post-combat: combat triggers, role-driven creature deployment,
        SPECIAL_MECHANICS handlers (Pyromancer, Phlage, Ocelot end-step,
        Bombardment finish), face burn.

        Stage 5 of role refactor: explicit priority tuple replaced with
        cheapest-first iteration over castable creatures in hand. Phlage
        / Pyromancer / Ocelot / Bombardment moved into _handle_* methods
        gated on has_<flag>. Lightning Bolt / face burn replaced with
        self.face_burn role iteration.
        """
        from engine.keywords import KWTag
        self._ensure_roles(gs)

        # Combat triggers (Ragavan treasure, Phlage attack, Ocelot lifelink)
        attackers = [c for c in gs.zones.creatures_on_battlefield()
                     if not c.summoning_sickness or KWTag.HASTE in c.tags]
        num_attackers = len(attackers)
        if num_attackers > 0:
            self._simulate_combat_triggers(gs, num_attackers)

        # Role-driven creature deployment -- was: explicit priority tuple
        # (OCELOT_PRIDE, GUIDE_OF_SOULS, AJANI, VOICE_OF_VICTORY, RAGAVAN).
        # Now: cheapest-first iteration over castable creatures in hand.
        # Each cast fires Ajani ETB if applicable + Guide trigger if guide
        # is on bf. Subsumes both the old priority tuple and the old
        # fill-curve loop into one role-driven loop.
        while True:
            castable = sorted(
                [c for c in gs.hand()
                 if c.has(Tag.CREATURE)
                 and c.name not in self.DEAD_IN_GOLDFISH
                 and gs.mana_pool.can_cast(c.mana_cost, c.cmc)],
                key=lambda c: (c.cmc, c.name),
            )
            if not castable:
                break
            card = castable[0]
            if not gs.cast_spell(card):
                break
            if card.name == AJANI:
                self._simulate_ajani_etb(gs)
            # Guide trigger for any creature ETB
            if "Guide of Souls" in self._deck_names:
                guides = sum(1 for c in gs.zones.battlefield
                             if c.name == GUIDE_OF_SOULS)
                if guides:
                    gs.life += guides
                    gs.energy += guides
                    self._gained_life_this_turn = True
                    gs._log(f"  Guide trigger: +{guides} life, +{guides} energy")

        # Pyromancer loot (SPECIAL_MECHANICS)
        if "Seasoned Pyromancer" in self._deck_names:
            self._handle_pyromancer_loot(gs, 'main2')

        # Phlage hardcast + escape (SPECIAL_MECHANICS).
        # Preserves the CMC=0 mana-pool kludge inside the handler.
        if "Phlage, Titan of Fire's Fury" in self._deck_names:
            self._handle_phlage(gs, 'main2')

        # Face burn -- ROLE-DRIVEN (was: if card.name == LIGHTNING_BOLT).
        # Cast all face_burn instants/sorceries; damage parsed from oracle.
        for card in list(gs.hand()):
            if (card.name in self.face_burn
                    and gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs.cast_spell(card)
                dmg = self._parse_burn_damage(card)
                gs.damage_dealt += dmg
                gs._log(f"  Face burn ({card.name}): {dmg} dmg ({gs.damage_dealt} total)")

        # End step: Ocelot Pride tokens (SPECIAL_MECHANICS)
        if "Ocelot Pride" in self._deck_names:
            self._handle_ocelot_end_step(gs, 'end')

        # Bombardment finish (SPECIAL_MECHANICS)
        if "Goblin Bombardment" in self._deck_names:
            self._handle_bombardment_finish(gs, 'main2')

    # ────────────────────────────────────────────────────────────────
    # Phase 1 role-refactor scaffolding (2026-04-25, stage 2)
    # ────────────────────────────────────────────────────────────────
    # See harness/knowledge/tech/apl-role-refactor-2026-04-25.md for
    # the full architectural spec. Stage 2: methods exist but NOT
    # called from the turn loop (no behavior change). Stages 3-5
    # migrate keep/bottom/main_phase/main_phase2 to use them.

    def _compute_roles(self, deck_cards):
        """Scan the loaded 75 once, bucket each card by inferred role.
        After this runs, the turn loop queries roles, not names."""
        from engine.keywords import KWTag
        deck_names = {c.name for c in deck_cards}

        def _otext(c):
            return (c.oracle_text or "").lower()

        # Haste threats: creatures MV <= 2 with haste
        # (Ragavan, Screaming Nemesis, Monastery Swiftspear, etc.)
        self.haste_threats = {
            c.name for c in deck_cards
            if c.has(Tag.CREATURE) and c.cmc <= 2
            and (KWTag.HASTE in c.tags or "haste" in _otext(c))
        }

        # Lifegain sources (Ocelot lifelink, Phlage gain 3, Helix, Guide)
        self.lifegain_sources = {
            c.name for c in deck_cards
            if KWTag.LIFELINK in c.tags
            or any(p in _otext(c) for p in ("you gain", "gain life", "gains life"))
        }

        # Token producers (Ajani, Pyromancer when discarding, Voice of Victory)
        self.token_producers = {
            c.name for c in deck_cards
            if "create" in _otext(c) and "token" in _otext(c)
        }

        # Energy sources (Guide of Souls, Galvanic Discharge, Static Prison)
        self.energy_sources = {
            c.name for c in deck_cards
            if "{e}" in _otext(c) or "energy" in _otext(c)
        }

        # Sac outlets (Goblin Bombardment, anything similar)
        self.sac_outlets = {
            c.name for c in deck_cards
            if "sacrifice a creature" in _otext(c) and ":" in _otext(c)
        }

        # Face burn -- instants/sorceries that "deal X damage to any target"
        # NOTE: Phlage NOT in here (it's a creature, routed through has_phlage)
        self.face_burn = {
            c.name for c in deck_cards
            if (c.has(Tag.INSTANT) or c.has(Tag.SORCERY))
            and "damage to any target" in _otext(c)
        }

        # All creatures sorted by CMC ascending, name as tiebreak.
        # Used by stage-5 main_phase2 fill-curve loop (cheapest-first).
        cmc_by_name = {c.name: c.cmc for c in deck_cards}
        self.creatures_by_cmc = sorted(
            {c.name for c in deck_cards if c.has(Tag.CREATURE)},
            key=lambda n: (cmc_by_name[n], n),
        )

        # Phase 2 unification: deck_names membership replaces individual
        # has_<card> flags for SPECIAL_MECHANICS dispatch.
        self._deck_names = deck_names

        self._roles_computed = True

    def _dispatch_special_mechanics(self, gs, phase):
        """Dispatch every registered SPECIAL_MECHANICS handler whose card
        is in the current deck. Handlers self-gate on `phase` arg.
        Used for combat-phase dispatch (Voice Mobilize) where a single
        dispatch loop fits naturally. main_phase / main_phase2 keep
        individual handler call positions to preserve canonical ordering."""
        for card_name, handler_name in self.SPECIAL_MECHANICS.items():
            if card_name in self._deck_names:
                handler = getattr(self, handler_name, None)
                if handler is not None:
                    handler(gs, phase)

    def _ensure_roles(self, gs):
        """Lazy-compute role buckets on first turn-loop call.
        Sources deck cards from gs.zones (library + hand + bf + GY)."""
        if self._roles_computed:
            return
        deck_cards = (list(gs.zones.library) + list(gs.zones.hand)
                      + list(gs.zones.battlefield) + list(gs.zones.graveyard))
        self._compute_roles(deck_cards)

    def _run_special_mechanics(self, gs, phase):
        """Dispatch each registered SPECIAL_MECHANICS handler whose
        corresponding has_<card> flag is True. phase in
        {'main', 'combat', 'main2', 'end'}."""
        for card_name, (flag_attr, method_name) in self.SPECIAL_MECHANICS.items():
            if getattr(self, flag_attr, False):
                handler = getattr(self, method_name, None)
                if handler is not None:
                    handler(gs, phase)

    # ── Handler stubs (stage 2: empty; stages 4-5 fill them in) ──

    def _handle_phlage(self, gs, phase):
        """Phlage hardcast + escape from GY. PRESERVES the CMC=0
        mana-pool kludge (Scryfall data has Phlage at CMC 0; mana check
        uses can_pay/pay with literal cost strings instead of can_cast).
        Stage 5 fill-in: moved verbatim from main_phase2."""
        if phase != 'main2':
            return
        # Phlage hardcast {1}{R}{W}: 3 dmg + 3 life, then sacrifice
        for card in list(gs.hand()):
            if (card.name == PHLAGE
                    and gs.mana_pool.can_pay("{1}{R}{W}", 3)):
                gs.mana_pool.pay("{1}{R}{W}", 3)
                gs.zones.remove_from_hand(card)
                gs.zones.battlefield.append(card)
                card.turn_entered = gs.turn
                gs.damage_dealt += 3
                gs.life += 3
                self._gained_life_this_turn = True
                # Sacrifice -- didn't escape from hand
                if card in gs.zones.battlefield:
                    gs.zones.battlefield.remove(card)
                    gs.zones.graveyard.append(card)
                gs._log(f"  Phlage hardcast: 3 dmg ({gs.damage_dealt}), "
                        f"+3 life, sacrificed (to GY for escape)")
                break
        # Phlage Escape: needs Phlage in GY + 5 other cards + {R}{R}{W}{W}
        phlage_in_gy = next(
            (c for c in gs.zones.graveyard if c.name == PHLAGE), None)
        other_gy_cards = [c for c in gs.zones.graveyard if c.name != PHLAGE]
        if (phlage_in_gy and len(other_gy_cards) >= 5
                and gs.mana_pool.can_pay("{R}{R}{W}{W}", 4)):
            gs.mana_pool.pay("{R}{R}{W}{W}", 4)
            for c in other_gy_cards[:5]:
                gs.zones.graveyard.remove(c)
                gs.zones.exile.append(c)
            gs.zones.graveyard.remove(phlage_in_gy)
            gs.zones.battlefield.append(phlage_in_gy)
            phlage_in_gy.turn_entered = gs.turn
            phlage_in_gy.summoning_sickness = True
            phlage_in_gy.power = "6"
            phlage_in_gy.toughness = "6"
            gs.damage_dealt += 3
            gs.life += 3
            self._gained_life_this_turn = True
            gs._log(f"  Phlage ESCAPED: 3 dmg ({gs.damage_dealt}), "
                    f"+3 life, 6/6 stays")

    def _handle_ajani_etb(self, gs, phase):
        """Pre-combat Ajani cast: 2/1 Cat Warrior token triggers Guide,
        sets up bigger attack. Stage 4 fill-in: moved from main_phase
        section 5 (was: `if card.name == AJANI ...`)."""
        if phase != 'main':
            return
        for card in list(gs.hand()):
            if (card.name == AJANI
                    and gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs.cast_spell(card)
                self._simulate_ajani_etb(gs)
                return

    def _handle_ocelot_end_step(self, gs, phase):
        """Ocelot Pride end-step Cat token if gained-life-this-turn.
        Stage 5 fill-in: delegates to existing _simulate_end_step
        which has the Ocelot+Guide chain logic."""
        if phase != 'end':
            return
        self._simulate_end_step(gs)

    def _handle_guide_attack_pump(self, gs, phase):
        """Guide of Souls attack trigger: pay 3E for +2/+2 flying.
        Stage 4 fill-in: delegates to existing
        _simulate_guide_attack_trigger."""
        if phase != 'main':
            return
        self._simulate_guide_attack_trigger(gs)

    def _handle_arena_exert_haste(self, gs, phase):
        """Arena of Glory exert: tap for RR, give haste to a non-haste
        creature. Stage 4 fill-in: moved from main_phase section 3."""
        if phase != 'main':
            return
        from engine.keywords import KWTag
        arena = next((c for c in gs.zones.lands_on_battlefield()
                      if c.name == "Arena of Glory" and not c.tapped), None)
        if not arena:
            return
        # Find a non-haste creature to give haste via Arena
        # Was: `card.name not in (RAGAVAN, SCREAMING_NEMESIS)`
        # Now: filter by KWTag.HASTE absence (creature doesn't already have haste)
        castable_with_haste = []
        for card in gs.hand():
            if (card.has(Tag.CREATURE)
                    and KWTag.HASTE not in card.tags
                    and card.summoning_sickness != False):  # not already on BF
                test_total = gs.mana_pool.total() + 1  # +1 net from exert
                if card.cmc <= test_total:
                    castable_with_haste.append(card)
        if not castable_with_haste:
            return
        # Pick best creature to give haste (highest power)
        best = max(castable_with_haste, key=lambda c: (
            int(c.power or 0), -c.cmc))
        # Exert Arena: tap it, add RR to pool
        arena.tapped = True
        arena._exerted = True  # won't untap next turn
        gs.mana_pool.add("R", 2)
        if gs.mana_pool.can_cast(best.mana_cost, best.cmc):
            gs.cast_spell(best)
            best.summoning_sickness = False  # HASTE from Arena
            gs._log(f"  [PRE-COMBAT] Arena of Glory exert -> {best.name} has HASTE")
            # Guide triggers on creature entering
            guides = sum(1 for c in gs.zones.battlefield
                         if c.name == GUIDE_OF_SOULS)
            if guides:
                gs.life += guides
                gs.energy += guides
                self._gained_life_this_turn = True

    def _handle_bombardment_finish(self, gs, phase):
        """Sac creatures to Goblin Bombardment for lethal.
        Stage 5 fill-in: delegates to existing _bombardment_finish
        which has the lethal-check + sac-priority logic."""
        if phase != 'main2':
            return
        self._bombardment_finish(gs)

    def _handle_pyromancer_loot(self, gs, phase):
        """Seasoned Pyromancer ETB: discard 2, draw 2, +1/1 Elemental
        token per nonland discarded. Stage 5 fill-in: moved verbatim
        from main_phase2."""
        if phase != 'main2':
            return
        for card in list(gs.hand()):
            if (card.name == SEASONED_PYRO
                    and gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs.cast_spell(card)
                # Discard 2: prefer discarding lands/dead cards
                hand = list(gs.zones.hand)
                discardable = sorted(hand, key=lambda c: (
                    0 if c.name in self.DEAD_IN_GOLDFISH else
                    1 if c.is_land() else
                    2 if c.name in self.LOW_VALUE_GOLDFISH else 3
                ))
                discarded_nonlands = 0
                for c in discardable[:2]:
                    if c in gs.zones.hand:
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        if not c.is_land():
                            discarded_nonlands += 1
                gs.zones.draw(2)
                for _ in range(discarded_nonlands):
                    gs._make_token("Elemental Token", "1", "1",
                                    "Creature — Elemental")
                    self._tokens_entered_this_turn += 1
                    guides = sum(1 for c in gs.zones.battlefield
                                 if c.name == GUIDE_OF_SOULS)
                    if guides:
                        gs.life += guides
                        gs.energy += guides
                        self._gained_life_this_turn = True
                gs._log(f"  Pyromancer: discard 2, draw 2, "
                        f"{discarded_nonlands} Elemental(s)")
                return

    def _handle_voice(self, gs, phase):
        """Voice of Victory: Mobilize 2 -- when this attacks, create 2x
        1/1 tapped attacking Warrior tokens (sacrificed end of turn).

        Goldfish modeling: tokens enter ATTACKING per oracle and are
        sacrificed EOT, so they don't persist to the next combat. We
        model them as immediate +2 dmg per Voice attacking, plus Guide
        ETB triggers for each token entering. We don't materialize the
        token objects on the battlefield (no persistence needed in
        goldfish; Mobilize tokens are Warriors not Cats so no Ajani
        transform interaction).

        Phase 2 stage 2 -- new card. See spec at
        harness/knowledge/tech/apl-role-refactor-2026-04-25.md."""
        if phase != 'combat':
            return
        from engine.keywords import KWTag
        voices_attacking = sum(
            1 for c in gs.zones.creatures_on_battlefield()
            if c.name == "Voice of Victory"
            and (not c.summoning_sickness or KWTag.HASTE in c.tags)
        )
        if voices_attacking == 0:
            return
        tokens = 2 * voices_attacking  # 2 tokens per Voice
        gs.damage_dealt += tokens      # 1 dmg each (1/1 attacking)
        # Guide ETB triggers per token entering
        if "Guide of Souls" in self._deck_names:
            guides = sum(1 for c in gs.zones.battlefield
                         if c.name == GUIDE_OF_SOULS)
            if guides > 0:
                life_gain = guides * tokens
                gs.life += life_gain
                gs.energy += life_gain
                self._gained_life_this_turn = True
                gs._log(f"  Voice Mobilize Guide trigger: "
                        f"+{life_gain} life, +{life_gain} energy")
        gs._log(f"  Voice of Victory Mobilize: {voices_attacking} Voice(s) "
                f"attacking -> {tokens} 1/1 Warrior tokens = {tokens} dmg "
                f"({gs.damage_dealt} total)")

    # ── Helper for face-burn role iteration ──

    _BURN_DMG_RE = None  # compiled lazily

    def _parse_burn_damage(self, card):
        """Extract damage amount from face-burn oracle text.
        Looks for 'deals N damage' or 'deal N damage'. Falls back to 3
        (Lightning Bolt default) if no match."""
        import re
        if BorosEnergyAPL._BURN_DMG_RE is None:
            BorosEnergyAPL._BURN_DMG_RE = re.compile(
                r"deals?\s+(\d+)\s+damage", re.IGNORECASE)
        if card.oracle_text:
            m = BorosEnergyAPL._BURN_DMG_RE.search(card.oracle_text)
            if m:
                return int(m.group(1))
        return 3
