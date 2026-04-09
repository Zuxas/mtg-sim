"""
game_state.py — Core game state and turn structure for mtg-sim

Manages the full turn skeleton, zone transitions, mana pool, ETB triggers,
combat triggers (Adeline, Kytheon, Guide of Souls), and energy counters.

Key card interactions modeled:
  - Adeline, Resplendent Cathar: */4 where * = creatures you control.
    Attack trigger: creates 1/1 tapped attacking Human token.
    That token entering attacking triggers each Guide of Souls in play.
  - Guide of Souls: when a creature enters attacking, gain 1 life + get 1 energy.
    Each Guide of Souls triggers independently (2x GoS = 2 life, 2 energy).
    Attack trigger: spend 3 energy to give Guide +2/+2 until EOT.
  - Kytheon, Hero of Akros: flips to Gideon (4/4 indestructible) when 3+ attack.
  - Thalia's Lieutenant: +1/+1 to all Humans on ETB + grows itself.
  - Champion of the Parish: +1/+1 counter whenever a Human enters.
  - Phantasmal Image: copies highest-power creature on board.
  - Aether Vial: +1 counter each upkeep, deploy creatures for free.
  - Delver of Secrets: flips to 3/2 flyer when 6+ instants/sorceries in deck.
  - Dragon's Rage Channeler: upgrades to 3/3 flyer at delirium (4 card types in GY).
"""

from enum import Enum
from data.card import Card, Tag
from engine.mana import ManaPool
from engine.zones import Zones


class Phase(str, Enum):
    UNTAP   = "untap"
    UPKEEP  = "upkeep"
    DRAW    = "draw"
    MAIN1   = "main1"
    COMBAT  = "combat"
    MAIN2   = "main2"
    END     = "end"


