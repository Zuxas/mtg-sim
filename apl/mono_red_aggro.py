"""
mono_red_aggro.py — APL for Modern Burn (Boros Burn; full rewrite, April 2026)

VERIFIED card interactions (CardDB, deck: mono_red_aggro_modern.txt):

  Goblin Guide [{R}] — 2/2 Haste.
    Attack trigger: defending player reveals top card. If land → they put it in hand.
    Goldfish: pure 2 damage per turn once in play. Land gift is irrelevant (no opponent).

  Monastery Swiftspear [{R}] — 1/2 Haste. Prowess.
    Prowess: each noncreature spell cast → +1/+1 until EOT.
    KEY: Casting Lightning Bolt pre-combat = Swiftspear attacks as 2/3 (or bigger).
    With 3 spells pre-combat: attacks as 4/5.

  Lava Spike [{R}] — Sorcery. 3 damage to player/PW.
  Lightning Bolt [{R}] — Instant. 3 damage to any target.
  Boros Charm [{R}{W}] — Choose one: 4 to player, or indestructible, or double strike.
    Goldfish: always mode 1 (4 damage).

  Rift Bolt [{2}{R}] or Suspend {R}.
    Suspend {R}: exile with time counter at start of turn → T+1 it fires for free.
    Cast normally: 3R for 3 damage (expensive, rarely done).
    KEY: T1 suspend → T2 3 free damage. Model as suspend on T1 always.

  Skewer the Critics [{2}{R}] or Spectacle {R}.
    Spectacle {R}: cast for {R} if opponent lost life this turn.
    After ANY bolt/spike = spectacle active. Net: {R} for 3 damage.
    Without spectacle: {2}{R} = expensive, usually not worth it.

  Searing Blaze [{R}{R}] — 1 damage to player + 1 to creature.
    Landfall: if a land entered this turn → 3+3 instead.
    With fetch land activated: landfall triggers → 3 damage to face.
    Goldfish without fetch: only 1 damage to face (the other 1 hits a creature = irrelevant).
    With fetch on same turn: 3 damage.
    NOTE: In this deck, 10 fetch lands → landfall frequently active.

  Lightning Helix [{R}{W}] — 3 damage + gain 3 life.
    In goldfish: 3 damage to face. Life gain irrelevant for kill calculation.

  Skullcrack [{1}{R}] — 3 damage to player. Opponents can't gain life this turn.
    Goldfish: 3 damage to face. Life prevention irrelevant.

  Roiling Vortex [{1}{R}] — Enchantment.
    Upkeep: 1 damage to each player.
    Free spells trigger: 5 damage to that player.
    {R}: opponents can't gain life.
    Goldfish: 1 damage per upkeep (starting your next turn). Cast ASAP.

  KILL MATH:
    T1: Guide (haste) = 2 damage. +Bolt/Spike = 5 total.
    T2: Guide attacks (2), Swiftspear (plays bolt pre-combat, attacks as 2) = 4 from creatures.
        + 2-3 more spells = 6-9 more damage. Running total: ~15.
    T3: Final burn spells close out 20. Average kill: T3.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from data.card import Card, Tag
from engine.game_state import GameState

# ── Constants ──────────────────────────────────────────────────────────────────
GUIDE      = "Goblin Guide"
SWIFTSPEAR = "Monastery Swiftspear"
BOLT       = "Lightning Bolt"
SPIKE      = "Lava Spike"
BOROS      = "Boros Charm"
RIFT       = "Rift Bolt"
SKEWER     = "Skewer the Critics"
BLAZE      = "Searing Blaze"
HELIX      = "Lightning Helix"
SKULLCRACK = "Skullcrack"
VORTEX     = "Roiling Vortex"

HASTE_CREATURES = {GUIDE, SWIFTSPEAR}
BOLT_SPELLS     = {BOLT, SPIKE, BOROS, SKEWER, HELIX, SKULLCRACK}
ALL_BURN        = {BOLT, SPIKE, BOROS, SKEWER, HELIX, SKULLCRACK, BLAZE, RIFT}


class MonoRedAggroAPL(SBPlanMixin, BaseAPL):
    """
    Goldfish APL for Modern Burn / Boros Burn (2026).

    Pure goldfish kill plan:
      1. T1: land + Goblin Guide (haste, 2 damage) + bolt (3 damage) = 5 damage T1.
      2. T2: creatures attack + more bolts. Rift Bolt fires from suspend.
      3. T3: final burn to close out 20.

    Priority: maximize damage per mana. Every spell targets the opponent's face.
    Swiftspear pre-combat spells first = bigger attacks.
    Rift Bolt always suspended on T1 if possible.
    Skewer always uses spectacle cost ({R}) after any life loss.
    Searing Blaze gets landfall bonus from fetch lands.
    """

    name = "Burn"
    win_condition_damage = 20
    max_turns = 6

    # ── Per-game state ─────────────────────────────────────────────────
    _swiftspear_power   = 1    # 1/2 base, +1 per noncreature spell this turn
    _prowess_triggers   = 0    # noncreature spells cast this turn
    _rift_suspended     = False  # Rift Bolt on suspend (will fire next turn)
    _life_lost_this_turn = False  # spectacle condition
    _vortex_up          = False  # Roiling Vortex on battlefield
    _fetch_used_this_turn = False  # landfall for Searing Blaze

    def reset_game(self):
        self._swiftspear_power    = 1
        self._prowess_triggers    = 0
        self._rift_suspended      = False
        self._life_lost_this_turn = False
        self._vortex_up           = False
        self._fetch_used_this_turn = False

    def reset_turn(self):
        self._swiftspear_power    = 1
        self._prowess_triggers    = 0
        self._life_lost_this_turn = False
        self._fetch_used_this_turn = False

    # ── Mulligan ────────────────────────────────────────────────────────
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """
        Burn mulligan: needs 2-3 lands and a mix of creatures + spells.
          - Must have at least 1 land (or a fetch)
          - Want at least 1 haste creature
          - Want at least 2 burn spells
          - 1-land hands: keep only with multiple 1-mana spells on play
          - 4+ land hands: mull (too flooded)
        """
        if len(hand) <= 4:
            return True

        lands     = [c for c in hand if c.is_land()]
        creatures = [c for c in hand if c.name in HASTE_CREATURES]
        burn      = [c for c in hand if c.name in ALL_BURN]
        ones      = [c for c in hand if c.cmc == 1 and not c.is_land()]

        if not lands: return False
        if len(lands) >= 4: return False

        # Perfect hand: 2 lands + creature + 3+ spells
        if len(lands) >= 2 and creatures and len(burn) >= 3: return True

        # 1-land hand on play: keep if 3+ one-drops
        if len(lands) == 1 and on_play and len(ones) >= 3: return True

        # 2-3 lands + enough burn
        if len(lands) >= 2 and len(burn) >= 2: return True

        return mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority:
          1. Excess lands past 2 (Burn wants exactly 2, sometimes 3)
          2. Roiling Vortex (slow, 2 mana enchantment — bottom in aggressive hands)
          3. Skullcrack (2 mana, situational — worse than 1-mana bolts)
          4. Highest CMC burn spells
        """
        to_bottom: list[Card] = []
        lands = [c for c in hand if c.is_land()]

        for c in lands[2:]:
            if len(to_bottom) < n: to_bottom.append(c)

        # Bottom slow cards in aggressive 5-card hands
        if mulligans_taken := max(0, 7 - len(hand)):
            for c in hand:
                if len(to_bottom) >= n: break
                if c.name in {VORTEX, SKULLCRACK} and c not in to_bottom:
                    to_bottom.append(c)

        # Bottom highest CMC non-lands
        rest = sorted(
            [c for c in hand if not c.is_land() and c not in to_bottom],
            key=lambda c: -c.cmc
        )
        for c in rest:
            if len(to_bottom) >= n: break
            to_bottom.append(c)

        return to_bottom[:n]

    # ── Helpers ─────────────────────────────────────────────────────────
    def _burn_face(self, card: Card, damage: int, gs: GameState, label: str = ""):
        """Cast a burn spell targeting the face. Track prowess + spectacle."""
        gs.cast_spell(card)
        gs.damage_dealt += damage
        if not card.has(Tag.CREATURE):
            self._prowess_triggers += 1
            self._life_lost_this_turn = True
        label = label or card.name
        gs._log(f"  {label}: {damage} damage ({gs.damage_dealt} total)")

    def _count_swiftspears(self, gs: GameState) -> int:
        return sum(1 for c in gs.zones.battlefield if c.name == SWIFTSPEAR)


    # ── Main Phase (pre-combat) ──────────────────────────────────────────
    def main_phase(self, gs: GameState):
        """
        Pre-combat priority for Burn:
          1. Reset on T1
          2. Land drop (fetch if available — activates Searing Blaze landfall)
          3. Roiling Vortex (play early so it ticks each upkeep)
          4. Rift Bolt: suspend on T1/T2 for free 3 damage next turn
          5. Haste creatures (attack this turn)
          6. Pre-combat burn spells (trigger Swiftspear prowess before attack)
             Priority: Bolt > Spike > Skewer (spectacle) > Helix > Boros Charm
        """
        if gs.turn == 1:
            self.reset_game()
        self.reset_turn()

        # Rift Bolt fires from suspend at start of upkeep if suspended last turn
        # Model: at turn start, if rift was suspended, add 3 damage
        if self._rift_suspended:
            gs.damage_dealt += 3
            self._rift_suspended = False
            self._life_lost_this_turn = True
            gs._log(f"  Rift Bolt (suspend fires): 3 damage ({gs.damage_dealt} total)")

        # Vortex upkeep damage (both players — in goldfish just 1 to face)
        if self._vortex_up:
            gs.damage_dealt += 1
            self._life_lost_this_turn = True
            gs._log(f"  Roiling Vortex upkeep: 1 damage ({gs.damage_dealt} total)")

        # ── 1. Land drop ────────────────────────────────────────────────
        if not gs.land_played:
            # Prefer fetch lands (activate landfall for Searing Blaze)
            fetch_names = {"Arid Mesa", "Bloodstained Mire", "Sunbaked Canyon", "Fiery Islet"}
            for c in list(gs.hand()):
                if c.is_land() and c.name in fetch_names:
                    gs.zones.play_from_hand(c)
                    gs.mana_pool.flex += 1
                    self._fetch_used_this_turn = True
                    gs._log(f"  Land: {c.name} (fetch → landfall active)")
                    break
            if not gs.land_played:
                self._play_land_if_able(gs)

        # ── 2. Roiling Vortex ({1}{R} = 2 mana) ───────────────────────
        if not self._vortex_up:
            for card in list(gs.hand()):
                if card.name == VORTEX and gs.mana_pool.total() >= 2:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 2)
                    gs.cast_spell(card)
                    self._vortex_up = True
                    gs._log("  Roiling Vortex: online (1 damage/upkeep, free spells = 5 dmg)")
                    break

        # ── 3. Rift Bolt suspend ({R}) ──────────────────────────────────
        # Suspend on T1 or T2 so it fires free next turn. Better than 3R hardcast.
        if not self._rift_suspended and gs.turn <= 2:
            for card in list(gs.hand()):
                if card.name == RIFT and gs.mana_pool.total() >= 1:
                    gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                    gs.zones.hand.remove(card)
                    gs.zones.exile.append(card)
                    self._rift_suspended = True
                    gs._log("  Rift Bolt: suspended for {R} (fires free next turn)")
                    break

        # ── 4. Haste creatures (attack this turn) ──────────────────────
        for name in [GUIDE, SWIFTSPEAR]:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    card.summoning_sickness = False  # haste
                    card.turn_entered = gs.turn
                    if name == SWIFTSPEAR:
                        self._swiftspear_power = 1  # reset each cast
                    gs._log(f"  {name}: haste, attacks this turn")
                    break

        # ── 5. Pre-combat burn (triggers Swiftspear prowess) ────────────
        swiftspears = self._count_swiftspears(gs)

        # Cast burn spells in this order: cheapest / most damage first
        burn_priority = [
            (BOLT,       1, 3),   # {R}, 3 damage
            (SPIKE,      1, 3),   # {R}, 3 damage
            (SKEWER,     1, 3),   # {R} spectacle (only if life lost)
            (HELIX,      2, 3),   # {R}{W}, 3 damage
            (BOROS,      2, 4),   # {R}{W}, 4 damage
            (BLAZE,      2, 3 if self._fetch_used_this_turn else 1),  # landfall or not
            (SKULLCRACK, 2, 3),   # {1}{R}, 3 damage
            (RIFT,       3, 3),   # hardcast if suspend already used
        ]

        for spell_name, mana_cost, damage in burn_priority:
            for card in list(gs.hand()):
                if card.name != spell_name:
                    continue
                # Spectacle check for Skewer
                if spell_name == SKEWER and not self._life_lost_this_turn:
                    continue  # Skip without spectacle (3R is too expensive)
                if gs.mana_pool.total() < mana_cost:
                    continue
                gs.mana_pool.flex = max(0, gs.mana_pool.flex - mana_cost)
                self._burn_face(card, damage, gs)
                # Prowess update for Swiftspears
                if swiftspears > 0:
                    self._swiftspear_power += 1
                break  # only cast one of each priority per pre-combat pass

        # Second pass: cast more burn if mana remains
        for card in list(gs.hand()):
            if card.name in ALL_BURN and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                if card.name == SKEWER and not self._life_lost_this_turn:
                    continue
                self._burn_face(card, 3, gs)
                if swiftspears > 0:
                    self._swiftspear_power += 1

    # ── Main Phase 2 (post-combat) ───────────────────────────────────────
    def main_phase2(self, gs: GameState):
        """
        Post-combat:
          1. Compute creature attack damage
          2. Cast remaining burn with leftover mana
        """
        # ── 1. Creature attacks ─────────────────────────────────────────
        for c in gs.zones.battlefield:
            if getattr(c, "summoning_sickness", True): continue
            if not c.has(Tag.CREATURE): continue
            try:
                power = int(c.power or 0)
            except (ValueError, TypeError):
                power = 0

            if c.name == GUIDE:
                gs.damage_dealt += 2
                gs._log(f"  Goblin Guide attacks: 2 ({gs.damage_dealt} total)")
            elif c.name == SWIFTSPEAR:
                # Swiftspear power = 1 (base) + prowess triggers from pre-combat spells
                atk = 1 + self._prowess_triggers
                gs.damage_dealt += atk
                gs._log(f"  Swiftspear attacks: {atk} (+{self._prowess_triggers} prowess) ({gs.damage_dealt} total)")

        # ── 2. Post-combat burn ──────────────────────────────────────────
        # Spectacle now active (opponent took combat damage)
        self._life_lost_this_turn = True

        for card in list(gs.hand()):
            if card.name not in ALL_BURN:
                continue
            cost = card.cmc
            if card.name == SKEWER:
                cost = 1  # spectacle cost
            if card.name == RIFT and not self._rift_suspended:
                cost = 3  # hardcast if needed
            if gs.mana_pool.total() < cost:
                continue

            dmg = 4 if card.name == BOROS else 3
            if card.name == BLAZE:
                dmg = 3 if self._fetch_used_this_turn else 1
            gs.mana_pool.flex = max(0, gs.mana_pool.flex - cost)
            self._burn_face(card, dmg, gs)

    # ── Sideboard premium ────────────────────────────────────────────────
    def sideboard_premium(self, opponent: str) -> float:
        opp = opponent.lower()
        if any(x in opp for x in ("living end", "cascade")):
            return -0.04  # Lifelink + life gain is problematic
        if any(x in opp for x in ("tron", "eldrazi")):
            return -0.07  # Too slow; they stabilize before we kill
        if any(x in opp for x in ("affinity", "artifact")):
            return 0.05   # Smash to Smithereens hits artifacts for 3 extra
        if any(x in opp for x in ("control", "blink")):
            return 0.04   # Exquisite Firecraft uncounterable
        if any(x in opp for x in ("boros energy",)):
            return -0.05  # Life gain from Phlage + Ocelot is brutal for burn
        if any(x in opp for x in ("combo", "storm", "goryo", "neoform")):
            return 0.06   # Pure race; we're often faster
        return 0.0



