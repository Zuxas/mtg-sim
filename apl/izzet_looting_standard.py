"""apl/izzet_looting_standard.py -- Izzet Looting goldfish APL (Standard).

Looting is the same UR archetype family as Prowess, but trades fast threats
(Slickshot Show-Off, Otter tokens) for sturdier 3-toughness bodies (Tiger-Seal,
Duelist of the Mind, Fear of Missing Out) and a Frostcliff Siege card-draw
engine.

Per Worldly Counsel and McNamara's primers, the deck plays two modes:
  - **Aggro:** lead Tiger-Seal/Duelist, attack on curve, Frostcliff Siege Temur
    mode (+1/+0 trample haste) closes
  - **Crab-Control:** open with cantrips/removal, Stormchaser L3 + Quantum
    Riddler + Frostcliff Siege Jeskai mode (card draw on combat damage) grinds

Sources of truth (see handoff 2026-05-11_post-compact_looting_session.md):
  - Verified card data: mtg-meta-analyzer/scrapers/_verified_sb_cards.txt
  - SB plans: Team Resolve/guides/looting_sb_plans_verified.md
  - Match data: Team Resolve/guides/looting_portland_side_events.md (3-2 result)

CRITICAL CARD-TEXT NOTES (verified 2026-05-11):
  - Cori-Steel Cutter is BANNED (since 2025-06-30) -- not a Prowess card anymore
  - Detect Intrusion / Belion are Unhinged JOKE cards, NOT Standard legal
  - Flow State is a SORCERY (not enchantment) -- Annul misses, Spell Snare hits
  - Voice of Victory is a CREATURE (1/3) -- Annul misses
  - Aven Interrupter is 3 CMC -- Spell Snare misses
  - Monument to Endurance is 3 CMC artifact -- Snare misses, Annul hits, Abrade destroys
  - Sear (1R, 4 dmg) kills Sapling Nursery 3/4 reach Treefolk tokens
  - Sapling Nursery first legal 2026-02-07 -- pre/post Nursery MGL builds differ structurally
"""
from apl.aggro_base import AggroAPL


# ── Card name constants (verified via _verified_sb_cards.txt) ────────
TIGER_SEAL     = "Tiger-Seal"             # {U} 3/3 vigilance, taps upkeep, untaps on 2nd card draw
DUELIST        = "Duelist of the Mind"    # {1}{U} */3 flying vigilance, power = cards drawn
FOMO           = "Fear of Missing Out"    # {1}{R} 2/3 enchantment-creature, looter ETB, extra combat at delirium 4
STORMCHASER    = "Stormchaser's Talent"   # {U} Class -- Otter token + L2/L3 paths
QUANTUM_RIDDLER = "Quantum Riddler"       # {3}{U}{U} 4/6 flying, ETB draw, warp {1}{U}

OPT            = "Opt"
SLEIGHT        = "Sleight of Hand"
BOOMERANG      = "Boomerang Basics"       # {U} Lesson, bounce + draw if owned
INTO_FLOODMAW  = "Into the Flood Maw"     # {U} bounce creature (or any nonland with gift token)

TORCH          = "Torch the Tower"        # {R} 2 dmg (3 bargained), exile if dies
BURST          = "Burst Lightning"        # {R} 2 dmg / kicker {4} for 4
PYROCLASM      = "Pyroclasm"              # {1}{R} 2 dmg each creature
ABRADE         = "Abrade"                 # {1}{R} 3 dmg creature OR destroy artifact
SEAR           = "Sear"                   # {1}{R} 4 dmg creature/planeswalker

WINTERNIGHT    = "Winternight Stories"    # {2}{U} draw 3, discard 2 unless creature
FROSTCLIFF     = "Frostcliff Siege"       # {1}{U}{R} Jeskai (draw on combat dmg) or Temur (+1/+0 trample haste)
ROARING_FURNACE = "Roaring Furnace // Steaming Sauna"  # Room split

# Counters (Standard-legal Tokyo SB)
SPELL_SNARE    = "Spell Snare"            # {U} counter cmc=2 only
ANNUL          = "Annul"                  # {U} counter artifact OR enchantment SPELL
FLASHFREEZE    = "Flashfreeze"            # {1}{U} counter red or green spell
DISDAINFUL     = "Disdainful Stroke"      # {1}{U} counter cmc>=4
SPELL_PIERCE   = "Spell Pierce"           # {U} counter noncreature unless paid {2}

# SB / utility
GHOST_VACUUM   = "Ghost Vacuum"           # {1} artifact, GY exile
SOUL_GUIDE     = "Soul-Guide Lantern"     # {1} artifact, GY exile + sac for full opp GY exile
TIDEBINDER     = "Tishana's Tidebinder"   # {2}{U} 3/2 flash, counter activated/triggered ability
KAITO_CUNNING  = "Kaito, Cunning Infiltrator"  # {1}{U}{U} planeswalker (transformative SB)
IROH_DEMO      = "Iroh's Demonstration"   # {1}{R} Lesson, 1 dmg each opp creature OR 4 dmg one
BROADSIDE      = "Broadside Barrage"      # {1}{U}{R} 5 dmg creature/pw + loot


class IzzetLootingAPL(AggroAPL):
    """Goldfish Looting plan: deploy 1-mana 3/3 Tiger-Seal, 2-mana flying
    threats (Duelist + FOMO), then Frostcliff Siege for engine + Quantum Riddler
    closer. Cantrip-light vs Prowess (no Opt/Sleight in main) -- Boomerang Basics
    + Stormchaser L2 grave-recur are the card-velocity engines.
    """

    name = "Izzet Looting"
    max_turns = 12   # grindier than Prowess

    CREATURES = (
        TIGER_SEAL,       # 1-drop {U} 3/3 vigilance anchor
        DUELIST,          # 2-drop {1}{U} */3 flying vigilance
        FOMO,             # 2-drop {1}{R} 2/3 nightmare with looter ETB + extra combat
        STORMCHASER,      # 2-drop {U} Class enchantment (token + L2/L3)
        QUANTUM_RIDDLER,  # top-end {3}{U}{U} 4/6 flying, warp {1}{U} for early ETB tempo
    )

    CANTRIP_SPELLS = (
        BOOMERANG,        # {U} bounce + draw if you owned the target
        INTO_FLOODMAW,    # {U} bounce, sometimes used as cantrip-equivalent
        WINTERNIGHT,      # {2}{U} draw 3 discard 2 (Portland list only -- cut in Store Champ)
    )

    BURN_SPELLS = {
        TORCH:        (1, 2),   # {R} 2 dmg (3 bargained) -- creature/PW only, exiles
        BURST:        (1, 2),   # {R} 2 dmg / kicker for 4
    }

    PUMP_SPELLS = {}            # Looting is not a pump deck

    HASTE_CREATURES = frozenset()

    # Mulligan: Looting can keep one-landers on the draw with cantrips/Boomerang;
    # mirror requires cantrip-heavy hands. Tiger-Seal is the snap-keep anchor.
    MULL_MIN_LANDS = 1
    MULL_MAX_LANDS = 5
