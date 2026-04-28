"""apl/izzet_spellementals_standard_match.py -- Spellementals match APL."""
from apl.match_apl import MatchAPL
from apl.izzet_spellementals_standard import IzzetSpellementalsAPL


class IzzetSpellementalsStandardMatchAPL(MatchAPL, IzzetSpellementalsAPL):
    ARCHETYPE = "control"
    # Sideboard: 1 Fire Magic, 1 Flame Javelin, 2 Get Out, 2 Nimble
    # Larcenist, 2 Pyroclasm, 2 Soul-Guide Lantern, 2 Tishana's
    # Tidebinder, 3 Torrent of Stone. Spell Pierce lives in mainboard
    # only (2 copies) — can't be brought in from SB.
    SB_PLANS = {
        "aggro": (
            ["1 Fire Magic", "2 Get Out", "2 Pyroclasm",
             "3 Torrent of Stone"],
            ["2 Bounce Off", "1 Glacial Dragonhunt",
             "4 Winternight Stories", "1 Abrade"],
        ),
        "control": (
            ["2 Nimble Larcenist", "2 Tishana's Tidebinder",
             "1 Flame Javelin"],
            ["2 Bounce Off", "3 Sunderflock"],
        ),
        "combo": (
            ["2 Soul-Guide Lantern", "2 Tishana's Tidebinder",
             "1 Flame Javelin"],
            ["2 Bounce Off", "4 Eddymurk Crab"],
        ),
        "ramp": (
            ["2 Nimble Larcenist", "1 Flame Javelin",
             "2 Tishana's Tidebinder"],
            ["2 Bounce Off", "2 Eddymurk Crab", "1 Sear"],
        ),
        "tempo": (
            ["1 Fire Magic", "2 Pyroclasm", "2 Get Out",
             "2 Tishana's Tidebinder"],
            ["4 Winternight Stories", "2 Bounce Off",
             "1 Glacial Dragonhunt"],
        ),
    }
