"""
apl/azorius_control_standard_match.py — Azorius Control (Standard)

Real-meta Azorius Control from Edge of Eternities SC (top 4, 2025-08-31).
Actually Orzhov-leaning mono-white tempo/control that splashes blue via
Voice of Victory and Nurturing Pixie. Gauntlet-2026-04-19 field WR 56.2%.

Plan:
  T1  Novice Inspector (1/2, makes a Clue on ETB) or Splitskin Doll
  T2  Seam Rip on something small, or Voice of Victory (locks opp
      off instants/sorceries on my turns — huge tempo swing)
  T3  Enduring Innocence (whenever I draw, gain 1 life; small threat)
      or Get Lost on a big threat
  T4  Starfield Shepherd (4/4 flying) or Elspeth, Storm Slayer
  T5+ Cosmogrand Zenith (6/6 flying, ETB draws 3 if threshold) +
      Shardmage's Rescue as flicker/protection

Uses ControlAPL base so MatchAPL's _match_cast_removal sees Seam Rip
and Get Lost in the REMOVAL tuple and fires them at the biggest
opp creature.
"""
from apl.control_base import ControlAPL
from apl.match_apl import MatchAPL


# ── Removal ────────────────────────────────────────────────────────
SEAM_RIP        = "Seam Rip"            # {W}: exile enchant/PW
GET_LOST        = "Get Lost"            # {1}{W}: exile any nonland

# ── Wipes (sideboard only) ─────────────────────────────────────────
DAY_OF_JUDG     = "Day of Judgment"
EXORCISE        = "Exorcise"

# ── Threats ────────────────────────────────────────────────────────
NOVICE_INSPECTOR = "Novice Inspector"    # {W} 1/2 + clue
SPLITSKIN_DOLL   = "Splitskin Doll"      # {W} 1/1 flicker-friendly
NURTURING_PIXIE  = "Nurturing Pixie"     # {1}{W} 1/3 flash flicker
VOICE_OF_VICTORY = "Voice of Victory"    # {1}{W}{W} 2/3, spell-lock opp
STARFIELD_SHEP   = "Starfield Shepherd"  # {2}{W} 4/4 flying ench-lord
COSMOGRAND_ZEN   = "Cosmogrand Zenith"   # {3}{W}{W} 6/6 flying + draw
ELSPETH          = "Elspeth, Storm Slayer"
ZACK_FAIR        = "Zack Fair"

# ── Value / setup ──────────────────────────────────────────────────
ENDURING_INNOCENCE = "Enduring Innocence"  # {W}{W} enchant 2/2
SHARDMAGES_RESCUE  = "Shardmage's Rescue"  # {1}{W} flicker/protection


class AzoriusControlStandardMatchAPL(MatchAPL, ControlAPL):
    ARCHETYPE = "control"
    name = "Azorius Control (Standard)"
    max_turns = 15

    HAND_ATTACK = ()

    REMOVAL = (
        SEAM_RIP,
        GET_LOST,
        EXORCISE,
    )

    COUNTERS = ()

    WIPES = (
        DAY_OF_JUDG,
    )

    # Priority order: ControlAPL casts reversed(THREATS), so the
    # BACK of this tuple is cast first when mana allows. Voice of
    # Victory is jumped ahead of Starfield Shepherd (same cmc 3)
    # because its spell-lock completely shuts down reactive opp
    # decks — a T3 Voice often snowballs the game.
    THREATS = (
        NOVICE_INSPECTOR,      # 1
        SPLITSKIN_DOLL,        # 1
        NURTURING_PIXIE,       # 2 flash
        STARFIELD_SHEP,        # 3 flyer
        VOICE_OF_VICTORY,      # 3 spell-lock — priority over Starfield
        ELSPETH,               # 5 PW
        COSMOGRAND_ZEN,        # 5 big flyer
        ZACK_FAIR,             # 6
    )

    VALUE_SPELLS = (
        ENDURING_INNOCENCE,
        SHARDMAGES_RESCUE,
    )

    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5

    SB_PLANS = {
        "aggro": (
            ["2 Day of Judgment", "2 Authority of the Consuls",
             "2 Devout Decree", "1 Dauntless Scrapbot"],
            ["3 Cosmogrand Zenith", "3 Starfield Shepherd",
             "1 Zack Fair"],
        ),
        "control": (
            ["3 Ghost Vacuum", "2 Beza, the Bounding Spring",
             "1 Exorcise"],
            ["4 Seam Rip", "2 Splitskin Doll"],
        ),
        "combo": (
            ["3 Ghost Vacuum", "1 Exorcise",
             "2 Authority of the Consuls"],
            ["3 Starfield Shepherd", "2 Nurturing Pixie",
             "1 Zack Fair"],
        ),
        "ramp": (
            ["2 Requisition Raid", "2 Beza, the Bounding Spring",
             "1 Exorcise"],
            ["3 Cosmogrand Zenith", "2 Splitskin Doll"],
        ),
        "tempo": (
            ["2 Authority of the Consuls", "2 Day of Judgment",
             "1 Dauntless Scrapbot"],
            ["3 Cosmogrand Zenith", "2 Nurturing Pixie"],
        ),
    }
