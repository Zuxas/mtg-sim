"""
format_config.py — Format-specific field data and combo kill distributions.
Field shares are from real tournament data in mtg_meta.db (see meta_bridge.py).
"""

FORMATS = {

"legacy": {
    "field": {
        "Dimir Reanimator": 22.4, "Lotus Combo": 10.5, "Dimir Tempo": 10.5,
        "Cephalid Breakfast": 7.5, "Eldrazi Stompy": 6.4, "Sneak And Show": 5.4,
        "Mono Red Painter": 5.0, "Doomsday": 4.9, "Izzet Delver": 4.7,
        "Death And Taxes": 4.6, "Bant Nadu": 4.3, "Four-Color": 3.7,
        "Jeskai Control": 3.6, "Mono Red Aggro": 3.4, "Mono Red Prison": 3.2,
    },
    "combo": {
        "dimir reanimator", "lotus combo", "cephalid breakfast",
        "sneak and show", "mono red painter", "doomsday", "bant nadu",
    },
    "combo_kill_dists": {
        "dimir reanimator":   {1: 5, 2: 40, 3: 35, 4: 15, 5: 5},
        "lotus combo":        {2: 5, 3: 30, 4: 40, 5: 20, 6: 5},
        "cephalid breakfast": {1: 2, 2: 30, 3: 45, 4: 18, 5: 5},
        "sneak and show":     {2: 10, 3: 40, 4: 35, 5: 10, 6: 5},
        "mono red painter":   {3: 20, 4: 40, 5: 30, 6: 10},
        "doomsday":           {2: 10, 3: 35, 4: 35, 5: 15, 6: 5},
        "bant nadu":          {3: 15, 4: 40, 5: 35, 6: 10},
    },
},

"modern": {
    # Field shares from MTGGoldfish 30-day snapshot 2026-04-29 (501-4 decks).
    # Only decks with working APLs included; launcher self-normalizes.
    # Covers ~72% of real meta. Dropped: Belcher/Neobrand/Grixis Rean/Temur Prowess
    # (no APLs), Dimir Murktide (0.2% real), Mono Red Aggro (absorbed into Izzet Prowess).
    "field": {
        "Boros Energy": 21.2, "Jeskai Blink": 10.6, "Affinity": 9.0,
        "Amulet Titan": 5.2,  "Ruby Storm": 4.1,    "Eldrazi Tron": 3.7,
        "Belcher": 3.5,       "Goryo's Vengeance": 3.5, "Domain Zoo": 3.4,
        "Neobrand": 3.2,      "Living End": 2.7,    "Grixis Reanimator": 2.3,
        "Dimir Midrange": 2.0, "Esper Blink": 1.8,  "Jeskai Control": 2.2,
        "Izzet Prowess": 1.7,  "Eldrazi Ramp": 1.6, "5C Humans": 1.5,
    },
    "combo": {
        "amulet titan", "goryo's vengeance", "ruby storm", "living end",
        "belcher", "neobrand", "grixis reanimator",
    },
    "combo_kill_dists": {
        "amulet titan":      {3: 15, 4: 45, 5: 30, 6: 10},
        "goryo's vengeance": {2: 15, 3: 45, 4: 30, 5: 10},
        "ruby storm":        {2: 10, 3: 35, 4: 40, 5: 15},
        "living end":        {3: 20, 4: 50, 5: 25, 6:  5},
        "belcher":           {2: 20, 3: 50, 4: 30},
        "neobrand":          {1: 30, 2: 50, 3: 20},
        "grixis reanimator": {2: 15, 3: 45, 4: 30, 5: 10},
    },
},

"standard": {
    # PT Lorwyn Eclipsed field (2026-05-04) — 306 players
    # Source: PT Lorwyn Eclipsed official results + meta-analyzer DB cross-ref
    # Major shift from PT SOS: Rhythm decks dominate (34.6% combined), Prowess fell.
    # Known exact shares: Simic 15.7%, Bant 15.0%, Sultai Rean 10.1%,
    #   Bant Airbending 6.5%, Spellementals 4.9%, Five-Color Rhythm 2.9%
    # Remaining shares estimated from post-PT meta data.
    "field": {
        "Simic Rhythm":          15.7,  # 48/306 — dominant, Nature's Rhythm engine
        "Bant Rhythm":           15.0,  # 46/306 — Seam Rip + Brightglass variant
        "Sultai Reanimator":     10.1,  # 31/306 — Bringer + Superior Spider-Man combo
        "Izzet Prowess":          9.5,  # ~29/306 — fell from 31.4% at SOS
        "Bant Airbending":        6.5,  # 20/306 — Aang/Appa finishers
        "Izzet Spellementals":    4.9,  # 15/306 — Sunderflock cost-reduction engine
        "Selesnya Landfall":      4.8,  # ~15/306 — PT SOS best deck, slightly down
        "Mono Green Landfall":    4.5,  # ~14/306 — Meltstrider + landfall chain
        "Five-Color Rhythm":      2.9,  #  9/306 — 5C Nature's Rhythm splash
        "Izzet Lessons":          3.5,  # ~11/306 — Zhang PT SOS winner, good matchup vs Rhythm
        "Grixis Elementals":      2.5,  #  ~8/306 — Filipe Sousa EMT list; Ashling+Sunderflock
        "Jeskai Control":         2.3,  #  ~7/306
        "Dimir Excruciator":      2.0,  #  ~6/306
        "Selesnya Ouroboroid":    1.8,  #  Nass PT SOS #2 seed
        "Azorius Momo":           1.5,  #  smaller presence post-Lorwyn
    },
    "combo": {
        "izzet cauldron", "jeskai oculus", "azorius omniscience",
        "sultai reanimator", "izzet lessons",
    },
    "combo_kill_dists": {
        "izzet cauldron":      {3: 10, 4: 35, 5: 35, 6: 15, 7: 5},
        "jeskai oculus":       {3: 15, 4: 40, 5: 35, 6: 10},
        "azorius omniscience": {4: 15, 5: 35, 6: 35, 7: 15},
        "sultai reanimator":   {2: 10, 3: 35, 4: 40, 5: 15},
        "izzet lessons":       {4: 20, 5: 40, 6: 30, 7: 10},
    },
},

"pioneer": {
    # Real field shares from Pioneer tournament data in DB
    "field": {
        "Izzet Prowess": 19.2, "Abzan Greasefang": 15.2, "Mono Red Aggro": 10.0,
        "Selesnya Company": 9.3, "Azorius Control": 8.3, "Izzet Phoenix": 6.3,
        "Rakdos Demons": 5.3, "Gruul Prowess": 4.4, "Golgari Midrange": 4.3,
        "Lotus Combo": 3.8, "Orzhov Midrange": 2.7, "Green Devotion": 1.8,
        "Izzet Lessons": 1.7, "Boros Convoke": 1.6, "5 Color Niv-Mizzet": 1.4,
    },
    "combo": {
        "lotus combo", "abzan greasefang",
        "green devotion", "izzet phoenix", "izzet lessons",
    },
    "combo_kill_dists": {
        "lotus combo":           {3: 10, 4: 35, 5: 35, 6: 15, 7: 5},
        "abzan greasefang":      {2: 10, 3: 40, 4: 35, 5: 15},
        "green devotion":        {3: 20, 4: 45, 5: 25, 6: 10},
        "izzet phoenix":         {3: 25, 4: 40, 5: 25, 6: 10},
        "izzet lessons":         {4: 20, 5: 40, 6: 30, 7: 10},
    },
},

}  # end FORMATS


def get_format(fmt):
    return FORMATS.get(fmt.lower())

def get_field(fmt, top_n=18):
    cfg = get_format(fmt)
    if not cfg:
        raise ValueError(f"Unknown format: {fmt}. Options: {list(FORMATS)}")
    return dict(sorted(cfg["field"].items(), key=lambda x: -x[1])[:top_n])

def is_combo(archetype, fmt):
    cfg = get_format(fmt)
    return cfg and archetype.lower() in cfg.get("combo", set())

def get_combo_dist(archetype, fmt):
    cfg = get_format(fmt)
    if not cfg:
        return {4: 50, 5: 30, 6: 20}
    return cfg.get("combo_kill_dists", {}).get(archetype.lower(), {4: 50, 5: 30, 6: 20})
