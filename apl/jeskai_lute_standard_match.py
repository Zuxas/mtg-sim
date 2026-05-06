"""
apl/jeskai_lute_standard_match.py -- Jeskai Control with Resonating Lute (post-PT-SOS).

Pure-spell control variant. Win condition is inevitability via card advantage
once Resonating Lute + Stock Up + Jeskai Revelation engine is online. Mainboard
runs 0 creatures, so it cannot win in the sim by combat damage -- needs an
inevitability proxy similar to Izzet Lessons.

Source: Nakazima Syunsuke 1st place 2026-04-26 (mtg_meta DB deck_id 137714).
Stock list:
  4 Consult the Star Charts, 4 Stock Up, 4 No More Lies, 4 Lightning Helix
  3 Jeskai Revelation, 3 Resonating Lute, 3 Get Lost
  2 Day of Judgment, 2 Spell Snare, 2 Three Steps Ahead, 2 Seam Rip
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from apl.jeskai_control_standard_match import JeskaiControlStandardMatchAPL


LUTE         = "Resonating Lute"
STOCK_UP     = "Stock Up"
CONSULT      = "Consult the Star Charts"
REVELATION   = "Jeskai Revelation"
NO_MORE_LIES = "No More Lies"


class JeskaiLuteMatchAPL(JeskaiControlStandardMatchAPL):
    """Lute control variant. Inherits Jeskai Control sequencing but adds
    inevitability proxy when card-advantage engine is online."""
    name = "Jeskai Lute Control"
    ARCHETYPE = "control"

    # Suppress under opposing spell-lock or hand-disruption attrition
    _SUPPRESSING_LOCK_PIECES = {
        "High Noon", "Voice of Victory", "Kutzil, Malamet Exemplar",
    }

    def main_phase2_match(self, gs: GameState, opponent: GameState):
        """Inevitability proxy: once Lute is on board + we have 5+ cards in
        hand + opponent's clock isn't lethal next turn, declare game won.

        Lute provides 2x mana for instants/sorceries + draws extra cards;
        Stock Up draws 5 / keeps 2; Jeskai Revelation can be flashbacked.
        Real-world this engine grinds opp out of resources. Sim can't model
        the recursive card advantage, so we use a proxy.

        Conditions to fire:
          T5+ AND Lute on board AND hand size >= 5 AND we have life cushion
          T6+ AND Lute on board AND hand size >= 4

        Suppress when:
          - opp has High Noon / Voice of Victory (we can't cast our spells)
          - opp has dealt 14+ damage (we're on the back foot)
        """
        if gs.turn < 5:
            return

        # Suppression: opp lock pieces
        if opponent is not None:
            for c in opponent.zones.battlefield:
                if c.name in self._SUPPRESSING_LOCK_PIECES:
                    return

        bf_names = {c.name for c in gs.zones.battlefield}
        lute_active = LUTE in bf_names
        if not lute_active:
            return

        hand_size = len(gs.zones.hand)
        my_life   = gs.life

        # Suppression: we're being killed quickly (life pressure)
        # If we're at 6 life or below, we can't durdle to inevitability
        if my_life <= 6:
            return

        # Suppression: opp has lethal-ish board this turn
        if opponent is not None:
            opp_power = sum(
                (c.effective_power() if hasattr(c, 'effective_power') else 0)
                for c in opponent.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'tapped', False)
            )
            if opp_power >= my_life - 2:
                return

        cond_t5 = gs.turn >= 5 and hand_size >= 5
        cond_t6 = gs.turn >= 6 and hand_size >= 4
        cond_t7 = gs.turn >= 7 and hand_size >= 3

        if cond_t5 or cond_t6 or cond_t7:
            opp_life = opponent.life if opponent is not None else 20
            if opp_life > 0:
                gs.damage_dealt += opp_life + 1
                gs._log(f"  [Lute] CA engine inevitability T{gs.turn}: "
                        f"hand={hand_size} life={my_life} opp_life={opp_life} "
                        f"-> declare win")
