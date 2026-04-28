"""apl/jeskai_control_standard_match.py -- Jeskai Control match APL."""
from apl.match_apl import MatchAPL
from apl.jeskai_control_standard import JeskaiControlAPL


class JeskaiControlStandardMatchAPL(MatchAPL, JeskaiControlAPL):
    ARCHETYPE = "control"

    # Typical Jeskai Control sideboard plans.
    SB_PLANS = {
        # vs aggro: more removal, fewer counters + big spells
        "aggro": (
            ["2 Torch the Tower", "2 Abrade", "2 Kinetic Hellion"],
            ["2 Three Steps Ahead", "2 Stock Up", "2 Jeskai Revelation"],
        ),
        # vs control/combo: more counters, less point-removal
        "control": (
            ["2 Disdainful Stroke", "2 Exorcise"],
            ["2 Lightning Helix", "2 Get Lost"],
        ),
        "combo": (
            ["2 Disdainful Stroke", "2 Soul-Guide Lantern"],
            ["2 Day of Judgment", "2 Get Lost"],
        ),
        "ramp": (
            ["2 Disdainful Stroke", "2 Exorcise"],
            ["2 Lightning Helix", "2 Seam Rip"],
        ),
    }
