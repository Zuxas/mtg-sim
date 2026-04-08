"""
game_state.py — Core game state and turn structure for mtg-sim
"""

import copy
from enum import Enum
from data.card import Card, Tag
from engine.mana import ManaPool
from engine.zones import ZoneManager


class Phase(str, Enum):
    UNTAP   = "untap"
    UPKEEP  = "upkeep"
    DRAW    = "draw"
    MAIN1   = "main1"
    COMBAT  = "combat"
    MAIN2   = "main2"
    END     = "end"


class GameState:
    def __init__(self, mainboard: list, on_play: bool = True):
        self.mainboard    = mainboard
        self.on_play      = on_play
        self.turn         = 0
        self.phase        = Phase.UNTAP
        self.damage_dealt = 0
        self.land_played  = False
        self.mana_pool    = ManaPool()
        self.zones        = ZoneManager()
        self.energy       = 0
        self.life         = 20
        self._log_lines   = []
        self._verbose     = False

    def new_game(self):
        self.turn         = 0
        self.damage_dealt = 0
        self.land_played  = False
        self.energy       = 0
        self.life         = 20
        self.mana_pool.empty()
        self._log_lines   = []

    def _log(self, msg):
        self._log_lines.append(msg)
        if self._verbose:
            print(msg)

    def has_won(self, win_damage=20):
        return self.damage_dealt >= win_damage