class GameState:
    """
    Full game state for one goldfish game.

    Attributes
    ----------
    turn          : current turn number (1-based)
    phase         : current Phase
    damage_dealt  : cumulative damage to opponent
    land_played   : whether a land drop was used this turn
    mana_pool     : ManaPool — floating mana available
    zones         : ZoneManager — all zones (library, hand, battlefield, etc.)
    energy        : energy counters (Guide of Souls mechanic)
    life          : our life total (for lifelink tracking)
    """

    def __init__(self, mainboard: list, on_play: bool = True):
        self.mainboard    = mainboard
        self.on_play      = on_play
        self.turn         = 0
        self.phase        = Phase.UNTAP
        self.damage_dealt = 0
        self.land_played  = False
        self.mana_pool    = ManaPool()
        self.zones        = Zones()
        self.energy       = 0
        self.life         = 20
        self._log_lines   = []
        self._verbose     = False

    def new_game(self):
        """Reset state for a fresh game (called after mulligan)."""
        self.turn         = 0
        self.damage_dealt = 0
        self.land_played  = False
        self.energy       = 0
        self.life         = 20
        self.mana_pool.empty()
        self._log_lines   = []

    def _log(self, msg: str):
        self._log_lines.append(msg)
        if self._verbose:
            print(msg)

    def has_won(self, win_damage: int = 20) -> bool:
        return self.damage_dealt >= win_damage

    def snapshot(self) -> dict:
        """Capture board state as ML feature dict. Called at end of each turn."""
        try:
            bf   = self.zones.battlefield
            hand = self.zones.hand

            def is_land(c):
                return hasattr(c, 'is_land') and callable(c.is_land) and c.is_land()

            def power_of(c):
                try:
                    ep = getattr(c, 'effective_power', None)
                    if callable(ep): return ep()
                    return int(c.power or 0)
                except Exception:
                    return 0

            KEY_CARDS = [
                "Thalia, Guardian of Thraben", "Champion of the Parish",
                "Thalia's Lieutenant",         "Adeline, Resplendent Cathar",
                "Guide of Souls",              "Cavern of Souls",
                "Esper Sentinel",              "Kytheon, Hero of Akros",
            ]

            lands_bf   = [c for c in bf if is_land(c)]
            total_pwr  = min(sum(power_of(c) for c in bf), 40)

            snap = {
                # Core features
                "turn":              self.turn,
                "damage_dealt":      self.damage_dealt,
                "creatures_in_play": len(bf),
                "total_power":       total_pwr,
                "lands_in_play":     len(lands_bf),
                "hand_size":         len(hand),
                "life":              self.life,
                "energy":            getattr(self, 'energy', 0),
                "mulligans":         getattr(self, '_mulligans', 0),
                "hand_creatures":    sum(1 for c in hand if not is_land(c)),
                "hand_lands":        sum(1 for c in hand if is_land(c)),
                # Richer features — milestone damage thresholds
                "dmg_by_t2":         getattr(self, '_dmg_by_t2', 0),
                "dmg_by_t3":         getattr(self, '_dmg_by_t3', 0),
                "dmg_by_t4":         getattr(self, '_dmg_by_t4', 0),
                # Creatures lost (removed by opponent effects)
                "creatures_lost":    getattr(self, '_creatures_lost', 0),
                # Whether we have a T1 play / T2 play (sequencing quality)
                "had_t1_creature":   getattr(self, '_had_t1_creature', 0),
                "had_t2_creature":   getattr(self, '_had_t2_creature', 0),
                # Tempo: average creatures per turn so far
                "avg_creatures_per_turn": round(
                    getattr(self, '_total_creature_turns', 0) / max(1, self.turn), 2),
            }
            for name in KEY_CARDS:
                key = f"has_{name.split(',')[0].lower().replace(' ','_')}"
                snap[key] = int(any(c.name == name for c in bf))
            return snap
        except Exception:
            return {"turn": getattr(self, 'turn', 0),
                    "damage_dealt": getattr(self, 'damage_dealt', 0)}

    # Convenience accessors used by APLs
    def hand(self) -> list:
        return self.zones.hand

    def battlefield(self) -> list:
        return self.zones.battlefield

    def graveyard(self) -> list:
        return self.zones.graveyard


    # -----------------------------------------------------------------------
    # Turn structure
    # -----------------------------------------------------------------------

    def run_turn(self):
        """Begin a new turn: untap, upkeep, draw. Main phases and combat
        are driven by the APL runner (base_apl.run_game) so it can insert
        decisions between phases."""
        self.turn += 1
        self._untap()
        self._upkeep()
        self._draw()
        # Track milestone damage and tempo features for ML
        self._update_ml_trackers()

    def _untap(self):
        self.phase = Phase.UNTAP
        self.land_played = False
        self.mana_pool.empty()
        for card in self.zones.battlefield:
            card.tapped = False
            card.summoning_sickness = False
        self._log(f"T{self.turn} — untap ({len(self.zones.lands_on_battlefield())} lands)")

    def _upkeep(self):
        self.phase = Phase.UPKEEP
        from engine.keywords import KWTag

        for card in self.zones.battlefield:
            # Aether Vial: +1 counter each upkeep
            if card.name == "Aether Vial":
                card.counters += 1
                self._log(f"  Aether Vial: {card.counters} counter(s)")

            # Delver of Secrets: flip to 3/2 flying if enough instants/sorceries
            elif card.name == "Delver of Secrets" and not getattr(card, "_flipped", False):
                spells = sum(
                    1 for c in self.zones.library + self.zones.graveyard
                    if "instant" in c.type_line.lower() or "sorcery" in c.type_line.lower()
                )
                if spells >= 6:
                    card._flipped  = True
                    card.power     = "3"
                    card.toughness = "2"
                    card.type_line = "Creature — Human Insect"
                    card.tags.add(KWTag.FLYING)
                    self._log("  Delver flips → 3/2 flying")

            # Dragon's Rage Channeler: 3/3 flyer at delirium
            elif card.name in ("Dragon's Rage Channeler", "Dragon Rage Channeler") \
                    and not getattr(card, "_delirium", False):
                types_in_gy = {
                    "instant"     if "instant"     in c.type_line.lower() else
                    "sorcery"     if "sorcery"     in c.type_line.lower() else
                    "creature"    if "creature"    in c.type_line.lower() else
                    "land"        if "land"        in c.type_line.lower() else
                    "artifact"    if "artifact"    in c.type_line.lower() else
                    "enchantment" if "enchantment" in c.type_line.lower() else "other"
                    for c in self.zones.graveyard
                }
                if len(types_in_gy) >= 4:
                    card._delirium = True
                    card.power     = "3"
                    card.toughness = "3"
                    card.tags.add(KWTag.FLYING)
                    self._log("  DRC delirium → 3/3 flying")

    def _draw(self):
        self.phase = Phase.DRAW
        if not (self.turn == 1 and self.on_play):
            self.zones.draw(1)


    def run_combat(self):
        """
        Combat phase — called by APL runner between main phases.
        
        Correct turn order: untap → upkeep → draw → MAIN1 → COMBAT → MAIN2 → end
        """
        self.phase = Phase.COMBAT
        self.check_state_based_actions()
        self._do_combat()

    def _do_combat(self):
        """
        Combat with accurate card-specific trigger modeling.

        Trigger ordering (as you'd order them in real Magic):
          1. All creatures declared as attackers
          2. Adeline trigger: create 1/1 tapped attacking Human token
          3. That token entering attacking fires each Guide of Souls:
             gain 1 life + get 1 energy (per Guide, independently)
          4. Guide of Souls attack trigger resolves:
             if 3+ energy, spend 3 to give Guide +2/+2 until EOT
             2x Guide of Souls: each can trigger if you have 6 energy total
          5. Kytheon flips to Gideon (4/4) if 3+ creatures attack
          6. Combat damage step: sum effective_power of all attackers
          7. Guide of Souls flying damage trigger: draw a card
        """
        from engine.keywords import KWTag

        # Refresh static abilities (Adeline */4 scaling)
        self._apply_static_abilities()

        attackers = [
            c for c in self.zones.creatures_on_battlefield()
            if not c.summoning_sickness or KWTag.HASTE in c.tags
        ]
        if not attackers:
            return

        # ── 1. Adeline trigger ─────────────────────────────────────────────
        adeline = next((c for c in attackers
                        if c.name == "Adeline, Resplendent Cathar"), None)
        if adeline:
            token = self._make_token("Human Token", "1", "1", "Creature — Human")
            token.summoning_sickness = False   # enters tapped and attacking
            attackers.append(token)
            self._log("  Adeline: created 1/1 attacking Human token")
            # Note: Guide of Souls trigger fires via _apply_existing_board_etb in _make_token

        # ── 3. Guide of Souls attack trigger: spend 3 energy for +2/+2 ────
        # Each Guide triggers independently — if you have 6 energy and 2 Guides,
        # both can trigger (spend 3 each)
        guides_attacking = [c for c in attackers if c.name == "Guide of Souls"]
        for guide in guides_attacking:
            if self.energy >= 3:
                self.energy -= 3
                guide.counters += 2   # +2/+2 (permanent in goldfish = same effect)
                self._log(f"  Guide of Souls: spent 3 energy → +2/+2 "
                          f"(energy now: {self.energy})")

        # ── Kytheon: flip when HE attacks + 2 other creatures also attack ─
        kytheon = next((c for c in self.zones.battlefield
                        if c.name == "Kytheon, Hero of Akros"
                        and not getattr(c, "_flipped", False)), None)
        kytheon_in_combat = kytheon is not None and kytheon in attackers
        if kytheon_in_combat and len(attackers) >= 3:  # himself + 2 others
            kytheon._flipped   = True
            kytheon.name       = "Gideon, Battle-Forged"
            kytheon.power      = "4"
            kytheon.toughness  = "4"
            kytheon.type_line  = "Legendary Planeswalker — Gideon"
            kytheon.tags.add(KWTag.INDESTRUCTIBLE)
            self._log("  Kytheon flips → Gideon, Battle-Forged (4/4 indestructible)")

        # Already-flipped Gideon attacks as 4/4 indestructible
        gideon = next((c for c in self.zones.battlefield
                       if c.name == "Gideon, Battle-Forged"
                       and getattr(c, "_flipped", False)
                       and not c.summoning_sickness), None)
        if gideon and gideon not in attackers:
            attackers.append(gideon)

        # ── Coppercoat Vanguard: other Humans get +1/+0 during combat ONLY ─
        # Track which cards got boosted so we can undo it after damage
        vanguards = [c for c in self.zones.battlefield
                     if c.name == "Coppercoat Vanguard"]
        coppercoat_boosted = []
        if vanguards:
            bonus = len(vanguards)
            for c in attackers:
                if "human" in c.type_line.lower() and c.name != "Coppercoat Vanguard":
                    c.counters += bonus
                    coppercoat_boosted.append((c, bonus))
            self._log(f"  Coppercoat Vanguard: +{bonus}/+0 to attacking Humans (temporary)")

        # ── Voice of Victory: Mobilize 2 — 2 tapped attacking 1/1 Warriors ─
        # Tokens are sacrificed at beginning of NEXT end step
        for vov in [c for c in attackers if c.name == "Voice of Victory"]:
            for _ in range(2):
                token = self._make_token("Warrior Token", "1", "1", "Creature — Warrior")
                token.summoning_sickness = False
                token._sacrifice_at_eot = True   # mark for end-step sacrifice
                attackers.append(token)
            self._log("  Voice of Victory: Mobilize 2 → 2x 1/1 Warrior tokens (sacrifice at EOT)")

        # ── Mutavault: pay {1} to attack as 2/2 all-types creature ───────
        mutavault = next((c for c in self.zones.battlefield
                          if c.name == "Mutavault"
                          and not c.has(Tag.CREATURE)), None)
        if mutavault and self.mana_pool.total() >= 1:
            self.mana_pool.pay("", 1)
            mutavault.power     = "2"
            mutavault.toughness = "2"
            mutavault.type_line = "Land Creature"
            mutavault.tags.add(Tag.CREATURE)
            mutavault._revert_at_eot = True   # revert to land at end of turn
            mutavault.summoning_sickness = False
            attackers.append(mutavault)
            self._log("  Mutavault: activated → 2/2, attacks (reverts to land at EOT)")

        # ── 5. Combat damage ───────────────────────────────────────────────
        damage = sum(c.effective_power() for c in attackers)
        if damage:
            self.damage_dealt += damage
            self._log(f"  Attack: {damage} dmg ({self.damage_dealt} total) "
                      f"[{len(attackers)} attackers]")

        # ── Post-damage cleanup ────────────────────────────────────────────
        # Remove temporary Coppercoat Vanguard bonus
        for card, bonus in coppercoat_boosted:
            card.counters -= bonus

        # ── Guide of Souls flying damage trigger: draw a card ─────────────
        flying_attackers = [c for c in attackers
                            if KWTag.FLYING in c.tags and c.effective_power() > 0]
        if flying_attackers:
            drawn = self.zones.draw(1)
            if drawn:
                self._log(f"  Guide of Souls flying trigger: drew {drawn[0].name}")

    def _end(self):
        self.phase = Phase.END
        self.mana_pool.empty()

        # Sacrifice Voice of Victory Warrior tokens (Mobilize — sac at EOT)
        to_sacrifice = [c for c in self.zones.battlefield
                        if getattr(c, "_sacrifice_at_eot", False)]
        for card in to_sacrifice:
            self.zones.battlefield.remove(card)
            self.zones.graveyard.append(card)
            self._log(f"  EOT: sacrificed {card.name} (Mobilize)")

        # Revert Mutavault back to a land
        for card in self.zones.battlefield:
            if card.name == "Mutavault" and getattr(card, "_revert_at_eot", False):
                card.power      = None
                card.toughness  = None
                card.type_line  = "Token Land"
                card.tags.discard(Tag.CREATURE)
                card._revert_at_eot = False
                self._log("  EOT: Mutavault reverts to land")


    def _update_ml_trackers(self):
        """Track milestone features for richer ML training data."""
        bf = self.zones.battlefield

        # Milestone damage snapshots
        if self.turn == 2:
            self._dmg_by_t2 = self.damage_dealt
        elif self.turn == 3:
            self._dmg_by_t3 = self.damage_dealt
        elif self.turn == 4:
            self._dmg_by_t4 = self.damage_dealt

        # Did we have a creature by T1/T2?
        creatures_now = sum(1 for c in bf
                            if hasattr(c, 'has') and not
                            (hasattr(c, 'is_land') and c.is_land()))
        if self.turn == 1 and creatures_now >= 1:
            self._had_t1_creature = 1
        if self.turn == 2 and creatures_now >= 1:
            self._had_t2_creature = 1

        # Cumulative creature-turns (for avg_creatures_per_turn)
        if not hasattr(self, '_total_creature_turns'):
            self._total_creature_turns = 0
        self._total_creature_turns += creatures_now

    def _make_token(self, name: str, power: str, toughness: str,
                    type_line: str) -> Card:
        """Create a token, place it on the battlefield, fire its ETB triggers."""
        token = Card(
            name=name, mana_cost="", cmc=0,
            type_line=type_line, oracle_text="",
            power=power, toughness=toughness, colors=[],
        )
        token.tags.add(Tag.CREATURE)
        token.summoning_sickness = True
        token.turn_entered = self.turn
        self.zones.battlefield.append(token)
        self._fire_etb_triggers(token)
        return token

    def _apply_static_abilities(self):
        """
        Continuous/static effects that scale with board state.
        Called before combat and after every ETB.

        Adeline, Resplendent Cathar is */4:
          power  = number of creatures you control (dynamic)
          toughness = 4 (fixed — she is NOT */* )
        The deck has ways to add counters but that's external to her text.
        """
        bf = self.zones.battlefield
        creature_count = sum(1 for c in bf if c.has(Tag.CREATURE))
        for card in bf:
            if card.name == "Adeline, Resplendent Cathar":
                card.power     = str(max(1, creature_count))
                card.toughness = "4"   # fixed toughness

    def check_state_based_actions(self):
        """
        State-based actions (Phase 0E) — checked whenever a player would
        receive priority. In practice, after each spell resolves and at
        the start of each phase.

        SBAs implemented:
          1. Creature with effective toughness <= 0 → graveyard
          2. Legend rule: if 2+ legendary permanents share a name, keep newest
          3. Player at 0 or less life → loses (tracked externally)
        """
        changed = True
        while changed:
            changed = False

            # 1. Zero toughness
            for card in list(self.zones.battlefield):
                if card.has(Tag.CREATURE) and card.effective_toughness() <= 0:
                    self.zones.battlefield.remove(card)
                    self.zones.graveyard.append(card)
                    self._log(f"  SBA: {card.name} dies (0 toughness)")
                    changed = True

            # 2. Legend rule
            seen_legends = {}
            for card in list(self.zones.battlefield):
                if "legendary" in card.type_line.lower():
                    if card.name in seen_legends:
                        # Keep the newer one (higher turn_entered, or later in list)
                        old = seen_legends[card.name]
                        victim = old if old.turn_entered <= card.turn_entered else card
                        if victim in self.zones.battlefield:
                            self.zones.battlefield.remove(victim)
                            self.zones.graveyard.append(victim)
                            self._log(f"  SBA: Legend rule — sacrificed {victim.name}")
                            changed = True
                        seen_legends[card.name] = card
                    else:
                        seen_legends[card.name] = card

    # -----------------------------------------------------------------------
    # APL-facing actions
    # -----------------------------------------------------------------------

    def tap_lands(self):
        """Tap all untapped lands for mana. Skips already-tapped lands."""
        for land in self.zones.lands_on_battlefield():
            if not land.tapped:
                land.tapped = True
                self.mana_pool.add_land(land.type_line, land.name)

    # -------------------------------------------------------------------
    # Land classification helpers (Phase 0B)
    # -------------------------------------------------------------------

    # Fetch lands: sacrifice → search library for a land → put into play
    FETCH_LANDS = {
        "flooded strand", "polluted delta", "bloodstained mire",
        "windswept heath", "wooded foothills", "scalding tarn",
        "misty rainforest", "verdant catacombs", "arid mesa",
        "marsh flats", "prismatic vista", "fabled passage",
    }

    # Fetch land → which basic land types it can find
    FETCH_TARGETS = {
        "flooded strand":    {"plains", "island"},
        "polluted delta":    {"island", "swamp"},
        "bloodstained mire": {"swamp", "mountain"},
        "windswept heath":   {"forest", "plains"},
        "wooded foothills":  {"mountain", "forest"},
        "scalding tarn":     {"island", "mountain"},
        "misty rainforest":  {"forest", "island"},
        "verdant catacombs": {"swamp", "forest"},
        "arid mesa":         {"mountain", "plains"},
        "marsh flats":       {"plains", "swamp"},
        "prismatic vista":   None,   # any basic
        "fabled passage":    None,   # any basic
    }

    # Shock lands: pay 2 life or enter tapped
    SHOCK_LANDS = {
        "hallowed fountain", "watery grave", "blood crypt",
        "stomping ground", "temple garden", "steam vents",
        "overgrown tomb", "sacred foundry", "breeding pool",
        "godless shrine",
    }

    # Lands that always enter tapped
    TAPLANDS = {
        "temple of silence", "temple of deceit", "temple of malice",
        "temple of abandon", "temple of plenty", "temple of mystery",
        "temple of triumph", "temple of enlightenment", "temple of epiphany",
        "temple of malady",
        # Gain lands
        "scoured barrens", "tranquil cove", "bloodfell caves",
        "rugged highlands", "blossoming sands", "dismal backwater",
        "swiftwater cliffs", "jungle hollow", "wind-scarred crag",
        "thornwood falls",
        # Bridges
        "razortide bridge", "mistvault bridge", "drossforge bridge",
        "slagwoods bridge", "thornglint bridge", "goldmire bridge",
        "silverbluff bridge", "tanglepool bridge", "rustvale bridge",
        "darkmoss bridge",
    }

    # Fast lands: enter untapped if you control ≤2 other lands
    FAST_LANDS = {
        "seachrome coast", "darkslick shores", "blackcleave cliffs",
        "copperline gorge", "razorverge thicket", "spirebluff canal",
        "blooming marsh", "concealed courtyard", "inspiring vantage",
        "botanical sanctum",
    }

    def _is_fetch_land(self, card: Card) -> bool:
        return card.name.lower() in self.FETCH_LANDS

    def _enters_tapped(self, card: Card) -> bool:
        """Determine if a land enters the battlefield tapped."""
        name = card.name.lower()

        # Always-tapped lands
        if name in self.TAPLANDS:
            return True

        # Elegant Parlor — always enters tapped (surveil land)
        if name == "elegant parlor":
            return True

        # Shock lands: in goldfish, always pay 2 life (perfect player wants speed)
        if name in self.SHOCK_LANDS:
            return False  # pay 2 life, enter untapped

        # Fast lands: untapped if ≤2 other lands
        if name in self.FAST_LANDS:
            other_lands = self.zones.count_lands_in_play() - 1  # exclude self
            return other_lands > 2

        # Arena of Glory: enters tapped unless you control a Mountain
        if name == "arena of glory":
            has_mountain = any("mountain" in c.type_line.lower()
                              for c in self.zones.lands_on_battlefield())
            return not has_mountain

        # Dalkovan Encampment: enters tapped unless you control a Swamp or Mountain
        if name == "dalkovan encampment":
            has_swamp_or_mountain = any(
                "swamp" in c.type_line.lower() or "mountain" in c.type_line.lower()
                for c in self.zones.lands_on_battlefield())
            return not has_swamp_or_mountain

        # Fabled Passage: tapped if <4 lands
        if name == "fabled passage":
            return self.zones.count_lands_in_play() < 4

        return False  # default: untapped

    def _resolve_fetch(self, card: Card) -> bool:
        """
        Resolve a fetch land: sacrifice it, search library for a matching
        land, put that land onto the battlefield.
        Returns True if a land was found and played.
        """
        name = card.name.lower()
        targets = self.FETCH_TARGETS.get(name)

        # Find best matching land in library
        best = None
        for lib_card in self.zones.library:
            if not lib_card.is_land():
                continue
            t = lib_card.type_line.lower()
            if targets is None:
                # Prismatic Vista / Fabled Passage: any basic
                if "basic" in t:
                    best = lib_card
                    break
            else:
                # Named fetch: find land with matching basic type
                for basic_type in targets:
                    if basic_type in t:
                        best = lib_card
                        break
                if best:
                    break

        if not best:
            return False

        # Sacrifice the fetch (already on battlefield from play_land)
        self.zones.battlefield.remove(card)
        self.zones.graveyard.append(card)

        # Put found land onto battlefield from library
        self.zones.library.remove(best)
        self.zones.battlefield.append(best)
        best.turn_entered = self.turn

        # Most fetched lands enter untapped (except Fabled Passage w/ <4 lands)
        enters_tapped = self._enters_tapped(best)
        if not enters_tapped:
            best.tapped = True  # tap immediately for mana
            self.mana_pool.add_land(best.type_line, best.name)
        else:
            best.tapped = True  # enters tapped, no mana this turn

        self.zones.shuffle()
        self._log(f"  Fetch: {card.name} → {best.name}"
                  f"{' (tapped)' if enters_tapped else ''}")
        return True

    def play_land(self, card: Card) -> bool:
        if self.land_played or card not in self.zones.hand or not card.is_land():
            return False
        self.zones.play_from_hand(card)
        self.land_played = True
        card.turn_entered = self.turn

        # Fetch lands: sacrifice and search
        if self._is_fetch_land(card):
            self._resolve_fetch(card)
            return True

        # Shock lands: pay 2 life in goldfish (perfect player wants speed)
        if card.name.lower() in self.SHOCK_LANDS:
            self.life -= 2
            self._log(f"  Shock: {card.name} (pay 2 life, life={self.life})")

        # Check if land enters tapped
        if self._enters_tapped(card):
            card.tapped = True  # enters tapped, no mana this turn
            self._log(f"  Land: {card.name} (enters tapped, "
                      f"{self.zones.count_lands_in_play()} total)")
        else:
            card.tapped = True  # tap immediately for mana
            self.mana_pool.add_land(card.type_line, card.name)
            self._log(f"  Land: {card.name} "
                      f"({self.zones.count_lands_in_play()} total)")
        return True

    def cast_spell(self, card: Card) -> bool:
        from engine.keywords import KWTag
        if card not in self.zones.hand or card.is_land():
            return False
        if not self.mana_pool.can_cast(card.mana_cost, card.cmc):
            return False
        self.mana_pool.pay(card.mana_cost, card.cmc)
        if card.has(Tag.INSTANT) or card.has(Tag.SORCERY):
            self.zones.cast_to_graveyard(card)
        else:
            self.zones.play_from_hand(card)
            card.turn_entered = self.turn
            if card.has(Tag.CREATURE) and KWTag.HASTE not in card.tags:
                card.summoning_sickness = True
            self._fire_etb_triggers(card)
        self._log(f"  Cast: {card.name} (CMC {card.cmc:.0f}, pool left: {self.mana_pool.total()})")
        self.check_state_based_actions()
        return True

    def put_via_vial(self, card: Card, vial: Card) -> bool:
        from engine.keywords import KWTag
        if card not in self.zones.hand or not card.has(Tag.CREATURE):
            return False
        if vial not in self.zones.battlefield or vial.name != "Aether Vial":
            return False
        if int(vial.counters) != int(card.cmc):
            return False
        self.zones.play_from_hand(card)
        card.turn_entered = self.turn
        if KWTag.HASTE not in card.tags:
            card.summoning_sickness = True
        self._fire_etb_triggers(card)
        self._log(f"  Vial ({vial.counters}): {card.name}")
        self.check_state_based_actions()
        return True

    def vial_in_play(self):
        for c in self.zones.battlefield:
            if c.name == "Aether Vial":
                return c
        return None

    def castable_via_vial(self) -> list:
        vial = self.vial_in_play()
        if not vial:
            return []
        return [c for c in self.zones.hand
                if c.has(Tag.CREATURE) and int(c.cmc) == int(vial.counters)]


    # -----------------------------------------------------------------------
    # ETB trigger system
    # -----------------------------------------------------------------------

    def _fire_etb_triggers(self, entered: Card, _depth: int = 0):
        """Fire ETB triggers. _depth prevents infinite recursion from clones."""
        if _depth > 2:
            return
        self._apply_existing_board_etb(entered)
        self._apply_entering_etb(entered, _depth=_depth)
        self._apply_static_abilities()

    def _apply_existing_board_etb(self, entered: Card):
        """Existing permanents react to something new entering."""
        if not entered.has(Tag.CREATURE):
            return
        is_human = "human" in entered.type_line.lower()
        for perm in self.zones.battlefield:
            if perm is entered:
                continue
            # Champion of the Parish: +1/+1 when a Human enters
            if perm.name == "Champion of the Parish" and is_human:
                perm.counters += 1
                self._log(f"    Champion: +1 → {perm.effective_power()}/{perm.effective_toughness()}")
            # Thalia's Lieutenant: +1/+1 when any Human enters (her static trigger)
            if perm.name == "Thalia's Lieutenant" and is_human:
                perm.counters += 1
                self._log(f"    Lieutenant: +1 → {perm.effective_power()}/{perm.effective_toughness()}")
            # Guide of Souls: whenever ANOTHER creature enters, gain 1 life + 1 energy
            if perm.name == "Guide of Souls":
                self.life   += 1
                self.energy += 1
                self._log(f"    Guide of Souls: creature entered → +1 life ({self.life}), +1 energy ({self.energy})")

    def _apply_entering_etb(self, entered: Card, _depth: int = 0):
        """The entering card fires its own ETB effects."""
        n = entered.name
        bf = self.zones.battlefield

        # Phantasmal Image: copy the highest-power creature in play
        if n == "Phantasmal Image":
            targets = [c for c in bf if c is not entered and c.has(Tag.CREATURE)]
            if targets:
                best = max(targets, key=lambda c: (c.effective_power(), c.cmc))
                entered.copying    = best.name
                entered.type_line  = best.type_line
                entered.oracle_text= best.oracle_text
                entered.power      = best.power
                entered.toughness  = best.toughness
                entered.colors     = list(best.colors)
                entered.tags       = set(best.tags)
                entered.counters   = best.counters
                self._log(f"    Image copies {best.name} "
                          f"({best.effective_power()}/{best.effective_toughness()})")
                self._fire_etb_triggers(entered, _depth=_depth + 1)

        # Thalia's Lieutenant: +1/+1 to all other Humans; +1/+1 per other Human
        elif n == "Thalia's Lieutenant":
            human_count = 0
            for perm in bf:
                if perm is entered:
                    continue
                if perm.has(Tag.CREATURE) and "human" in perm.type_line.lower():
                    perm.counters += 1
                    human_count   += 1
            entered.counters += human_count
            if human_count:
                self._log(f"    Lieutenant ETB: +1/+1 to {human_count} Humans, "
                          f"self {entered.effective_power()}/{entered.effective_toughness()}")

        # Urdnan, Dromoka Warrior: ETB puts +1/+1 counter on target creature
        # Target the biggest creature on board for maximum value
        elif n == "Urdnan, Dromoka Warrior":
            targets = [c for c in bf if c is not entered and c.has(Tag.CREATURE)]
            if targets:
                best = max(targets, key=lambda c: c.effective_power())
                best.counters += 1
                self._log(f"    Urdnan ETB: +1/+1 on {best.name} "
                          f"→ {best.effective_power()}/{best.effective_toughness()}")

# ---------------------------------------------------------------------------
# GameResult — output of one goldfish game, returned by BaseAPL.run_game()
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field as dc_field

@dataclass
class GameResult:
    won:          bool       = False
    kill_turn:    int        = 0
    turn_count:   int        = 0
    mulligans:    int        = 0
    opening_hand: list       = dc_field(default_factory=list)
    lands_played: list       = dc_field(default_factory=list)
    spells_cast:  list       = dc_field(default_factory=list)
    turn_snapshots: list     = dc_field(default_factory=list)  # per-turn board state dicts
