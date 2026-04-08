"""
delver.py — APL for UR Delver (Legacy)

Win condition: Flip Delver of Secrets T2, beat down with
Dragon's Rage Channeler / Murktide Regent behind Daze + Force.

Turn sequence:
  T1: Delver of Secrets or DRC (+ pitch spell for delirium)
  T2: More threats, flip Delver (3/2 flying)
  T3+: Murktide Regent (often 5/5+ for 2), finish

Keep criteria:
  - 1-2 lands (tempo deck — keep low land counts)
  - At least 1 threat (Delver, DRC, Murktide)
  - Cantrips count as action
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from apl.mulligan import generic_bottom


THREATS    = {"Delver of Secrets", "Dragon's Rage Channeler", "Dragon Rage Channeler",
              "Murktide Regent", "Sprite Dragon"}
COUNTERS   = {"Force of Will", "Daze", "Spell Pierce", "Flusterstorm"}
CANTRIPS   = {"Brainstorm", "Ponder", "Mishra's Bauble", "Consider"}
BURN       = {"Lightning Bolt", "Chain Lightning", "Price of Progress", "Fireblast"}


class DelverAPL(BaseAPL):

    name = "Delver"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        lands   = [c for c in hand if c.is_land()]
        threats = [c for c in hand if c.name in THREATS]
        cantrip = [c for c in hand if c.name in CANTRIPS]
        counters= [c for c in hand if c.name in COUNTERS]
        size = len(hand)

        if size <= 4: return True

        lc = len(lands)
        if lc == 0: return size <= 4
        if lc >= 4: return size <= 5  # tempo deck floods easily

        has_action = bool(threats or cantrip)
        if lc >= 1 and has_action: return True
        if mulligans >= 3: return lc >= 1
        return False

    def bottom(self, hand, n):
        return generic_bottom(hand, n)

    def main_phase(self, gs: GameState):
        """
        Delver priority:
          1. Land (only 1 needed — tempo deck)
          2. Threats first (Delver T1, DRC T1)
          3. Cantrips (Brainstorm/Ponder to find threats or flip Delver)
          4. Burn to face
          5. Murktide Regent (can be cast for cheap via delve)
        """
        self._play_land_if_able(gs)

        # 1. T1 threats — priority order
        for name in ("Delver of Secrets", "Dragon's Rage Channeler"):
            for c in list(gs.hand()):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 2. Cantrips (help flip Delver, find threats)
        self._resolve_cantrips(gs)

        # 3. More threats
        for c in sorted([c for c in gs.hand()
                         if c.name in THREATS
                         and gs.mana_pool.can_cast(c.mana_cost, c.cmc)],
                        key=lambda c: c.cmc):
            gs.cast_spell(c)

        # 4. Murktide — delve reduces effective CMC
        for c in list(gs.hand()):
            if c.name == "Murktide Regent":
                gy_size = len(gs.zones.graveyard)
                effective_cmc = max(2, int(c.cmc) - gy_size)
                if gs.mana_pool.total() >= effective_cmc:
                    # Temporarily reduce CMC, cast, restore
                    original_cmc = c.cmc
                    c.cmc = effective_cmc
                    success = gs.cast_spell(c)
                    if not success:
                        c.cmc = original_cmc
                    break

        # 5. Burn any leftover mana
        for c in list(gs.hand()):
            if c.name in BURN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.damage_dealt += 3  # burn to face

    def main_phase2(self, gs: GameState):
        # Burn spells are instants — can be cast post-combat
        for c in list(gs.hand()):
            if c.name in BURN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.damage_dealt += 3
