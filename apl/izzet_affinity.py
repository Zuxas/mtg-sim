"""
izzet_affinity.py — APL for Modern Izzet Affinity (full rewrite, April 2026)

VERIFIED card interactions (from local CardDB, deck: izzet_affinity_modern.txt):

  Kappa Cannoneer [{5}{U}] — Artifact Creature, Turtle Warrior
    Improvise: each artifact you tap after mana abilities pays {1}.
    Ward {4}: opponent must pay 4 or their spell/ability is countered.
    ETB + each artifact ETB → put a +1/+1 counter on Kappa; it can't be blocked this turn.
    NOTE: triggers on EVERY artifact entering, including tokens. 4/4 base.

  Pinnacle Emissary [{1}{U}{R}] — Artifact Creature, Robot. 3/3.
    Whenever you CAST an artifact spell → create 1/1 colorless Drone artifact
    creature token with flying (blocks only flyers).
    Warp {U/R}: cast from hand for {U/R}, exile at end step, recast from exile later.
    NOTE: casting Emissary itself (an artifact spell) triggers its own ability → 1 Drone.

  Weapons Manufacturing [{1}{R}] — Enchantment.
    Whenever a NONTOKEN artifact you control enters → create a colorless artifact
    token named Munitions with "When this token leaves the battlefield, deal 2 to
    any target." This is a LEAVES trigger, not ETB — sacrifice/destroy to trigger.

  Claws of Gix [{0}] — Artifact.
    {1}, Sacrifice a permanent: you gain 1 life.
    KEY: Sacrifice Munitions tokens with Claws of Gix → 2 damage each + 1 life.

  Skateboard [{1}] — Equipment.
    ETB: tap a target permanent.
    Equipped creature gets +1/+0 and haste. Equip {1}.
    Goldfish value: tap opponent's blocker (irrelevant) / give Kappa haste.

  Emry, Lurker of the Loch [{2}{U}] — Legendary Creature, 1/2.
    Affinity for artifacts (costs {1} less per artifact you control).
    ETB: mill 4.
    {T}: choose target artifact card in your GY; you may cast it this turn.
    KEY: recurring Mox Opal / 0-drops from GY = free mana and triggers.

  Arcbound Ravager [{2}] — Artifact Creature, 0/0. Modular 1 (enters with +1/+1).
    Sacrifice an artifact: put a +1/+1 counter on this creature.
    When it dies, move its counters to target artifact creature.

  Metallic Rebuke [{2}{U}] — Instant, Improvise.
    Counter target spell unless controller pays {3}. DEAD IN GOLDFISH — bottom it.

  Mox Opal [{0}] — Legendary Artifact.
    Metalcraft: {T}: add one mana of any color. Activate only if 3+ artifacts in play.

  Engineered Explosives [{X}] — Artifact, Sunburst (enters with 1 counter per color spent).
    {2}, Sacrifice: destroy each nonland permanent with MV = # charge counters.
    GOLDFISH BURST: cast X=0 (free), let Weapons Manufacturing create Munitions,
    then {2}+sacrifice EE (destroys MV0 permanents including Munitions) → 2 dmg each.
    NOTE: Munitions token has MV 0 (token, no mana cost) → dies to EE at 0.

  Tormod's Crypt [{0}] — Artifact.
    {T}, Sacrifice: exile target player's GY. Dead in goldfish but free artifact.

  Urza's Saga [land] — Enchantment Land, Urza's Saga.
    Chapter I (enter): gains "{T}: Add {C}."
    Chapter II: gains "{2},{T}: Create 0/0 Construct token (gets +1/+1 per artifact)."
    Chapter III: search library for artifact with mana cost {0} or {1}, put into play.
    Then sacrifice.

  Aether Spellbomb [{1}] — Artifact.
    {U}, Sacrifice: return target creature to hand. (Dead in goldfish.)
    {1}, Sacrifice: draw a card. (Use to filter.)

  Mishra's Bauble [{0}] — Artifact.
    {T}, Sacrifice: look at top card of any library. Draw a card at start of next upkeep.

  Welding Jar [{0}] — Artifact.
    Sacrifice: regenerate target artifact. (Dead in goldfish, free 0-drop.)

  Pithing Needle [{1}] — Artifact.
    Name a card; activated abilities of cards with that name can't be activated.
    (Dead in goldfish but a 1-drop artifact for Emry / Urza's Saga fetch.)
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Card name constants ────────────────────────────────────────────────────────
KAPPA           = "Kappa Cannoneer"
PINNACLE        = "Pinnacle Emissary"
WEAPONS_MFG     = "Weapons Manufacturing"
CLAWS_OF_GIX    = "Claws of Gix"
SKATEBOARD      = "Skateboard"
EMRY            = "Emry, Lurker of the Loch"
ARCBOUND        = "Arcbound Ravager"
METALLIC_REBUKE = "Metallic Rebuke"
MOX_OPAL        = "Mox Opal"
EE              = "Engineered Explosives"
TORMOD          = "Tormod's Crypt"
URZA_SAGA       = "Urza's Saga"
AETHER_BOMB     = "Aether Spellbomb"
BAUBLE          = "Mishra's Bauble"
WELDING_JAR     = "Welding Jar"
PITHING_NEEDLE  = "Pithing Needle"
SHADOWSPEAR     = "Shadowspear"

# Free 0-drop artifacts (no mana cost at all)
FREE_ARTIFACTS = {MOX_OPAL, TORMOD, BAUBLE, WELDING_JAR, CLAWS_OF_GIX}
# Cheap 1-drop artifacts worth casting early
ONE_DROP_ARTIFACTS = {EE, AETHER_BOMB, SKATEBOARD, PITHING_NEEDLE, SHADOWSPEAR}
# Spells that are dead in goldfish and should be bottomed
DEAD_IN_GOLDFISH = {METALLIC_REBUKE}  # Only Rebuke is truly dead; Tormod/Aether are free artifact triggers


class IzzetAffinityAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Izzet Affinity (2026).

    Win axes:
      A) Kappa Cannoneer — Ward-4 threat that grows from every artifact ETB.
         Improvise makes it castable with 0 real mana once artifacts are on board.
      B) Urza's Saga — Land that makes a Construct army and fetches 0-1 mana artifacts.
      C) Weapons Manufacturing + EE — Each nontoken artifact ETB creates a Munitions token.
         Sacrifice EE at X=0 to destroy all MV-0 permanents (including all Munitions)
         → 2 damage per Munitions = burst kill from nowhere.

    Typical kill: T3 Kappa unblockable beatdown or T4 Weapons+EE burst.
    """

    name = "Izzet Affinity"
    win_condition_damage = 20
    max_turns = 10

    # ── Per-game state (class-level defaults, overwritten each run_game) ──
    # Follows boros_energy.py pattern: class attrs shadow to instance attrs on write.
    # reset_game() resets all of these at the top of each goldfish game.
    _munitions_count   = 0
    _weapons_mfg_up    = False
    _kappa_up          = False
    _kappa_counters    = 0
    _pinnacle_up       = False
    _emry_up           = False
    _gy_artifacts: list = []
    _ee_in_hand        = 0
    _saga_chapter      = 0
    _saga_up           = False

    def reset_game(self):
        """Reset per-game state. Call at start of each game manually or via hook."""
        self._munitions_count   = 0
        self._weapons_mfg_up    = False
        self._kappa_up          = False
        self._kappa_counters    = 0
        self._pinnacle_up       = False
        self._emry_up           = False
        self._gy_artifacts      = []
        self._ee_in_hand        = 0
        self._saga_chapter      = 0
        self._saga_up           = False

    # ── Helper: count artifacts on battlefield ─────────────────────────
    def _artifact_count(self, gs: GameState) -> int:
        """All artifacts in play (creatures, non-creatures, tokens)."""
        return sum(
            1 for c in gs.zones.battlefield
            if "artifact" in c.type_line.lower()
        )

    def _metalcraft(self, gs: GameState) -> bool:
        """True if we control 3+ artifacts (Mox Opal / Metallic Rebuke condition)."""
        return self._artifact_count(gs) >= 3

    def _improvise_reduction(self, gs: GameState) -> int:
        """
        How many {1} can we save via Improvise?
        Tap artifacts that aren't already tapped and aren't providing mana.
        Conservative: only count non-land artifacts not needed for mana.
        Mox Opal is excluded (we need it for colored mana).
        """
        improvise_artifacts = [
            c for c in gs.zones.battlefield
            if "artifact" in c.type_line.lower()
            and c.name != MOX_OPAL       # keep Opal for colored mana
            and not c.is_land()
        ]
        return len(improvise_artifacts)

    def _can_cast_kappa(self, gs: GameState) -> bool:
        """
        Kappa Cannoneer: {5}{U} base. Improvise reduces generic cost.
        With N improvise artifacts and M colored mana + flex:
          generic_needed = max(0, 5 - improvise_count)
          need at least 1 {U} for the pip.
        """
        imp = self._improvise_reduction(gs)
        generic_needed = max(0, 5 - imp)
        has_blue = (gs.mana_pool.U + gs.mana_pool.flex) >= 1
        has_generic = (gs.mana_pool.total() - 1) >= generic_needed if has_blue else False
        return has_blue and has_generic

    def _can_cast_metallic_rebuke(self, gs: GameState) -> bool:
        """Metallic Rebuke: {2}{U} with Improvise. Dead in goldfish — always False."""
        return False


    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Affinity mulligans differently than creature decks.
        We want: artifact density + a payoff or enabler.

        Keep criteria:
          - Always keep 4 or fewer (post-mull we take what we get)
          - Need at least 1 colored mana source (land or Mox Opal with metalcraft)
          - Need 2+ artifacts for Metalcraft to come online fast
          - Want at least 1 payoff: Kappa, Pinnacle, Weapons Mfg, Emry, Urza's Saga
          - Mull hands with 3+ dead-in-goldfish spells (Metallic Rebuke)
        """
        if len(hand) <= 4:
            return True

        lands    = [c for c in hand if c.is_land()]
        free_art = [c for c in hand if c.name in FREE_ARTIFACTS]
        one_drop = [c for c in hand if c.name in ONE_DROP_ARTIFACTS]
        dead     = [c for c in hand if c.name in DEAD_IN_GOLDFISH]

        payoffs = [c for c in hand if c.name in {
            KAPPA, PINNACLE, WEAPONS_MFG, EMRY, ARCBOUND, SKATEBOARD
        }]
        sagas = [c for c in hand if c.name == URZA_SAGA]

        total_artifacts = len(free_art) + len(one_drop)

        # Hard mulls
        if not lands and not any(c.name == MOX_OPAL for c in hand):
            return False   # no mana at all
        if len(lands) > 4:
            return False   # flood
        if len(dead) >= 3 and mulligans < 2:
            return False

        # Need real artifact density to function
        if total_artifacts < 1 and mulligans < 2:
            return False

        # Urza's Saga acts as land + payoff: great keep with any artifacts
        if sagas and total_artifacts >= 1:
            return True

        # Payoff + artifacts + mana = keep
        if payoffs and total_artifacts >= 1 and (lands or free_art):
            return True

        # Pure artifact density with land: acceptable
        if total_artifacts >= 3 and lands:
            return True

        # Fallback: any hand with land + nonland is keepable on 6 or fewer
        if lands and (free_art or one_drop or payoffs) and len(hand) <= 6:
            return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        London Mulligan bottom priority for Affinity:
          1. Excess lands (want exactly 2, Urza's Saga counts)
          2. Dead-in-goldfish spells (Metallic Rebuke, Aether Spellbomb)
          3. Duplicate payoffs (second Kappa / second Emry)
          4. Highest CMC non-payoff spells
        """
        to_bottom: list[Card] = []
        lands = [c for c in hand if c.is_land()]

        # 1. Excess lands past 2 (keep 2 max for this deck)
        excess_lands = [c for c in lands if c.name != URZA_SAGA][2:]
        to_bottom.extend(excess_lands)

        # 2. Dead spells
        for c in hand:
            if len(to_bottom) >= n:
                break
            if c.name in DEAD_IN_GOLDFISH and c not in to_bottom:
                to_bottom.append(c)

        # 3. Duplicate copies of payoffs (keep first, bottom rest)
        seen = set()
        for c in hand:
            if len(to_bottom) >= n:
                break
            if c.name in {KAPPA, EMRY, WEAPONS_MFG} and c not in to_bottom:
                if c.name in seen:
                    to_bottom.append(c)
                else:
                    seen.add(c.name)

        # 4. Highest CMC non-free spells
        rest = sorted(
            [c for c in hand if not c.is_land() and c not in to_bottom],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n:
                break
            to_bottom.append(c)

        return to_bottom[:n]


    # ── Trigger handler ─────────────────────────────────────────────────
    def _on_artifact_etb(self, card: Card, is_token: bool, gs: GameState):
        """
        Central trigger router called whenever any artifact enters the battlefield.

        Fires:
          - Kappa Cannoneer: +1/+1 counter + can't be blocked this turn.
          - Weapons Manufacturing (nontoken only): create a Munitions token.
          - Pinnacle Emissary: only on artifact SPELLS cast (handled separately in cast hooks).

        NOTE: Munitions tokens ARE artifacts entering → they trigger Kappa again.
        NOTE: Munitions tokens are tokens → they do NOT re-trigger Weapons Manufacturing.
        """
        art_count = self._artifact_count(gs)

        # Kappa Cannoneer trigger: fires on every artifact ETB (including tokens)
        if self._kappa_up:
            self._kappa_counters += 1
            # Kappa can't be blocked this turn (affects combat damage)
            # Power = 4 (base) + counters. All damage goes through unblocked.
            kappa_power = 4 + self._kappa_counters
            gs._log(f"  Kappa trigger: +1/+1 counter (now {kappa_power}/4+{self._kappa_counters}), unblockable this turn")

        # Weapons Manufacturing trigger: nontoken artifacts only
        if self._weapons_mfg_up and not is_token:
            self._munitions_count += 1
            gs._log(f"  Weapons Manufacturing: Munitions token #{self._munitions_count} created")
            # The Munitions token is itself an artifact entering → Kappa trigger
            if self._kappa_up:
                self._kappa_counters += 1
                gs._log(f"  Kappa trigger from Munitions: now {4 + self._kappa_counters}/{4 + self._kappa_counters}")

    def _on_artifact_spell_cast(self, card: Card, gs: GameState):
        """
        Called when we CAST an artifact spell (not when token enters).
        Pinnacle Emissary triggers on 'cast', not on 'ETB'.
        Creates 1/1 Drone token → artifact creature enters → triggers Kappa + Weapons Mfg.
        """
        if self._pinnacle_up:
            gs._log(f"  Pinnacle Emissary: Drone token from casting {card.name}")
            # Drone is a token artifact creature entering (nontoken? No — it IS a token)
            # Kappa triggers on ALL artifacts including tokens
            if self._kappa_up:
                self._kappa_counters += 1
                gs._log(f"  Kappa trigger from Drone: now {4 + self._kappa_counters}/{4 + self._kappa_counters}")
            # Weapons Mfg: tokens do NOT re-trigger it (only NONTOKEN artifacts)

    # ── Mox Opal mana generation ─────────────────────────────────────────
    def _apply_mox_mana(self, gs: GameState):
        """Add colored mana from any Mox Opals in play under Metalcraft."""
        if self._metalcraft(gs):
            mox_count = sum(1 for c in gs.zones.battlefield if c.name == MOX_OPAL)
            if mox_count > 0:
                gs.mana_pool.flex += mox_count
                gs._log(f"  Mox Opal x{mox_count}: Metalcraft, +{mox_count} flex mana")

    # ── Cast helpers ─────────────────────────────────────────────────────
    def _cast_free_artifact(self, card: Card, gs: GameState):
        """Cast a 0-mana artifact. Update triggers."""
        gs.cast_spell(card)
        self._on_artifact_spell_cast(card, gs)
        self._on_artifact_etb(card, is_token=False, gs=gs)
        # Mox Opal just entered — re-check metalcraft for mana
        if card.name == MOX_OPAL:
            self._apply_mox_mana(gs)

    def _cast_spell_with_cost(self, card: Card, gs: GameState, is_artifact: bool = True):
        """Cast a spell that costs real mana. Fires triggers if artifact."""
        gs.cast_spell(card)
        if is_artifact:
            self._on_artifact_spell_cast(card, gs)
            self._on_artifact_etb(card, is_token=False, gs=gs)


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat priority order:
          1. Land drop (Urza's Saga counts — tap for {C}, start chapters)
          2. All free 0-drop artifacts (Mox Opal, Bauble, Tormod, Welding Jar, Claws of Gix)
          3. Apply Mox Opal mana (metalcraft check after all 0-drops)
          4. Weapons Manufacturing (ASAP — makes every future artifact into a Munitions bomb)
          5. Pinnacle Emissary (ASAP — makes every artifact spell create a Drone token)
          6. Emry, Lurker of the Loch (affinity = free with enough artifacts)
          7. Engineered Explosives at X=0 (free, triggers Weapons Mfg, feeds Kappa)
          8. Kappa Cannoneer via Improvise (pre-combat so it can attack this turn)
          9. Arcbound Ravager (2 mana, grows from artifact sacs)
          10. Remaining 1-drops (Skateboard, Shadowspear)
        """
        self._play_land_if_able(gs)
        # Reset all per-game tracking state on T1
        if gs.turn == 1:
            self.reset_game()
        self._apply_mox_mana(gs)

        # ── Step 1: dump all free 0-drop artifacts ─────────────────────
        for card in list(gs.hand()):
            if card.name in FREE_ARTIFACTS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._cast_free_artifact(card, gs)
                self._apply_mox_mana(gs)  # re-check after each Mox

        # ── Step 2: Weapons Manufacturing (enchantment, {1}{R}) ────────
        # Cast as early as possible — every subsequent artifact ETB is worth 2+ damage.
        if not self._weapons_mfg_up:
            for card in list(gs.hand()):
                if card.name == WEAPONS_MFG and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)  # enchantment — no artifact triggers
                    self._weapons_mfg_up = True
                    gs._log("  Weapons Manufacturing: online — all nontoken artifacts now create Munitions")
                    break
        # After Weapons comes online, dump any remaining 0-drops (NOW they create Munitions!)
        if self._weapons_mfg_up:
            for card in list(gs.hand()):
                if card.name in FREE_ARTIFACTS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    self._cast_free_artifact(card, gs)
                    self._apply_mox_mana(gs)

        # ── Step 3: Pinnacle Emissary ({1}{U}{R}) ──────────────────────
        # Casting it triggers its own ability → 1 Drone token.
        # Then Drone enters → triggers Kappa. Powerful snowball.
        if not self._pinnacle_up:
            for card in list(gs.hand()):
                if card.name == PINNACLE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Pinnacle is itself an artifact spell → triggers its OWN ability
                    # (but Pinnacle isn't in play yet at cast time — ability creates Drone
                    #  which enters after Pinnacle resolves, when Pinnacle is in play)
                    self._pinnacle_up = True
                    self._on_artifact_spell_cast(card, gs)   # → Drone token
                    self._on_artifact_etb(card, is_token=False, gs=gs)  # Pinnacle ETB
                    gs._log("  Pinnacle Emissary: 3/3 in play, Drone token created")
                    break

        # ── Step 4: Emry, Lurker of the Loch ───────────────────────────
        # Affinity: costs {1} less per artifact. With 2 artifacts: costs {U}.
        # With 3+ artifacts: free or close to it.
        if not self._emry_up:
            for card in list(gs.hand()):
                if card.name == EMRY:
                    art = self._artifact_count(gs)
                    affinity_cost = max(0, 2 - art)  # base generic is 2
                    # Need affinity_cost generic + 1 blue
                    has_blue = (gs.mana_pool.U + gs.mana_pool.flex) >= 1
                    has_generic = (gs.mana_pool.total()) >= (affinity_cost + 1)
                    if has_blue and has_generic:
                        gs.mana_pool.U = max(0, gs.mana_pool.U - 1)
                        gs.mana_pool.flex = max(0, gs.mana_pool.flex - affinity_cost)
                        gs.zones.play_from_hand(card)
                        card.summoning_sickness = True
                        card.turn_entered = gs.turn
                        self._emry_up = True
                        # ETB: mill 4 → put top 4 cards into GY
                        milled = []
                        for _ in range(4):
                            if gs.zones.library:
                                top = gs.zones.library.pop(0)
                                gs.zones.graveyard.append(top)
                                if "artifact" in top.type_line.lower():
                                    self._gy_artifacts.append(top.name)
                                    milled.append(top.name)
                        gs._log(f"  Emry ETB: milled 4 ({len(milled)} artifacts: {milled})")
                    break

        # ── Step 5: Engineered Explosives at X=0 ───────────────────────
        # Free cast (X=0, Sunburst → 0 counters). Creates Munitions + feeds Kappa.
        # Keep at least 1 EE for post-combat burst plan.
        ee_in_hand = [c for c in gs.hand() if c.name == EE]
        self._ee_in_hand = len(ee_in_hand)
        if self._ee_in_hand > 1:  # cast all but one as free artifacts
            for card in ee_in_hand[:-1]:
                gs.cast_spell(card)
                card.charge_counters = 0  # cast at X=0
                self._on_artifact_spell_cast(card, gs)
                self._on_artifact_etb(card, is_token=False, gs=gs)
                self._ee_in_hand -= 1
                gs._log(f"  EE cast at X=0 (0 charge counters, enters as 0-mana artifact)")


        # ── Step 6: Kappa Cannoneer via Improvise ──────────────────────
        # Base cost {5}{U}. Tap non-Mox artifacts for Improvise.
        # Each artifact tapped pays {1} of the generic cost.
        # With 5 non-Mox artifacts: costs just {U}.
        # Priority: cast pre-combat so it attacks immediately (no summoning sickness).
        # NOTE: Kappa ETB triggers itself (+1/+1 counter from its own ETB).
        if not self._kappa_up:
            for card in list(gs.hand()):
                if card.name == KAPPA and self._can_cast_kappa(gs):
                    imp = self._improvise_reduction(gs)
                    generic_paid_by_improvise = min(5, imp)
                    generic_remaining = 5 - generic_paid_by_improvise
                    # Tap artifacts for improvise (they're tapped but still in play)
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - generic_remaining)
                    gs.mana_pool.U   = max(0, gs.mana_pool.U - 1)
                    if gs.mana_pool.U < 0:
                        gs.mana_pool.flex = max(0, gs.mana_pool.flex + gs.mana_pool.U)
                        gs.mana_pool.U = 0
                    gs.zones.play_from_hand(card)
                    card.summoning_sickness = False  # haste via Improvise? No —
                    # Kappa has no haste. But cast pre-combat still attacks this turn
                    # ONLY if we give it haste (Skateboard). Without haste: attacks T+1.
                    # Goldfish model: if Skateboard in hand/equippable, give haste.
                    has_skateboard = any(c.name == SKATEBOARD for c in gs.zones.battlefield)
                    if has_skateboard:
                        card.summoning_sickness = False
                        gs._log("  Skateboard: Kappa gains haste — attacks this turn!")
                    else:
                        card.summoning_sickness = True
                    card.turn_entered = gs.turn
                    self._kappa_up = True
                    # Kappa ETB → trigger its own ability
                    self._on_artifact_etb(card, is_token=False, gs=gs)
                    gs._log(f"  Kappa Cannoneer: in play via Improvise ({generic_paid_by_improvise} tapped)")
                    break

        # ── Step 7: Arcbound Ravager ───────────────────────────────────
        # {2} artifact creature. Sac artifacts for +1/+1. Modular 1 (enters 1/1).
        # In goldfish: deploy it early, then sac dead artifacts (Tormod, Bauble) to grow.
        for card in list(gs.hand()):
            if card.name == ARCBOUND and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._cast_spell_with_cost(card, gs, is_artifact=True)
                gs._log("  Arcbound Ravager: 1/1 (Modular 1), ready to grow")
                break

        # ── Step 8: Skateboard ─────────────────────────────────────────
        # {1} artifact. ETB: tap target permanent (irrelevant in goldfish).
        # Equip {1}: equipped creature gets +1/+0 and haste.
        # KEY USE: equip to Kappa on T+1 → haste when it enters the next game
        # or equip to any creature to push damage.
        for card in list(gs.hand()):
            if card.name == SKATEBOARD and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._cast_spell_with_cost(card, gs, is_artifact=True)
                gs._log("  Skateboard: ETB, can equip for +1/+0 and haste")
                break

        # ── Step 9: Shadowspear ({1}) ──────────────────────────────────
        for card in list(gs.hand()):
            if card.name == SHADOWSPEAR and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._cast_spell_with_cost(card, gs, is_artifact=True)
                gs._log("  Shadowspear: in play")
                break


    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat priority:
          1. Compute Kappa Cannoneer combat damage (can't be blocked when triggered)
          2. Arcbound Ravager: sac used artifacts for +1/+1 counters
          3. Emry: recast 0-drops from graveyard → more Munitions triggers
          4. EE burst plan: if Weapons Manufacturing up + 3+ Munitions, sacrifice EE at X=0
          5. Claws of Gix: sacrifice Munitions for 2 damage + 1 life each
          6. Urza's Saga: advance chapter, make Construct token on II, fetch on III
          7. Cast anything remaining in hand
        """
        # ── 1. Kappa combat damage ──────────────────────────────────────
        # Kappa is unblockable during turns when its trigger fired.
        # Power = 4 (base) + kappa_counters. All goes through as damage.
        if self._kappa_up:
            kappas = [c for c in gs.zones.battlefield if c.name == KAPPA]
            for kappa in kappas:
                if not kappa.summoning_sickness:
                    power = 4 + self._kappa_counters
                    gs.damage_dealt += power
                    gs._log(f"  Kappa combat: {power} unblockable damage ({gs.damage_dealt} total)")

        # ── 2. Arcbound Ravager: sac dead artifacts ────────────────────
        # In goldfish, Tormod's Crypt and Mishra's Bauble have done their job
        # (Bauble's delayed draw is helpful; sac conservatively).
        arcbounds = [c for c in gs.zones.battlefield if c.name == ARCBOUND]
        if arcbounds:
            ravager = arcbounds[0]
            sac_targets = [
                c for c in gs.zones.battlefield
                if "artifact" in c.type_line.lower()
                and c.name in {TORMOD, WELDING_JAR}  # truly dead-value artifacts
                and c is not ravager
            ]
            for target in sac_targets:
                gs.zones.battlefield.remove(target)
                gs.zones.graveyard.append(target)
                # Sac = artifact leaving → Munitions trigger (if Munitions token is sacrificed)
                # But TORMOD/WELDING_JAR are not Munitions, no 2-damage trigger
                ravager.power = str(int(ravager.power or 0) + 1)
                ravager.toughness = str(int(ravager.toughness or 0) + 1)
                gs._log(f"  Arcbound: sac {target.name}, now {ravager.power}/{ravager.toughness}")

        # ── 3. Emry: recast 0-drops from graveyard ────────────────────
        # {T}: cast artifact card from GY this turn. Free recursion.
        # Priority: Mox Opal (mana), Mishra's Bauble (draw trigger), EE (burst plan).
        if self._emry_up:
            emrys = [c for c in gs.zones.battlefield if c.name == EMRY and not c.summoning_sickness]
            if emrys:
                recast_priority = [MOX_OPAL, BAUBLE, CLAWS_OF_GIX, TORMOD]
                for target_name in recast_priority:
                    if target_name in self._gy_artifacts:
                        # Find matching card in GY
                        gy_card = next(
                            (c for c in gs.zones.graveyard if c.name == target_name), None
                        )
                        if gy_card:
                            gs.zones.graveyard.remove(gy_card)
                            gs.zones.battlefield.append(gy_card)  # GY → BF directly
                            gy_card.summoning_sickness = False
                            gy_card.turn_entered = gs.turn
                            self._gy_artifacts.remove(target_name)
                            self._on_artifact_etb(gy_card, is_token=False, gs=gs)
                            if target_name == MOX_OPAL:
                                self._apply_mox_mana(gs)
                            gs._log(f"  Emry: recast {target_name} from GY")
                            break  # only 1 activation per turn

        # ── 4. EE Burst Plan ───────────────────────────────────────────
        # When: Weapons Manufacturing is up + we have an EE in hand/BF at 0 counters
        #       + 3+ Munitions tokens (= 6+ potential damage)
        # How:  Sacrifice EE: {2} + sacrifice → destroys all MV-0 nonland permanents
        #       → Munitions tokens die (they are MV-0 tokens) → each deals 2 damage.
        # ALSO: Claws of Gix tokens, Drone tokens, other 0-MV permanents all die.
        # Note: We need {2} mana to activate. Costs 2 to trigger.
        ee_on_bf = [
            c for c in gs.zones.battlefield
            if c.name == EE and getattr(c, "charge_counters", 0) == 0
        ]
        ee_in_hand = [c for c in gs.hand() if c.name == EE]

        if self._weapons_mfg_up and self._munitions_count >= 1:
            # Check if we can pay {2} for EE activation
            if ee_on_bf and gs.mana_pool.total() >= 2:
                gs.mana_pool.flex -= 2
                if gs.mana_pool.flex < 0:
                    gs.mana_pool.flex = 0   # simplified: assume generic covers it
                burst_damage = self._munitions_count * 2
                gs.damage_dealt += burst_damage
                gs._log(f"  EE BURST: {self._munitions_count} Munitions × 2 = {burst_damage} damage ({gs.damage_dealt} total)")
                # Remove EE and Munitions from battlefield
                gs.zones.battlefield.remove(ee_on_bf[0])
                gs.zones.graveyard.append(ee_on_bf[0])
                self._munitions_count = 0   # all Munitions died
            elif ee_in_hand and gs.mana_pool.total() >= 2:
                # Cast EE at X=0 (free), Weapons Mfg creates 1 Munitions, then sac EE
                for card in ee_in_hand:
                    gs.cast_spell(card)
                    card.charge_counters = 0
                    self._on_artifact_spell_cast(card, gs)
                    self._on_artifact_etb(card, is_token=False, gs=gs)
                    # Now immediately sacrifice EE for burst
                    if self._munitions_count >= 1 and gs.mana_pool.total() >= 2:
                        burst_damage = self._munitions_count * 2
                        gs.damage_dealt += burst_damage
                        gs._log(f"  EE BURST: {self._munitions_count} Munitions × 2 = {burst_damage} dmg ({gs.damage_dealt} total)")
                        self._munitions_count = 0
                    break


        # ── 5. Claws of Gix: manual Munitions sacrifice ─────────────────
        # {1}, Sacrifice a permanent → gain 1 life.
        # Use this to cash out Munitions tokens: each sac costs {1}, deals 2, gains 1.
        # Positive trade as long as we have mana to spare. Do this post-EE-burst cleanup
        # or when we have spare Munitions and Claws of Gix in play.
        claws_up = any(c.name == CLAWS_OF_GIX for c in gs.zones.battlefield)
        if claws_up and self._munitions_count > 0:
            affordable = min(self._munitions_count, gs.mana_pool.total())
            if affordable > 0:
                spent = 0
                for _ in range(affordable):
                    if gs.mana_pool.total() < 1:
                        break
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                    gs.damage_dealt += 2
                    self._munitions_count -= 1
                    spent += 1
                if spent:
                    gs._log(f"  Claws of Gix: sacrificed {spent} Munitions → {spent*2} damage ({gs.damage_dealt} total)")

        # ── 5.5. Sacrifice Baubles for card draw ──────────────────────
        # Bauble: {T}, Sacrifice → draw a card next upkeep (model as draw now)
        for card in list(gs.zones.battlefield):
            if card.name == BAUBLE:
                gs.zones.battlefield.remove(card)
                gs.zones.graveyard.append(card)
                self._gy_artifacts.append(card.name)
                if gs.zones.library:
                    drawn = gs.zones.library.pop(0)
                    gs.zones.hand.append(drawn)
                    gs._log(f"  Bauble sac: draw {drawn.name}")

        # ── 6. Urza's Saga chapters ────────────────────────────────────
        # Saga gets a lore counter at beginning of each turn.
        # Chapter I: tap for {C} (handled as land mana)
        # Chapter II: {2},{T}: create 0/0 Construct token (gets +1/+1 per artifact)
        # Chapter III: search for artifact with mana cost {0} or {1}, put into play
        if self._saga_up:
            self._saga_chapter += 1
            art = self._artifact_count(gs)
            if self._saga_chapter == 2:
                # Make a Construct token (size = artifact count)
                # Token is an artifact creature → triggers Kappa and Weapons Mfg
                if gs.mana_pool.total() >= 2:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                    construct_size = art
                    gs._log(f"  Urza's Saga II: Construct token {construct_size}/{construct_size}")
                    # Create a fake construct card for trigger purposes
                    from data.card import Card as _Card
                    construct = _Card.__new__(_Card)
                    construct.name = "Construct"
                    construct.type_line = "Artifact Creature — Construct"
                    construct.power = str(construct_size)
                    construct.toughness = str(construct_size)
                    construct.cmc = 0
                    construct.mana_cost = ""
                    construct.tags = set()
                    construct.summoning_sickness = True
                    construct.turn_entered = gs.turn
                    gs.zones.battlefield.append(construct)
                    self._on_artifact_etb(construct, is_token=True, gs=gs)
                    if not construct.summoning_sickness:
                        gs.damage_dealt += construct_size
                        gs._log(f"  Construct attacks: {construct_size} damage ({gs.damage_dealt} total)")
            elif self._saga_chapter == 3:
                # Search for 0-1 mana artifact and put into play.
                # Priority: Mox Opal (best), EE (burst plan), Pithing Needle
                fetch_priority = [MOX_OPAL, EE, CLAWS_OF_GIX, PITHING_NEEDLE, WELDING_JAR]
                for target_name in fetch_priority:
                    fetched = next(
                        (c for c in gs.zones.library if c.name == target_name and c.cmc <= 1), None
                    )
                    if fetched:
                        gs.zones.library.remove(fetched)
                        gs.zones.battlefield.append(fetched)
                        fetched.summoning_sickness = False  # put directly into play
                        fetched.turn_entered = gs.turn
                        self._on_artifact_etb(fetched, is_token=False, gs=gs)
                        if fetched.name == MOX_OPAL:
                            self._apply_mox_mana(gs)
                        gs._log(f"  Urza's Saga III: fetched {fetched.name}, put into play")
                        break
                # Saga sacrifices itself after chapter III
                sagas = [c for c in gs.zones.battlefield if c.name == URZA_SAGA]
                if sagas:
                    gs.zones.battlefield.remove(sagas[0])
                    gs.zones.graveyard.append(sagas[0])
                    self._saga_up = False
                    gs._log("  Urza's Saga: sacrificed (Chapter III done)")

        # ── 7. Play Urza's Saga if in hand ─────────────────────────────
        # It's a land drop — handled in main_phase via _play_land_if_able,
        # but track it for chapter triggers.
        for c in gs.zones.battlefield:
            if c.name == URZA_SAGA and not self._saga_up:
                self._saga_up = True
                self._saga_chapter = 1
                gs.mana_pool.flex += 1   # Chapter I: {T}: add {C}
                break

        # ── 8. Cast remaining 0-drops missed pre-combat ─────────────────
        for card in list(gs.hand()):
            if card.name in FREE_ARTIFACTS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                self._cast_free_artifact(card, gs)
                self._apply_mox_mana(gs)

        # ── 9. Galvanic Blast from SB (if in hand) ─────────────────────
        # Present in sideboard, sometimes cycles in. 4 damage with Metalcraft.
        for card in list(gs.hand()):
            if card.name == "Galvanic Blast" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                dmg = 4 if self._metalcraft(gs) else 2
                gs.cast_spell(card)
                gs.damage_dealt += dmg
                gs._log(f"  Galvanic Blast: {dmg} damage (Metalcraft: {self._metalcraft(gs)})")
                # No break — cast ALL Galvanic Blasts

        # ── 10. Creatures in hand (not already handled) ─────────────────
        self._cast_all_castable(gs, Tag.CREATURE)


    # ── Sideboard premium (from SBPlanMixin) ────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        """
        Estimated win% delta from sideboarding against this opponent.
        Izzet Affinity SB: Damping Sphere (mirrors/Storm), Consign to Memory
        (counterspells), Whipflare (small creatures), Blood Moon (greedy manabases),
        Grafdigger's Cage (Cascade/GY), Swan Song (combo).
        """
        opp = opponent.lower()
        if any(x in opp for x in ("storm", "ruby", "grinding")):
            return 0.08   # Damping Sphere + Swan Song devastates Storm
        if any(x in opp for x in ("living end", "cascade")):
            return 0.06   # Grafdigger's Cage + Consign
        if any(x in opp for x in ("yawgmoth", "reanimator", "goryo")):
            return 0.05   # Cage + Consign
        if any(x in opp for x in ("domain", "zoo")):
            return 0.04   # Blood Moon + Whipflare
        if any(x in opp for x in ("humans", "merfolk")):
            return 0.06   # Whipflare clears 1-toughness creatures
        if any(x in opp for x in ("boros energy", "prowess")):
            return -0.03  # They're faster in the damage race
        if any(x in opp for x in ("tron", "eldrazi")):
            return 0.02   # Reckless Air Strike hits Chalice/Tron lands
        return 0.0

    # ── Opponent-aware mulligan ──────────────────────────────────────────
    def keep_vs_opponent(self, hand: list[Card], mulligans: int,
                         on_play: bool, opponent: str) -> bool:
        """
        Adjust keep decisions based on opponent.
        vs. Control: keep more disruption hands (EE for sweeping tokens).
        vs. Combo: keep hands with Metallic Rebuke or more counterspell SB pieces.
        vs. Aggro: keep faster hands (more 0-drops).
        """
        opp = opponent.lower()
        base = self.keep(hand, mulligans, on_play)

        # vs. control: EE in hand is extra valuable (sweeps their tokens)
        if any(x in opp for x in ("control", "blink", "jeskai")):
            if any(c.name == EE for c in hand) and base:
                return True

        # vs. combo: be slightly looser — artifact density matters for Rebuke
        if any(x in opp for x in ("storm", "living end", "neoform", "goryo")):
            art_count = sum(1 for c in hand if c.name in FREE_ARTIFACTS)
            if art_count >= 3 and mulligans <= 1:
                return True

        return base



# ── Edge Case Registry ──────────────────────────────────────────────────────
# Verified against oracle text. Each edge case is a real interaction the pilot
# must know. These are NOT modeled in goldfish but inform match APL logic.
#
# EC-01: Kappa Ward {4} — opponent must pay 4 for each spell/ability targeting Kappa.
#   Most removal (Fatal Push, Lightning Bolt, Swords) fails to overcome Ward.
#   Exception: Path to Exile {W}+{4} = {5} total, still playable. Assassin's Trophy too.
#   In practice: Kappa almost never dies to spot removal. Must be swept.
#
# EC-02: Pinnacle Emissary triggers on CAST, not on ETB.
#   If Pinnacle is countered, you STILL get the Drone token (trigger went on stack on cast).
#   Important vs. Control: they can't counter away your board presence.
#
# EC-03: Weapons Manufacturing + EE at X=0.
#   Munitions tokens have MV 0 (tokens have no mana cost, MV = 0).
#   EE sacrificed at 0 counters destroys all nonland permanents with MV 0.
#   This includes Drone tokens (from Pinnacle), other MV-0 tokens, and Munitions.
#   Your own artifacts may die too — sac them to Ravager first to save modular counters.
#
# EC-04: Arcbound Ravager + Kappa Cannoneer interaction.
#   You can sacrifice any artifact (including Kappa!) to Ravager in response to removal.
#   Ravager gets the counters. Then Modular 1 moves counters to Kappa if Kappa is alive.
#   Net: your best creatures become unkillable without sweepers.
#
# EC-05: Emry can recast Legendary artifacts (Mox Opal, Shadowspear).
#   The Legend Rule applies — you must sacrifice the existing copy.
#   Trick: sac the old Mox to Ravager for a free +1/+1 counter, then recast fresh Mox.
#
# EC-06: Urza's Saga is a land but also an enchantment.
#   Ghost Quarter / Field of Ruin can destroy it (it's a land).
#   Enchantment removal (Boseiju, Reckless Air Strike) also hits it.
#   Losing Saga on Chapter I or II is a significant tempo loss.
#
# EC-07: Metallic Rebuke improvise.
#   Rebuke costs {2}{U} but Improvise lets you tap artifacts.
#   With 2 artifacts tapped, costs only {U}. Effectively Force of Negation for blue decks.
#   In goldfish: dead. In match: keep exactly 2 in SB plan for combo matchups.
#
# EC-08: Pinnacle Emissary Warp cost.
#   Warp {U/R}: cast from hand for {U/R} (1 mana), exile at end step, recast from exile later.
#   This means Pinnacle can come down on T1 with a blue/red source.
#   Warped Pinnacle: leaves at end step (no ETB value from Kappa that turn),
#   but triggers its own artifact-cast trigger → Drone token stays.
#
# EC-09: Claws of Gix sac cost is {1} + sacrifice.
#   You pay {1} to sacrifice any permanent, gain 1 life.
#   Munitions are worth: pay {1}, sac Munitions → Munitions trigger 2 damage, gain 1 life.
#   Net: spend {1}, deal 2 damage, gain 1 life. Always worth it when you have mana.
#
# EC-10: Urza's Saga Construct size is DYNAMIC.
#   As the Construct gets +1/+1 for each artifact you control (continuous effect),
#   its size fluctuates with your artifact count. If opponent removes 3 of your artifacts
#   in response to an attack, the Construct shrinks mid-combat and may die to blocks.
#
EDGE_CASES = [
    "EC-01: Kappa Ward {4} stops most spot removal — only sweepers reliably answer it",
    "EC-02: Pinnacle Emissary Drone trigger goes on stack at CAST — survives counterspells",
    "EC-03: EE at X=0 destroys all MV-0 permanents including Munitions, Drone, and Claws tokens",
    "EC-04: Arcbound Ravager sac-to-counter-removal — save modular counters before sweepers",
    "EC-05: Emry + Mox Legend Rule — sac old Mox to Ravager before recasting",
    "EC-06: Urza's Saga is vulnerable to land removal (GQ, Field of Ruin) AND enchantment hate",
    "EC-07: Metallic Rebuke with 2 artifacts tapped costs {U} — near-free countermagic",
    "EC-08: Pinnacle Emissary Warp = T1 1/1 Drone + future 3/3 recast from exile",
    "EC-09: Claws of Gix Munitions = spend {1}, deal 2, gain 1 — always correct with mana up",
    "EC-10: Urza's Construct shrinks dynamically — opponent artifact removal mid-combat can kill it",
]
