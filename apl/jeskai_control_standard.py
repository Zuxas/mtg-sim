"""apl/jeskai_control_standard.py -- Jeskai Control (Standard)

Current-meta UWR control deck. Real counterspells (No More Lies,
Three Steps Ahead), burn removal (Lightning Helix, Fire Magic),
spot removal (Get Lost, Seam Rip), board wipes (Day of Judgment,
Ultima), flying finishers (North Wind Avatar, Shiko, Wan Shi Tong).

Lightning Helix is a 3-face-damage burn (handled via SPELL_EFFECTS
so it fires when cast, not just in AggroAPL's burn dictionary).

Composes ControlAPL.
"""
from apl.control_base import ControlAPL

# ── Counters (reactive) ────────────────────────────────────────────
NO_MORE_LIES   = "No More Lies"           # {W}{U}: counter unless 3
THREE_STEPS    = "Three Steps Ahead"      # {U} spree counter

# ── Removal ────────────────────────────────────────────────────────
LIGHTNING_HLX  = "Lightning Helix"        # {R}{W}: 3 face dmg + 3 life
GET_LOST       = "Get Lost"               # {1}{W}: exile creature/PW
SEAM_RIP       = "Seam Rip"               # {W}: 2-cmc exile enchant
FIRE_MAGIC     = "Fire Magic"             # {R} tiered wipe

# ── Wipes ───────────────────────────────────────────────────────────
DAY_OF_JUDG    = "Day of Judgment"        # {2}{W}{W}: wipe
ULTIMA         = "Ultima"                 # {3}{W}{W}: wipe + end turn

# ── Threats ────────────────────────────────────────────────────────
NORTH_WIND     = "North Wind Avatar"      # {2}{U}{U}{R} 5/5 flying
SHIKO          = "Shiko, Paragon of the Way"   # {2}{U}{R}{W} 4/5 flying vig
WAN_SHI        = "Wan Shi Tong, Librarian"     # {X}{U}{U} flash flying
JESKAI_REV     = "Jeskai Revelation"      # 7-cmc everything-spell

# ── Value / setup ──────────────────────────────────────────────────
STOCK_UP       = "Stock Up"
CONSULT        = "Consult the Star Charts"


class JeskaiControlAPL(ControlAPL):
    name = "Jeskai Control"
    max_turns = 16

    # No hand attack in mainboard
    HAND_ATTACK = ()

    # Reactive removal — hold mana open through main 1
    REMOVAL = (
        LIGHTNING_HLX,   # {R}{W}: doubles as face damage
        SEAM_RIP,        # {W}
        GET_LOST,        # {1}{W}
        FIRE_MAGIC,      # {R}: tiered wipe
    )

    # Counters — never cast on our own turn; reserve mana
    COUNTERS = (
        THREE_STEPS,     # {U} (spree mode)
        NO_MORE_LIES,    # {W}{U}
    )

    WIPES = (
        DAY_OF_JUDG,
        ULTIMA,
    )

    THREATS = (
        NORTH_WIND,      # 5/5 flying
        SHIKO,           # 4/5 flying vigilance
        WAN_SHI,         # X/X flash flying
        JESKAI_REV,      # 7-cmc big spell
    )

    VALUE_SPELLS = (
        STOCK_UP,
        CONSULT,
    )

    # 3-color control — wants 3+ lands, can run up to 6
    MULL_MIN_LANDS = 3
    MULL_MAX_LANDS = 6
