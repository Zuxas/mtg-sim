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
    """Lute control variant. Inherits Jeskai Control sequencing. Wins via
    card advantage; the inevitability win-proxy was removed (flagged
    [!MISMODEL] until hand advantage is modeled -- see #74)."""
    name = "Jeskai Lute Control"
    ARCHETYPE = "control"
