# -*- coding: utf-8 -*-
"""
apl/sb_plans.py — Sideboard premium lookup table for all decks.

Returns the estimated win% swing from G1 → G2 based on:
  - Which SB cards are live vs this opponent
  - How many dedicated slots we're bringing in
  - Whether the hate fundamentally changes the game plan

Used by sideboard_premium() in each APL when a full override isn't present.
Values are additive deltas on top of G1 win rate for the on-play G2 estimate.
"""

# ── Per-deck SB premium tables ─────────────────────────────────────────────
# Format: {opp_keyword: premium_pct}
# Matched via substring search on lowercase opponent name.

AMULET_TITAN_SB = {
    # Amulet SB: 2x Force of Negation, 2x Veil of Summer, 2x Boseiju,
    #            2x Endurance, 2x Reclamation Sage, 2x Cavern of Souls,
    #            1x Bojuka Bog, 1x Otawara, 1x Thragtusk
    "boros energy": 8.0,   # FON + Veil to protect combo
    "izzet prowess": 9.0,
    "goryo": 5.0,           # they're also combo, racing
    "breach": 5.0,
    "control": 10.0,        # Veil + FON shut down counters
    "azorius": 10.0,
    "jeskai": 9.0,
    "eldrazi": 6.0,         # Reclamation Sage + Endurance
    "tron": 5.0,
    "domain": 8.0,
    "mono red": 7.0,        # Thragtusk
}

ELDRAZI_TRON_SB = {
    # ETron SB: 3x Relic of Progenitus, 2x Warping Wail, 2x Dismember,
    #           2x All Is Dust, 2x Surgical Extraction, 2x Karn SB hate,
    #           1x Ulamog, 1x Endbringer
    "goryo": 12.0,          # Relic + Surgical
    "reanimator": 12.0,
    "boros energy": 7.0,    # Dismember + All Is Dust
    "domain": 7.0,
    "mono red": 8.0,        # All Is Dust sweeper
    "prowess": 8.0,
    "control": 5.0,
    "blink": 6.0,
    "breach": 10.0,         # Relic + Surgical stop the combo
    "neoform": 10.0,
}

DOMAIN_ZOO_SB = {
    # Domain SB: 3x Blood Moon, 2x Leyline of Sanctity, 2x Engineered Explosives,
    #            2x Wear/Tear, 2x Surgical Extraction, 2x Veil of Summer,
    #            1x Boseiju, 1x Flusterstorm
    "boros energy": 5.0,    # Leyline of Sanctity
    "tron": 12.0,           # Blood Moon
    "titan": 12.0,
    "breach": 11.0,
    "control": 8.0,         # Veil + Flusterstorm
    "reanimator": 9.0,      # Surgical + Veil
    "mono red": 6.0,        # Leyline of Sanctity
}

GORYO_VENGEANCE_SB = {
    # Esper Reanimator SB: 2x Force of Negation, 2x Thoughtseize,
    #                       2x Surgical Extraction, 2x Disallow,
    #                       2x Teferi ToT, 2x Counterspell, 1x Gideon
    "boros energy": 5.0,
    "mono red": 6.0,
    "control": 4.0,         # symmetrical — both board into the other
    "reanimator": 3.0,      # mirror — minimal delta
    "breach": 6.0,
    "neoform": 5.0,
}

NEOFORM_SB = {
    # Neoform SB: 4x Force of Negation, 2x Veil of Summer, 2x Pact of Negation,
    #             2x Endurance, 2x Boseiju, 2x Outland Liberator, 1x Haywire Mite
    "boros energy": 8.0,    # FON + Veil protect combo
    "control": 10.0,        # Veil + FON shut down counters
    "reanimator": 4.0,      # racing each other
    "eldrazi": 5.0,
    "domain": 7.0,
}

ESPER_MIDRANGE_SB = {
    # Esper Mid SB: typical — Surgical, Leyline of Sanctity, Rest in Peace,
    #               Dovin's Veto, Flusterstorm, Celestial Purge
    "goryo": 12.0,          # Rest in Peace + Surgical
    "reanimator": 11.0,
    "combo": 8.0,
    "prowess": 7.0,         # Leyline of Sanctity
    "mono red": 8.0,
    "control": 4.0,
    "blink": 4.0,
}

ESPER_BLINK_SB = {
    "goryo": 10.0,
    "reanimator": 10.0,
    "mono red": 8.0,
    "prowess": 7.0,
    "aggro": 7.0,
    "control": 3.0,
    "blink": 3.0,           # mirror
}

