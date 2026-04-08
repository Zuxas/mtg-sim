"""
lands.py — APL for Legacy Lands

Win condition: Dark Depths + Thespian's Stage → 20/20 Marit Lage token
Secondary: Loam + Wasteland/Rishadan lock

Turn sequence:
  T1: Mox Diamond (discard land) + Exploration / land
  T2: Fetch Dark Depths via Crop Rotation, get Thespian's Stage
  T3: Activate Stage copying Dark Depths (0 counters) → sacrifice → Marit Lage
  Attack for 20 on T4

Keep criteria:
  - At least 2 mana sources (lands / Mox Diamond)
  - Either Exploration or Crop Rotation
  - Combo pieces accessible within 2-3 turns
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from apl.mulligan import generic_bottom


MANA_ACCEL = {"Mox Diamond", "Exploration", "Loam Dryad"}
COMBO      = {"Dark Depths", "Thespian's Stage"}
TUTORS     = {"Crop Rotation", "Elvish Reclaimer"}
LOCK       = {"Wasteland", "Rishadan Port", "The Tabernacle at Pendrell Vale"}


class LandsAPL(BaseAPL):

    name = "Lands"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        lands   = [c for c in hand if c.is_land()]
        mox     = [c for c in hand if c.name == "Mox Diamond"]
        explor  = [c for c in hand if c.name == "Exploration"]
        crop    = [c for c in hand if c.name == "Crop Rotation"]
        reclaim = [c for c in hand if c.name == "Elvish Reclaimer"]
        depth   = [c for c in hand if c.name == "Dark Depths"]
        stage   = [c for c in hand if c.name == "Thespian's Stage"]
        size = len(hand)

        if size <= 4: return True
        lc = len(lands)
        if lc == 0 and not mox: return False

        # Ideal: has a combo piece and a way to find the other
        has_combo  = bool(depth or stage)
        has_tutor  = bool(crop or reclaim)
        has_engine = bool(explor or mox)
        if has_combo and (has_tutor or has_engine): return True
        if lc >= 2 and (has_tutor or has_engine): return True
        if mulligans >= 3: return lc >= 1 or bool(mox)
        return lc >= 2

    def bottom(self, hand, n):
        return generic_bottom(hand, n)

    def main_phase(self, gs: GameState):
        """
        Lands priority:
          1. Land drop (critical — plays 2+ per turn with Exploration)
          2. Mox Diamond (discard a land, get 1 mana of any color)
          3. Exploration (play extra lands)
          4. Crop Rotation (instant-speed land tutor — find Dark Depths or Stage)
          5. Assemble Dark Depths + Stage combo
          6. Elvish Reclaimer (finds lands each turn)
        """
        # Multiple land drops if Exploration is in play
        explorations = sum(1 for c in gs.zones.battlefield if c.name == "Exploration")
        land_drops_allowed = 1 + explorations
        lands_played_this_turn = 0

        while lands_played_this_turn < land_drops_allowed:
            land = self._best_land_for_combo(gs)
            if not land:
                break
            if gs.play_land(land):
                lands_played_this_turn += 1
                gs.mana_pool.empty()
                gs.tap_lands()
            else:
                break

        # Mox Diamond — discard a land to add 1 mana immediately
        for c in list(gs.hand()):
            if c.name == "Mox Diamond" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Only cast if we have a spare land to discard
                spare_lands = [l for l in gs.hand() if l.is_land()]
                if spare_lands:
                    gs.cast_spell(c)
                    # Discard cheapest land as the Mox cost
                    discard = spare_lands[0]
                    gs.zones.hand.remove(discard)
                    gs.zones.graveyard.append(discard)
                    gs.mana_pool.add("G")  # Mox produces any color — use G

        # Exploration
        for c in list(gs.hand()):
            if c.name == "Exploration" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # Now get the extra land drop
                extra = self._best_land_for_combo(gs)
                if extra:
                    gs.play_land(extra)
                    gs.mana_pool.empty()
                    gs.tap_lands()

        # Crop Rotation — fetch Dark Depths if not in play, else Stage
        for c in list(gs.hand()):
            if c.name == "Crop Rotation" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                self._use_crop_rotation(gs, c)

        # Elvish Reclaimer — activated ability to fetch a land
        for c in gs.zones.battlefield:
            if c.name == "Elvish Reclaimer":
                self._use_reclaimer(gs, c)

        # Assemble combo
        self._try_assemble_combo(gs)

    def _best_land_for_combo(self, gs):
        """Choose the most useful land to play next."""
        hand_lands = [c for c in gs.hand() if c.is_land()]
        if not hand_lands:
            return None
        # Priority: Dark Depths > Thespian's Stage > Crop Rotation lands > others
        has_depths = any(c.name == "Dark Depths" for c in gs.zones.battlefield)
        has_stage  = any(c.name == "Thespian's Stage" for c in gs.zones.battlefield)
        for priority in (
            ("Dark Depths" if not has_depths else None),
            ("Thespian's Stage" if not has_stage else None),
        ):
            if priority:
                for l in hand_lands:
                    if l.name == priority:
                        return l
        return hand_lands[0]

    def _use_crop_rotation(self, gs, crop_card):
        """Crop Rotation: sacrifice a land, find Dark Depths or Stage."""
        has_depths = any(c.name == "Dark Depths" for c in gs.zones.battlefield)
        has_stage  = any(c.name == "Thespian's Stage" for c in gs.zones.battlefield)
        target_name = "Dark Depths" if not has_depths else "Thespian's Stage"

        target = next((c for c in gs.zones.library if c.name == target_name), None)
        if not target:
            return

        # Sacrifice a non-combo land
        sacrifice_candidates = [
            c for c in gs.zones.battlefield
            if c.is_land() and c.name not in COMBO
        ]
        if not sacrifice_candidates:
            return

        sac = sacrifice_candidates[0]
        gs.zones.destroy(sac)
        gs.zones.library.remove(target)
        gs.zones.battlefield.append(target)
        if crop_card in gs.zones.hand:
            gs.zones.hand.remove(crop_card)
            gs.zones.graveyard.append(crop_card)
        gs._log(f"  Crop Rotation → {target.name}")

    def _use_reclaimer(self, gs, reclaimer):
        """Elvish Reclaimer: tap + 1G → fetch a land."""
        if gs.mana_pool.can_cast("{G}", 1):
            has_depths = any(c.name == "Dark Depths" for c in gs.zones.battlefield)
            target_name = "Dark Depths" if not has_depths else "Thespian's Stage"
            target = next((c for c in gs.zones.library if c.name == target_name), None)
            if target:
                gs.mana_pool.pay("{G}", 1)
                gs.zones.library.remove(target)
                gs.zones.battlefield.append(target)
                gs._log(f"  Elvish Reclaimer → {target.name}")

    def _try_assemble_combo(self, gs):
        """If Dark Depths + Stage in play, activate Stage → Marit Lage."""
        has_depths = any(c.name == "Dark Depths" for c in gs.zones.battlefield)
        has_stage  = any(c.name == "Thespian's Stage" for c in gs.zones.battlefield)

        if has_depths and has_stage:
            # Activate Stage (copy Dark Depths with 0 counters → sacrifice)
            # Cost: {2} + T — need 2 mana
            if gs.mana_pool.total() >= 2:
                gs.mana_pool.pay("", 2)
                # Remove both combo pieces
                gs.zones.battlefield = [c for c in gs.zones.battlefield
                                        if c.name not in COMBO]
                # Create 20/20 Marit Lage
                marit = Card(
                    name="Marit Lage",
                    mana_cost="",
                    cmc=0,
                    type_line="Legendary Creature — Avatar",
                    oracle_text="Flying, indestructible",
                    power="20", toughness="20",
                    colors=[],
                )
                from engine.keywords import KWTag
                marit.tags.add(Tag.CREATURE)
                marit.tags.add(KWTag.FLYING)
                marit.tags.add(KWTag.INDESTRUCTIBLE)
                marit.summoning_sickness = True
                gs.zones.battlefield.append(marit)
                gs._log("  Dark Depths + Stage → Marit Lage (20/20 flying, indestructible)")

    def main_phase2(self, gs: GameState):
        """Post-combat: instant-speed Crop Rotation, Life from the Loam."""
        pass
