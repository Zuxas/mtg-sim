"""
apl/sultai_control_standard_match.py -- Sultai Control match APL (Standard 2026)

G/U/B grindy control. Kills via attrition T7-9.

Key cards:
  Ancient Cornucopia {3}: artifact ramp + life gain trigger
  Deceit {2UB}:           bounce + draw (repeatable with self-bounce)
  Superior Spider-Man:    recursive threat / card advantage
  Rakshasa's Bargain {2BB}: draw 3, lose 3 life
  Awaken the Honored Dead {4BG}: recur two creatures from GY
  Withering Curse {1B}:   enchantment; opponent loses 1 life each upkeep
  Emeritus of Ideation:   card draw engine

Matchup roles:
  vs Aggro:    stabilize with removal + Cornucopia lifegain; Deceit bounces threats
  vs Midrange: out-grind with Bargain + Superior Spider-Man recursion
  vs Control:  Deceit generates inevitable advantage; Awaken refills from GY
  vs Combo:    counter Lessons engine; soul lantern GY hate

No counters main; Deceit is the primary interaction (bounce + draw replaces removal).
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power
from apl.aware_match_apl import AwareMatchAPL
from apl.sultai_control_standard import SultaiControlAPL

DECEIT       = "Deceit"
WITHERING    = "Withering Curse"
CORNUCOPIA   = "Ancient Cornucopia"
SPIDERMAN    = "Superior Spider-Man"
BARGAIN      = "Rakshasa's Bargain"
AWAKEN       = "Awaken the Honored Dead"

SOUL_GUIDE   = "Soul-Guide Lantern"
FLASHFREEZE  = "Flashfreeze"
DURESS       = "Duress"
NEGATE       = "Negate"
DISDAINFUL   = "Disdainful Stroke"
FATAL_PUSH   = "Fatal Push"

KILL_PRIORITY = (
    "Gran-Gran",
    "Mightform Harmonizer",
    "Icetill Explorer",
    "Stormchaser's Talent",
    "Monument to Endurance",
    "Badgermole Cub",
)


class SultaiControlStandardMatchAPL(AwareMatchAPL, SultaiControlAPL):
    name = "Sultai Control"
    ARCHETYPE = "control"

    # No main-deck counters, so no lands are held back on the opponent's turn.
    COUNTER_COST  = 0
    COUNTER_CARDS = set()

    # Deceit ({4}{U/B}{U/B}, evoke {U/B}{U/B}, no flash) is not in the generic
    # removal table: that path charged its printed six mana, put it in the
    # graveyard, and also ran from pre_combat_instant on the opponent's turn.
    # It is evoked for {U}{U} in our own main phase instead.
    MATCH_REMOVAL = {}
    MATCH_BOUNCE = set()
    MATCH_EXILE  = set()

    def _match_cast_removal(self, gs: GameState, opponent: GameState):
        if opponent is not None:
            for name in KILL_PRIORITY:
                target = next((c for c in opponent.zones.battlefield
                               if c.name == name and c.has(Tag.CREATURE)), None)
                if target is not None and self._evoke_deceit(gs, opponent, target):
                    break
        super()._match_cast_removal(gs, opponent)

    SB_PLANS = {
        "aggro": (
            [SOUL_GUIDE, SOUL_GUIDE, FATAL_PUSH, FATAL_PUSH, DURESS, DURESS],
            [WITHERING, WITHERING, AWAKEN, BARGAIN, DECEIT, DECEIT],
        ),
        "control": (
            [NEGATE, NEGATE, DISDAINFUL, DISDAINFUL, DURESS, DURESS],
            [WITHERING, WITHERING, AWAKEN, CORNUCOPIA, DECEIT, DECEIT],
        ),
        "combo": (
            [SOUL_GUIDE, SOUL_GUIDE, SOUL_GUIDE, NEGATE, NEGATE, DURESS, DURESS],
            [WITHERING, WITHERING, AWAKEN, CORNUCOPIA, BARGAIN, DECEIT, DECEIT],
        ),
        "ramp": (
            [FLASHFREEZE, FLASHFREEZE, DISDAINFUL, DISDAINFUL, DURESS],
            [WITHERING, AWAKEN, CORNUCOPIA, DECEIT, BARGAIN],
        ),
        "tempo": (
            [FATAL_PUSH, FATAL_PUSH, SOUL_GUIDE, SOUL_GUIDE, DURESS, DURESS],
            [WITHERING, WITHERING, AWAKEN, BARGAIN, DECEIT, DECEIT],
        ),
    }