UW_BLINK_SB = {
    "goryo": 9.0,
    "reanimator": 9.0,
    "mono red": 9.0,
    "aggro": 8.0,
    "prowess": 7.0,
    "combo": 8.0,
    "control": 4.0,
    "blink": 3.0,           # mirror — Solitude + Ephemerate is still strong
}

JESKAI_CONTROL_SB = {
    "goryo": 10.0,          # Rest in Peace + Surgical
    "reanimator": 10.0,
    "neoform": 8.0,
    "mono red": 9.0,        # Anger of the Gods + Leyline
    "prowess": 9.0,
    "aggro": 9.0,
    "combo": 7.0,
    "blink": 5.0,
    "eldrazi": 6.0,
}

GRINDING_BREACH_SB = {
    # Grinding Station / Underworld Breach
    "boros energy": 7.0,    # FON + Veil
    "control": 9.0,
    "eldrazi": 6.0,
    "tron": 5.0,
    "reanimator": 3.0,      # racing
}

IZZET_PHOENIX_SB = {
    # Pioneer Phoenix SB: 3x Mystical Dispute, 2x Aether Gust, 2x Rest in Peace,
    #                      2x Negate, 2x Spell Pierce, 2x Young Pyromancer, 2x Saheeli
    "control": 9.0,         # Dispute + Negate
    "rakdos": 7.0,          # Aether Gust on Fable
    "jund": 8.0,
    "lotus": 8.0,           # Dispute + Pierce
    "mono green": 6.0,
    "humans": 5.0,
    "selesnya": 6.0,
}

RAKDOS_MIDRANGE_SB = {
    # Pioneer Rakdos SB: 3x Kalitas, 2x Leyline of the Void, 2x Abrade,
    #                     2x Collective Brutality, 2x Unlicensed Hearse, 2x Scooze
    "phoenix": 10.0,        # Leyline + Kalitas + Hearse
    "greasefang": 10.0,     # Leyline + Hearse
    "devotion": 5.0,
    "control": 5.0,
    "aggro": 7.0,           # Kalitas + Brutality
    "humans": 6.0,
}

DIMIR_MIDRANGE_SB = {
    "combo": 8.0,
    "aggro": 8.0,
    "mono red": 8.0,
    "prowess": 7.0,
    "control": 4.0,
    "midrange": 3.0,        # mirror — minimal delta
}

MONO_RED_SB = {
    # Burn SB: 3x Eidolon (already main), 2x Smash to Smithereens,
    #          2x Exquisite Firecraft, 2x Skullcrack, 2x Shard Volley,
    #          2x Price of Progress, 2x Searing Blood
    "control": 10.0,        # Exquisite Firecraft can't be countered
    "tron": 9.0,            # Price of Progress + Blood Moon SB
    "combo": 8.0,           # just race
    "blink": 7.0,
    "reanimator": 7.0,
    "aggro": 5.0,           # Searing Blood
    "mono red": 3.0,        # mirror
}


def get_sb_premium(deck_name: str, opp_name: str) -> float:
    """
    Look up SB premium from the pre-built tables.
    Falls back to a keyword-based generic estimate.
    """
    deck_tables = {
        "amulet titan":      AMULET_TITAN_SB,
        "eldrazi tron":      ELDRAZI_TRON_SB,
        "domain zoo":        DOMAIN_ZOO_SB,
        "goryo's vengeance": GORYO_VENGEANCE_SB,
        "goryo vengeance":   GORYO_VENGEANCE_SB,
        "neoform":           NEOFORM_SB,
        "esper midrange":    ESPER_MIDRANGE_SB,
        "esper blink":       ESPER_BLINK_SB,
        "uw blink":          UW_BLINK_SB,
        "jeskai control":    JESKAI_CONTROL_SB,
        "grinding breach":   GRINDING_BREACH_SB,
        "izzet phoenix":     IZZET_PHOENIX_SB,
        "rakdos midrange":   RAKDOS_MIDRANGE_SB,
        "dimir midrange":    DIMIR_MIDRANGE_SB,
        "mono red aggro":    MONO_RED_SB,
    }

    deck_key = deck_name.lower()
    for k, table in deck_tables.items():
        if k in deck_key or deck_key in k:
            opp_lower = opp_name.lower()
            for opp_key, premium in table.items():
                if opp_key in opp_lower:
                    return premium
            return 6.0   # not in table — generic

    return 6.0   # unknown deck