# ── Edge Case Registry ──────────────────────────────────────────────────────
#
# EC-01: Goblin Guide attack trigger — if they reveal a land, they get it.
#   In real matches: opponent reveals land → their next draw is known + they get a free land.
#   This is a NET NEGATIVE for us long-term (gives opponent resources).
#   However: Guide is still correct because 2 damage per turn beats the gift of a land.
#   The Gift of the Land means: don't overcount Guide's contribution in long games.
#
# EC-02: Monastery Swiftspear prowess timing.
#   PROWESS TRIGGER goes on the stack when you cast a noncreature spell.
#   You MUST cast the spell, then Swiftspear gets +1/+1.
#   You can cast spells PRE-COMBAT to make Swiftspear larger, THEN attack.
#   Sequence: cast Bolt (prowess trigger) → attack with Swiftspear as 2/3 → Bolt resolves.
#   With 2 spells before combat: Swiftspear is 3/4. With 3: 4/5. Etc.
#
# EC-03: Rift Bolt suspend — the "free" cast at suspend removal is NOT the suspend cost.
#   The suspend cost ({R}) is paid when you EXILE the card.
#   When the last counter is removed: "you may cast it without paying its mana cost."
#   This means Rift Bolt fires at the BEGINNING OF YOUR UPKEEP (not main phase).
#   It resolves before your draw step. You can target face, creature, or planeswalker.
#
# EC-04: Skewer the Critics spectacle condition.
#   "If an opponent lost life this turn" — ANY life loss counts.
#   Shock lands (pay 2 life) don't lose opponent life, they lose YOUR life.
#   But: opponent taking 1 damage from Vortex upkeep = spectacle active.
#   Opponent taking 2 from Guide = spectacle active for the rest of the turn.
#   Cast Bolt first → spectacle enabled → Skewer for {R} → effectively two 1-mana 3-damage spells.
#
# EC-05: Searing Blaze landfall timing.
#   "If you had a land enter the battlefield under your control THIS TURN."
#   Fetch land activation: crack fetch → land enters → landfall active.
#   Searing Blaze then deals 3 to player + 3 to creature.
#   In Burn deck without creatures to target: the 3 to creature is wasted.
#   STILL CORRECT: 3 to face is better than 1. Crack fetch before Searing Blaze.
#
# EC-06: Boros Charm + indestructible mode.
#   Mode 2 "permanents gain indestructible until EOT" — key vs. Supreme Verdict.
#   In goldfish: always mode 1 (4 damage). Never mode 2.
#   In match: hold Boros Charm open vs. control decks. If they don't sweep: use for damage.
#
# EC-07: Roiling Vortex + free spells interaction.
#   "Whenever a player casts a spell, if no mana was spent to cast that spell → 5 damage."
#   This fires for: Force of Negation (pitched), Solitude (evoked = no mana for evoke cost?).
#   Actually: Solitude evoke pays "exile a white card" — no MANA spent → Vortex fires!
#   Vortex deals 5 damage to the opponent who cast the free spell.
#   Also fires on your own free spells (if any) — rare in Burn.
#
# EC-08: Lightning Helix 3-damage + 3-life.
#   The life gain is yours (not irrelevant in burn mirror = life buffer).
#   In racing situations vs. Burn: gaining 3 life is effectively 3 less damage needed.
#   Priority: cast Helix before opponent's burn resolves to gain life first.
#
# EC-09: Skullcrack timing.
#   "Players can't gain life this turn. Damage can't be prevented this turn."
#   Cast Skullcrack BEFORE opponent gains life (e.g., in response to their Helix).
#   Also shuts down: Batterskull, Sorin, Amulet Titan Spelunking +4 life, etc.
#   In goldfish: just 3 damage, no tactical use.
#
# EC-10: Sunbaked Canyon / Fiery Islet cycling.
#   These can be tapped for mana (red or red/white) OR cycled for 1 mana + draw.
#   In goldfish: if we have excess mana and top-deck these with 20 damage needed:
#   cycle them to find actual burn spells. Don't waste them for {R} if you have burn.
#   Rule: cycle if you need cards more than you need the mana.
#
EDGE_CASES = [
    "EC-01: Goblin Guide gift of land is net negative long-term — still correct play (2 damage beats 1 land)",
    "EC-02: Swiftspear prowess: cast spell → trigger on stack → attack → trigger resolves before damage",
    "EC-03: Rift Bolt suspend fires at BEGINNING OF UPKEEP (before draw step)",
    "EC-04: Skewer spectacle: opponent losing ANY life this turn activates it — Bolt first then Skewer",
    "EC-05: Searing Blaze landfall: crack fetch BEFORE casting Blaze for 3+3 instead of 1+1",
    "EC-06: Boros Charm mode 2 (indestructible) is held vs. Supreme Verdict — goldfish: always mode 1",
    "EC-07: Roiling Vortex fires on FREE SPELLS (no mana paid) — Solitude evoke, Grief evoke = 5 damage",
    "EC-08: Lightning Helix life gain matters in burn mirrors — 3 life = 3 less damage needed from opponent",
    "EC-09: Skullcrack BEFORE opponent gains life — in response to their Helix, Prismatic Ending, etc.",
    "EC-10: Sunbaked Canyon / Fiery Islet: cycle when you need burn, use for mana when you need mana",
]
