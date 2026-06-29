"""apl/temur_prowess_match.py -- Temur Prowess (Standard) match APL.

Archetype: Temur Prowess -- the "Break Out" tempo-prowess shell.
Source: mtg_meta.db -- 158 Temur Prowess samples, 154 of them Standard
(only 4 Modern). Representative list: deck_id=14216 (1st, MTGO League
2026-07-27) -> decks/temur_prowess_standard.txt.

Despite the "prowess" name this is a creature-based RG/Temur tempo deck.
The growth comes from cheap pump spells (Violent Urge, Overprotect,
Dreadmaw's Ire, Bushwhack) layered on aggressive bodies, plus Break Out
to cheat Balustrade Wurm / Summon: Brynhildr onto the board ahead of curve.

Game plan:
  T1  Patchwork Beastie / Cenote Scout (1-drop bodies)
  T2  Keen-Eyed Curator / Fear of Missing Out / Wildfire Wickerfolk
      (haste trample) / Summon: Brynhildr  (or Break Out)
  T3  Tersa Lightshatter, keep deploying, start layering pump
  T4+ Pump a connecting threat with Violent Urge/Overprotect/Dreadmaw's Ire
      for trample reach; Balustrade Wurm (haste trample) closes.

Timing priorities:
  1. Deploy cheap threats on curve (tempo first).
  2. Break Out early to put a big body down ahead of curve.
  3. Spend leftover mana on pump spells when a creature is in play
     (they double as prowess-style fuel and combat reach).
  4. Hold a pump spell as a combat trick to push lethal / win a block.

Extends AwareMatchAPL for trade-aware combat, lethal recognition, and the
opponent threat model. No maindeck counters/removal (Bushwhack's fight mode
and the SB burn are the only interaction), so COUNTER_COST = 0.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL


# --- 1-drops ---------------------------------------------------------------
PATCHWORK_BEASTIE   = "Patchwork Beastie"
CENOTE_SCOUT        = "Cenote Scout"
# --- 2-drops ---------------------------------------------------------------
KEEN_EYED_CURATOR   = "Keen-Eyed Curator"
FEAR_OF_MISSING_OUT = "Fear of Missing Out"
WILDFIRE_WICKERFOLK = "Wildfire Wickerfolk"
SUMMON_BRYNHILDR    = "Summon: Brynhildr"
# --- 3-drops ---------------------------------------------------------------
TERSA_LIGHTSHATTER  = "Tersa Lightshatter"
# --- top end / cheat target -----------------------------------------------
BALUSTRADE_WURM     = "Balustrade Wurm"
# --- enabler ---------------------------------------------------------------
BREAK_OUT           = "Break Out"
# --- pump / interaction (noncreature fuel) --------------------------------
VIOLENT_URGE        = "Violent Urge"
OVERPROTECT         = "Overprotect"
DREADMAWS_IRE       = "Dreadmaw's Ire"
BUSHWHACK           = "Bushwhack"
# --- sideboard burn (only relevant post-board / for removal dispatcher) ---
FIRE_MAGIC          = "Fire Magic"
ABRADE              = "Abrade"


# Cheap bodies in rough curve order (cast earliest first).
CREATURE_CURVE = [
    PATCHWORK_BEASTIE, CENOTE_SCOUT,
    WILDFIRE_WICKERFOLK, KEEN_EYED_CURATOR, FEAR_OF_MISSING_OUT,
    SUMMON_BRYNHILDR,
    TERSA_LIGHTSHATTER,
    BALUSTRADE_WURM,
]

# Noncreature pump spells -- cast cheapest first as prowess-style fuel /
# board growth once we actually have a creature to benefit.
PUMP_SPELLS = [DREADMAWS_IRE, VIOLENT_URGE, BUSHWHACK, OVERPROTECT]

# A pump spell we like to hold back as a combat trick.
COMBAT_TRICK_SPELLS = [OVERPROTECT, VIOLENT_URGE, DREADMAWS_IRE]


class TemurProwessMatchAPL(AwareMatchAPL):
    """Temur Prowess (Standard) -- Break Out tempo-prowess."""

    name = "Temur Prowess (Standard)"
    ARCHETYPE = "tempo"
    win_condition_damage = 20
    max_turns = 12

    # No maindeck counters -> never bluff counter mana.
    COUNTER_COST  = 0
    COUNTER_CARDS = set()

    # Only burn lives in the SB; modelled here so post-board games / the
    # removal dispatcher have a valid suite. (name -> (cost, max_toughness))
    MATCH_REMOVAL = {
        FIRE_MAGIC: ("R",  2),   # 2 dmg tier (SB)
        ABRADE:     ("1R", 4),   # 3 dmg / destroy artifact (SB)
    }
    MATCH_EXILE  = set()
    MATCH_BOUNCE = set()
    MATCH_WIPES  = set()

    # ------------------------------------------------------------------
    # Mulligan -- aggro keep: 2-4 lands plus an early play.
    # ------------------------------------------------------------------
    def keep(self, hand, mulligans, on_play) -> bool:
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return mulligans >= 2
        # Want a turn-1 or turn-2 play.
        early = any(
            (not c.is_land())
            and getattr(c, "cmc", 9) <= 2
            and (c.has(Tag.CREATURE) or c.name == BREAK_OUT)
            for c in hand
        )
        if early:
            return True
        return mulligans >= 2

    def bottom(self, hand, n) -> list:
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, "cmc", 0))
        # Keep ~3 lands; pitch extra lands then the most expensive spells.
        return (lands[3:] + spells)[:n]

    # ------------------------------------------------------------------
    # Main phase
    # ------------------------------------------------------------------
    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent

        # 1. Land + mana. The engine already tapped (honoring reserve, which
        #    is 0 here); playing a land needs a re-tap to pick it up.
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 2. Removal (no-op pre-board unless SB burn is in hand).
        if opponent is not None:
            self._match_cast_removal(gs, opponent)

        # 3. Break Out early -- cheat a body / manifest ahead of curve.
        self._cast_named(gs, BREAK_OUT)

        # 4. Deploy creatures on curve.
        for name in CREATURE_CURVE:
            self._cast_named(gs, name)

        # 5. Any remaining creature not in the explicit curve.
        for card in list(gs.zones.hand):
            if (not card.is_land() and card.has(Tag.CREATURE)
                    and gs.mana_pool.can_cast(card.mana_cost, card.cmc)):
                gs.cast_spell(card)

        # 6. Spend leftover mana on pump spells -- but only when we have a
        #    creature to benefit, and keep one trick back if a combat is
        #    likely (we have an untapped attacker + opp has blockers).
        self._spend_on_pump(gs, opponent)

    def _have_creature(self, gs) -> bool:
        return any(not c.is_land() and c.has(Tag.CREATURE)
                   for c in gs.zones.battlefield)

    def _spend_on_pump(self, gs, opponent):
        if not self._have_creature(gs):
            return
        # Decide whether to reserve a combat trick: only if we have an
        # attacker that can connect and the opp has a blocker to beat.
        ready_attacker = any(
            not c.is_land() and c.has(Tag.CREATURE)
            and not getattr(c, "summoning_sickness", False)
            and not getattr(c, "tapped", False)
            for c in gs.zones.battlefield
        )
        opp_blockers = 0
        if opponent is not None:
            opp_blockers = sum(
                1 for c in opponent.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, "tapped", False)
            )
        reserve_trick = ready_attacker and opp_blockers > 0

        reserved_name = None
        if reserve_trick:
            for tname in COMBAT_TRICK_SPELLS:
                if any(c.name == tname for c in gs.zones.hand):
                    reserved_name = tname
                    break

        # Cast remaining pump cheapest-first, skipping the reserved trick.
        for _ in range(12):
            cast_any = False
            for name in PUMP_SPELLS:
                if name == reserved_name:
                    continue
                if self._cast_named(gs, name):
                    cast_any = True
                    break
            if not cast_any:
                break

    def _cast_named(self, gs: GameState, name: str) -> bool:
        """Cast the first castable copy of `name` from hand. Returns True if cast."""
        for card in list(gs.zones.hand):
            if card.name != name:
                continue
            if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                return False
            try:
                gs.cast_spell(card)
            except Exception as e:
                # Defensive: never let one card crash the match.
                gs._log(f"  [temur] cast {name} failed: {e}")
                return False
            return True
        return False

    def _play_land_if_able(self, gs: GameState):
        if gs.land_played:
            return
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands:
            return

        def score(c):
            n = (c.name or "").lower()
            # Untapped duals first, then basics; nothing here enters tapped
            # unconditionally, so keep it simple and stable.
            if "copperline" in n or "thornspire" in n or "karplusan" in n:
                return 0
            if "forest" in n or "mountain" in n:
                return 1
            return 2

        gs.play_land(min(lands, key=score))

    # ------------------------------------------------------------------
    # Combat trick: pump a blocked attacker to win the fight / push damage.
    # Mirrors the engine's pump model (counters add to power/toughness).
    # ------------------------------------------------------------------
    def combat_trick(self, gs: GameState, opponent: GameState,
                     attackers: list, blocker_assignments: dict):
        if not attackers:
            return
        assign = {id(k): v for k, v in (blocker_assignments or {}).items()}

        # Pick the trick in hand (cheapest first) we can afford.
        trick = None
        for tname in (DREADMAWS_IRE, VIOLENT_URGE, OVERPROTECT):
            for c in gs.zones.hand:
                if c.name == tname and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    trick = c
                    break
            if trick:
                break
        if trick is None:
            return

        # Target: a blocked attacker that would die or fail to kill its
        # blocker, where +2/+2 flips the outcome. Fall back to the biggest
        # unblocked attacker (extra reach toward lethal).
        target = None
        for atk in attackers:
            blks = assign.get(id(atk), [])
            if not blks:
                continue
            blk = max(blks, key=lambda b: safe_power(b))
            ap, at = safe_power(atk), safe_toughness(atk)
            bp, bt = safe_power(blk), safe_toughness(blk)
            dies = bp >= at
            kills = ap >= bt
            if (dies and (at + 2) > bp) or (not kills and (ap + 2) >= bt):
                target = atk
                break
        if target is None:
            unblocked = [a for a in attackers if not assign.get(id(a), [])]
            if unblocked:
                target = max(unblocked, key=lambda a: safe_power(a))
        if target is None:
            return

        gs.mana_pool.pay(trick.mana_cost, trick.cmc)
        gs.zones.hand.remove(trick)
        gs.zones.graveyard.append(trick)
        gs.noncreature_spells_this_turn += 1
        # +2/+2 approximation (Violent Urge/Overprotect/Dreadmaw's Ire all
        # buff power; counters drive both P and T in the engine model).
        target.counters = getattr(target, "counters", 0) + 2
        gs._log(f"  [combat trick] {trick.name} pumps {target.name} (+2/+2)")
