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
    # Real field shares from 53,269 tournament matches in DB
    "field": {
        "Boros Energy": 22.1, "Amulet Titan": 8.5, "Eldrazi Ramp": 7.4,
        "Izzet Prowess": 7.2, "Izzet Affinity": 6.8, "Grinding Breach": 6.4,
        "Jeskai Blink": 6.4, "Orzhov Blink": 6.1, "Goryo's Vengeance": 5.6,
        "Domain Zoo": 5.0, "Eldrazi Tron": 4.3, "Mono Red Aggro": 4.1,
        "Temur Breach": 3.8, "Dimir Murktide": 3.5, "Esper Blink": 2.8,
    },
    "combo": {
        "amulet titan", "goryo's vengeance", "grinding breach", "temur breach",
    },
    "combo_kill_dists": {
        "amulet titan":      {3: 15, 4: 45, 5: 30, 6: 10},
        "goryo's vengeance": {2: 15, 3: 45, 4: 30, 5: 10},
        "grinding breach":   {3: 20, 4: 40, 5: 30, 6: 10},
        "temur breach":      {3: 25, 4: 40, 5: 25, 6: 10},
    },
},

"standard": {
    # Real field shares from 60,658 tournament matches in DB
    "field": {
        "Izzet Prowess": 19.6, "Dimir Midrange": 12.8, "Mono Red Aggro": 12.2,
        "Izzet Cauldron": 6.5, "Jeskai Control": 6.3, "Izzet Lessons": 6.3,
        "Azorius Control": 5.7, "Esper Pixie": 5.2, "Gruul Aggro": 4.7,
        "Mono Green Landfall": 4.2, "Jeskai Oculus": 4.0,
        "Azorius Omniscience": 3.7, "Simic Ouroboroid": 3.4,
        "Boros Aggro": 2.9, "Sultai Reanimator": 2.5,
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
    # Real field shares from 13,298 tournament matches in DB
    "field": {
        "Izzet Phoenix": 17.3, "Azorius Control": 12.7, "Rakdos Aggro": 9.4,
        "Jund Sacrifice": 7.5, "Enigmatic Incarnation": 6.4, "Lotus Combo": 6.3,
        "Selesnya Company": 6.2, "Rakdos Midrange": 5.7,
        "Rakdos Transmogrify": 5.6, "Rakdos Demons": 5.3,
        "Rakdos Prowess": 5.0, "Mono Black Demons": 3.3,
        "Abzan Greasefang": 3.2, "Mono Green Devotion": 3.1, "5C Humans": 3.0,
    },
    "combo": {
        "lotus combo", "enigmatic incarnation", "abzan greasefang",
        "mono green devotion", "izzet phoenix",
    },
    "combo_kill_dists": {
        "lotus combo":           {3: 10, 4: 35, 5: 35, 6: 15, 7: 5},
        "enigmatic incarnation": {4: 20, 5: 40, 6: 30, 7: 10},
        "abzan greasefang":      {2: 10, 3: 40, 4: 35, 5: 15},
        "mono green devotion":   {3: 20, 4: 45, 5: 25, 6: 10},
        "izzet phoenix":         {3: 25, 4: 40, 5: 25, 6: 10},
    },
},

}  # end FORMATS


def get_format(fmt):
    return FORMATS.get(fmt.lower())

def get_field(fmt, top_n=15):
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
