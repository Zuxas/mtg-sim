"""
format_config.py — Format-specific field data and combo kill distributions

Single source of truth for:
  - Field shares per format (top archetypes by meta share)
  - Which archetypes are combo (use kill-turn sampler instead of combat sim)
  - Combo kill distributions per archetype
  - Our deck's kill turn distribution (goldfish, used in combo model)

Add new formats here. Each entry in FORMATS contains:
  - "field":  {Archetype: field_share_pct}
  - "combo":  set of lowercase archetype names that kill via combo
  - "our_kill_dist": {turn: weight} for the deck we're playing
  - "our_sb": {archetype: {"in": [...], "out": [...], "hard_stops": set()}}
"""

FORMATS = {

# ─────────────────────────────────────────────────────────────────────────────
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
        "dimir reanimator":    {1: 5, 2: 40, 3: 35, 4: 15, 5: 5},
        "lotus combo":         {2: 5, 3: 30, 4: 40, 5: 20, 6: 5},
        "cephalid breakfast":  {1: 2, 2: 30, 3: 45, 4: 18, 5: 5},
        "sneak and show":      {2: 10, 3: 40, 4: 35, 5: 10, 6: 5},
        "mono red painter":    {3: 20, 4: 40, 5: 30, 6: 10},
        "doomsday":            {2: 10, 3: 35, 4: 35, 5: 15, 6: 5},
        "bant nadu":           {3: 15, 4: 40, 5: 35, 6: 10},
    },
},

# ─────────────────────────────────────────────────────────────────────────────
"modern": {
    "field": {
        "Boros Energy":         18.2, "Dimir Murktide":      11.3,
        "Amulet Titan":         8.7,  "Living End":           7.2,
        "Golgari Yawgmoth":     6.8,  "Izzet Prowess":        6.1,
        "Domain Zoo":           5.9,  "Temur Rhinos":         5.4,
        "Mono Black Necro":     4.8,  "Jeskai Control":       4.3,
        "Goryo Vengeance":      3.9,  "Urza Thopter":         3.5,
        "Storm":                3.2,  "Tron":                 2.8,
        "Hardened Scales":      2.4,
    },
    "combo": {
        "amulet titan", "living end", "goryo vengeance",
        "storm", "temur rhinos", "urza thopter",
    },
    "combo_kill_dists": {
        "amulet titan":    {3: 15, 4: 45, 5: 30, 6: 10},
        "living end":      {3: 30, 4: 45, 5: 20, 6: 5},
        "goryo vengeance": {2: 15, 3: 45, 4: 30, 5: 10},
        "storm":           {3: 25, 4: 40, 5: 25, 6: 10},
        "temur rhinos":    {3: 20, 4: 40, 5: 30, 6: 10},
        "urza thopter":    {4: 25, 5: 40, 6: 25, 7: 10},
    },
},

# ─────────────────────────────────────────────────────────────────────────────
"pioneer": {
    "field": {
        "Lotus Field Combo":    16.8, "Izzet Phoenix":       12.4,
        "Azorius Spirits":      9.3,  "Rakdos Midrange":      8.7,
        "Boros Heroic":         7.5,  "Mono White Humans":    6.9,
        "Green Devotion":       6.2,  "Dimir Rogues":         5.4,
        "Hidden Strings":       4.8,  "Abzan Greasefang":     4.3,
        "Boros Convoke":        3.7,  "Azorius Control":      3.6,
        "Rakdos Sacrifice":     3.2,  "Mono Red Aggro":       3.0,
        "Gruul Vehicles":       2.8,
    },
    "combo": {
        "lotus field combo", "hidden strings", "abzan greasefang",
        "green devotion", "izzet phoenix",
    },
    "combo_kill_dists": {
        "lotus field combo": {3: 10, 4: 35, 5: 35, 6: 15, 7: 5},
        "hidden strings":    {3: 20, 4: 40, 5: 30, 6: 10},
        "abzan greasefang":  {2: 10, 3: 40, 4: 35, 5: 15},
        "green devotion":    {3: 20, 4: 45, 5: 25, 6: 10},
        "izzet phoenix":     {3: 25, 4: 40, 5: 25, 6: 10},
    },
},

# ─────────────────────────────────────────────────────────────────────────────
"standard": {
    "field": {
        "Azorius Oculus":       15.3, "Dimir Midrange":      13.8,
        "Mono Red Aggro":       11.2, "Esper Pixie":         10.4,
        "Boros Convoke":        8.7,  "Orzhov Lifegain":      7.5,
        "Temur Ramp":           6.8,  "Golgari Midrange":     6.1,
        "Domain Control":       5.4,  "Gruul Aggro":          4.8,
        "Azorius Soldiers":     4.2,  "Rakdos Midrange":      3.6,
        "Selesnya Enchantments":2.8,  "Izzet Prowess":        2.4,
        "Mono White Humans":    2.2,
    },
    "combo": {
        "azorius oculus",   # Oculus + looting combo
        "esper pixie",      # Pixie chain
    },
    "combo_kill_dists": {
        "azorius oculus": {3: 10, 4: 35, 5: 35, 6: 15, 7: 5},
        "esper pixie":    {4: 20, 5: 40, 6: 30, 7: 10},
    },
},

}


def get_format(fmt: str) -> dict:
    """Get format config. Returns None if not found."""
    return FORMATS.get(fmt.lower())


def get_field(fmt: str, top_n: int = 15) -> dict:
    """Get top-N field shares for a format."""
    cfg = get_format(fmt)
    if not cfg:
        raise ValueError(f"Unknown format: {fmt}. Options: {list(FORMATS)}")
    field = cfg["field"]
    sorted_f = sorted(field.items(), key=lambda x: -x[1])
    return dict(sorted_f[:top_n])


def is_combo(archetype: str, fmt: str) -> bool:
    cfg = get_format(fmt)
    if not cfg:
        return False
    return archetype.lower() in cfg.get("combo", set())


def get_combo_dist(archetype: str, fmt: str) -> dict:
    cfg = get_format(fmt)
    if not cfg:
        return {4: 50, 5: 30, 6: 20}
    dists = cfg.get("combo_kill_dists", {})
    key = archetype.lower()
    return dists.get(key, {4: 50, 5: 30, 6: 20})
