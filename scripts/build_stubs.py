"""
build_stubs.py — Generate stub_decks.py with real decklists + hardcoded Standard/Pioneer stubs.
"""
import sys, os, json, re, sqlite3
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

DB = os.path.join(_ROOT, '..', 'mtg-meta-analyzer', 'data', 'mtg_meta.db')
conn = sqlite3.connect(DB)
cur  = conn.cursor()
cur.execute("SELECT id, name, format, archetype, mainboard FROM saved_decks ORDER BY id")
rows = cur.fetchall()
conn.close()

def make_key(name, arch):
    raw = arch if arch and arch not in ('', 'unknown') else name
    raw = re.sub(r'\s*\(gauntlet\s+\w+\)', '', raw, flags=re.IGNORECASE).strip()
    return raw.lower().replace(' ', '_').replace("'", '').replace('/', '_').replace('-', '_')

# De-duplicate: prefer lower id (first entry)
seen = {}
entries = []
for did, name, fmt, arch, mb_json in rows:
    key = make_key(name, arch)
    if key not in seen:
        seen[key] = True
        entries.append((key, name, fmt, arch, json.loads(mb_json)))

# Hardcoded stubs for Standard/Pioneer archetypes not in saved_decks
EXTRA_STUBS = {
    "mono_red_aggro_standard": {
        "format": "standard",
        "mainboard": {
            "Monastery Swiftspear": 4, "Goblin Guide": 4,
            "Cacophony Scamp": 4, "Lightning Bolt": 4,
            "Slickshot Show-Off": 4, "Dragon's Rage Channeler": 4,
            "Lava Dart": 4, "Mutagenic Growth": 4,
            "Galvanic Discharge": 4, "Felonious Rage": 2,
            "Mountain": 16, "Arid Mesa": 4, "Bloodstained Mire": 2,
        }
    },
    "izzet_phoenix": {
        "format": "pioneer",
        "mainboard": {
            "Arclight Phoenix": 4, "Sprite Dragon": 4,
            "Dragon's Rage Channeler": 4, "Ledger Shredder": 4,
            "Consider": 4, "Fiery Impulse": 4,
            "Lightning Bolt": 4, "Strategic Planning": 4,
            "Expressive Iteration": 4, "Treasure Cruise": 2,
            "Steam Vents": 4, "Spirebluff Canal": 4,
            "Shivan Reef": 4, "Island": 3, "Mountain": 3,
            "Riverglide Pathway": 3,
        }
    },
    "rakdos_midrange": {
        "format": "pioneer",
        "mainboard": {
            "Thoughtseize": 4, "Fatal Push": 4,
            "Fable of the Mirror-Breaker": 4,
            "Graveyard Trespasser": 4, "Bloodtithe Harvester": 4,
            "Sheoldred, the Apocalypse": 3, "Invoke Despair": 3,
            "Dreadbore": 2, "Kolaghan's Command": 2,
            "Reckoner Bankbuster": 2, "Preordain": 2,
            "Blood Crypt": 4, "Blightstep Pathway": 4,
            "Haunted Ridge": 4, "Swamp": 3, "Mountain": 2,
            "Sulfurous Springs": 3,
        }
    },
    "izzet_prowess_standard": {
        "format": "standard",
        "mainboard": {
            "Monastery Swiftspear": 4, "Dragon's Rage Channeler": 4,
            "Slickshot Show-Off": 4, "Cori-Steel Cutter": 4,
            "Lightning Bolt": 4, "Lava Dart": 4,
            "Mishra's Bauble": 4, "Mutagenic Growth": 4,
            "Expressive Iteration": 4,
            "Steam Vents": 4, "Mountain": 6,
            "Island": 3, "Scalding Tarn": 4,
            "Bloodstained Mire": 3,
        }
    },
    "dimir_midrange": {
        "format": "standard",
        "mainboard": {
            "Psychic Frog": 4, "Thoughtseize": 4,
            "Fatal Push": 4, "Overlord of the Balemurk": 4,
            "Raffine, Scheming Seer": 3, "Sheoldred, the Apocalypse": 2,
            "Consider": 4, "Preordain": 4,
            "Boggart Trawler": 2, "Emperor of Bones": 1,
            "Watery Grave": 4, "Underground River": 4,
            "Shadowy Backstreet": 2, "Swamp": 3, "Island": 2,
            "Flooded Strand": 4, "Polluted Delta": 3,
        }
    },
    "5c_humans": {
        "format": "pioneer",
        "mainboard": {
            "Champion of the Parish": 4, "Thalia's Lieutenant": 4,
            "Kitesail Freebooter": 4, "Mantis Rider": 4,
            "Reflector Mage": 4, "Mayor of Avabruck": 4,
            "Coppercoat Vanguard": 4, "General Kudro of Drannith": 3,
            "Cavern of Souls": 4, "Unclaimed Territory": 4,
            "Seachrome Coast": 4, "Sacred Foundry": 2,
            "Hallowed Fountain": 2, "Stomping Ground": 2,
            "Temple Garden": 2, "Plains": 3, "Forest": 2,
        }
    },
    "dimir_murktide": {
        "format": "modern",
        "mainboard": {
            "Murktide Regent": 4, "Psychic Frog": 4, "Snapcaster Mage": 2,
            "Fatal Push": 4, "Force of Negation": 4, "Thoughtseize": 4,
            "Counterspell": 4, "Consider": 4, "Preordain": 4,
            "Expressive Iteration": 2, "Flooded Strand": 4,
            "Polluted Delta": 4, "Watery Grave": 2, "Underground River": 2,
            "Island": 3, "Swamp": 2, "Otawara, Soaring City": 1,
        }
    },
    "gruul_aggro": {
        "format": "standard",
        "mainboard": {
            "Monastery Swiftspear": 4, "Questing Druid": 4,
            "Emberheart Challenger": 4, "Monstrous Rage": 4,
            "Lightning Strike": 4, "Might of the Meek": 4,
            "Shock": 4, "Cacophony Scamp": 4, "Pawpatch Formation": 2,
            "Brushland": 4, "Karplusan Forest": 4,
            "Forest": 5, "Mountain": 5, "Copperline Gorge": 4,
        }
    },
    "boros_aggro": {
        "format": "standard",
        "mainboard": {
            "Emberheart Challenger": 4, "Monastery Swiftspear": 4,
            "Ocelot Pride": 4, "Ajani, Nacatl Pariah": 4,
            "Guide of Souls": 4, "Monstrous Rage": 4,
            "Shock": 4, "Lightning Strike": 4,
            "Sacred Foundry": 4, "Inspiring Vantage": 4,
            "Plains": 5, "Mountain": 5, "Sundown Pass": 4,
        }
    },
    "simic_ouroboroid": {
        "format": "standard",
        "mainboard": {
            "Aether Channeler": 4, "Preordain": 4, "Consider": 4,
            "Expressive Iteration": 4, "Questing Druid": 4,
            "Growth Spiral": 4, "Hullbreacher": 3, "Deeproot Elite": 3,
            "Merfolk Mistbinder": 4, "Svyelun of Sea and Sky": 3,
            "Breeding Pool": 4, "Misty Rainforest": 4,
            "Forest": 4, "Island": 4, "Botanical Sanctum": 4,
        }
    },
    "rakdos_aggro": {
        "format": "pioneer",
        "mainboard": {
            "Monastery Swiftspear": 4, "Thoughtseize": 4,
            "Bloodtithe Harvester": 4, "Fable of the Mirror-Breaker": 4,
            "Lightning Strike": 4, "Fatal Push": 4,
            "Obliterating Bolt": 4, "Cacophony Scamp": 4,
            "Emberheart Challenger": 4, "Preordain": 2,
            "Blood Crypt": 4, "Blightstep Pathway": 4,
            "Mountain": 4, "Swamp": 2, "Sulfurous Springs": 4,
        }
    },
    "rakdos_transmogrify": {
        "format": "pioneer",
        "mainboard": {
            "Transmogrify": 4, "Fable of the Mirror-Breaker": 4,
            "Thoughtseize": 4, "Fatal Push": 4, "Invoke Despair": 3,
            "Atraxa, Grand Unifier": 2, "Ulamog, the Ceaseless Hunger": 2,
            "Bloodtithe Harvester": 4, "Preordain": 3,
            "Blood Crypt": 4, "Blightstep Pathway": 4,
            "Haunted Ridge": 3, "Swamp": 3, "Mountain": 3,
            "Sulfurous Springs": 3, "Shivan Reef": 3,
        }
    },
    "rakdos_demons": {
        "format": "pioneer",
        "mainboard": {
            "Archfiend of the Dross": 4, "Bloodtithe Harvester": 4,
            "Overlord of the Balemurk": 4, "Thoughtseize": 4,
            "Fatal Push": 4, "Fable of the Mirror-Breaker": 4,
            "Invoke Despair": 3, "Dreadbore": 2,
            "Blood Crypt": 4, "Blightstep Pathway": 4,
            "Haunted Ridge": 3, "Swamp": 4, "Mountain": 3,
            "Sulfurous Springs": 3, "Blackcleave Cliffs": 2,
        }
    },
    "rakdos_prowess": {
        "format": "pioneer",
        "mainboard": {
            "Monastery Swiftspear": 4, "Dragon's Rage Channeler": 4,
            "Thoughtseize": 4, "Lightning Bolt": 4, "Fatal Push": 4,
            "Mutagenic Growth": 4, "Lava Dart": 4, "Mishra's Bauble": 4,
            "Reckless Lackey": 4,
            "Blood Crypt": 4, "Blightstep Pathway": 4,
            "Mountain": 4, "Swamp": 2, "Sulfurous Springs": 4,
        }
    },
    "mono_black_demons": {
        "format": "pioneer",
        "mainboard": {
            "Archfiend of the Dross": 4, "Overlord of the Balemurk": 4,
            "Sire of Seven Deaths": 4, "Thoughtseize": 4,
            "Fatal Push": 4, "Invoke Despair": 4,
            "Sheoldred, the Apocalypse": 3, "Reckoner Bankbuster": 3,
            "Swamp": 16, "Field of Ruin": 4, "Castle Locthwain": 4,
        }
    },
    "jund_sacrifice": {
        "format": "pioneer",
        "mainboard": {
            "Cauldron Familiar": 4, "Witch's Oven": 4, "Mayhem Devil": 4,
            "Korvold, Fae-Cursed King": 3, "Fatal Push": 4,
            "Thoughtseize": 4, "Fiend Artisan": 4, "Prosperous Innkeeper": 3,
            "Collected Company": 2, "Overgrown Tomb": 4,
            "Blood Crypt": 3, "Stomping Ground": 2,
            "Swamp": 3, "Forest": 3, "Mountain": 2, "Blightstep Pathway": 3,
        }
    },
    "selesnya_company": {
        "format": "pioneer",
        "mainboard": {
            "Collected Company": 4, "Llanowar Elves": 4, "Elvish Mystic": 4,
            "Knight of Autumn": 4, "Voice of Resurgence": 4,
            "Werewolf Pack Leader": 4, "Loran of the Third Path": 3,
            "Questing Beast": 2, "Blade Splicer": 3,
            "Temple Garden": 4, "Sunpetal Grove": 4,
            "Forest": 6, "Plains": 4, "Razorverge Thicket": 3,
        }
    },
    # ── Legacy fair decks ─────────────────────────────────────────────────
    "dimir_tempo": {
        "format": "legacy",
        "mainboard": {
            "Murktide Regent": 4, "Dragon's Rage Channeler": 4,
            "Force of Will": 4, "Daze": 4, "Brainstorm": 4,
            "Ponder": 4, "Consider": 2, "Preordain": 2,
            "Fatal Push": 4, "Expressive Iteration": 2,
            "Mishra's Bauble": 4,
            "Polluted Delta": 4, "Flooded Strand": 2,
            "Volcanic Island": 2, "Underground Sea": 2,
            "Island": 4, "Swamp": 2,
        }
    },
    "eldrazi_stompy": {
        "format": "legacy",
        "mainboard": {
            "Thought-Knot Seer": 4, "Reality Smasher": 4,
            "Eldrazi Mimic": 4, "Endless One": 4,
            "Matter Reshaper": 4, "Endbringer": 2,
            "Chalice of the Void": 4, "Trinisphere": 2,
            "Umezawa's Jitte": 2, "Dismember": 3,
            "Ancient Tomb": 4, "City of Traitors": 4,
            "Eldrazi Temple": 4, "Eye of Ugin": 4,
            "Cavern of Souls": 4, "Wastes": 4,
        }
    },
    "izzet_delver": {
        "format": "legacy",
        "mainboard": {
            "Delver of Secrets": 4, "Dragon's Rage Channeler": 4,
            "Murktide Regent": 2, "Force of Will": 4,
            "Daze": 4, "Brainstorm": 4, "Ponder": 4,
            "Lightning Bolt": 4, "Chain Lightning": 2,
            "Expressive Iteration": 2, "Mishra's Bauble": 4,
            "Volcanic Island": 4, "Scalding Tarn": 4,
            "Flooded Strand": 4, "Island": 4,
        }
    },
    "death_and_taxes": {
        "format": "legacy",
        "mainboard": {
            "Thalia, Guardian of Thraben": 4,
            "Recruiter of the Guard": 3,
            "Stoneforge Mystic": 4,
            "Sanctum Prelate": 2, "Palace Jailer": 2,
            "Mother of Runes": 4, "Phelia, Exuberant Shepherd": 4,
            "Aether Vial": 4, "Batterskull": 1, "Umezawa's Jitte": 1,
            "Swords to Plowshares": 4,
            "Karakas": 4, "Rishadan Port": 4, "Wasteland": 4,
            "Plains": 8,
        }
    },
    "four_color": {
        "format": "legacy",
        "mainboard": {
            "Orcish Bowmasters": 4, "Psychic Frog": 4,
            "Murktide Regent": 2, "Bowmasters": 2,
            "Force of Will": 4, "Brainstorm": 4, "Ponder": 4,
            "Thoughtseize": 4, "Fatal Push": 4,
            "Expressive Iteration": 2, "Mishra's Bauble": 2,
            "Volcanic Island": 2, "Underground Sea": 2,
            "Tropical Island": 1, "Bayou": 1,
            "Polluted Delta": 4, "Scalding Tarn": 4,
            "Flooded Strand": 4, "Island": 2,
        }
    },
    "mono_red_prison": {
        "format": "legacy",
        "mainboard": {
            "Goblin Rabblemaster": 4, "Magus of the Moon": 4,
            "Eidolon of the Great Revel": 4, "Monastery Swiftspear": 4,
            "Blood Moon": 4, "Chalice of the Void": 4,
            "Trinisphere": 3, "Fiery Islet": 4,
            "Simian Spirit Guide": 4, "Chrome Mox": 4,
            "Recruiter of the Guard": 2,
            "Ancient Tomb": 4, "City of Traitors": 4,
            "Mountain": 7,
        }
    },
}

out_path = 'data/stub_decks.py'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""data/stub_decks.py — Real + hardcoded stub decklists.\nAuto-generated by build_stubs.py.\n"""\n\n')
    f.write('_DB_DECKS = {\n')
    for key, name, fmt, arch, mb in entries:
        f.write(f'    # {name} ({fmt})\n')
        f.write(f'    "{key}": {{"format": "{fmt}", "mainboard": {json.dumps(mb, ensure_ascii=True)}}},\n')
    for key, v in EXTRA_STUBS.items():
        f.write(f'    # Extra stub: {key}\n')
        f.write(f'    "{key}": {{"format": "{v["format"]}", "mainboard": {json.dumps(v["mainboard"], ensure_ascii=True)}}},\n')
    f.write('}\n\n\n')
    f.write('''def get_stub_deck_list(deck_name: str):
    import re
    key = deck_name.lower().replace(" ","_").replace("'","").replace("/","_").replace("-","_")
    key = re.sub(r"_\\(gauntlet_\\w+\\)", "", key).strip("_")
    if key in _DB_DECKS: return _DB_DECKS[key]["mainboard"]
    for k, v in _DB_DECKS.items():
        if k == key or k.startswith(key) or key.startswith(k[:max(4,len(key)-4)]):
            return v["mainboard"]
    return None

def get_format_decks(fmt): return {k:v for k,v in _DB_DECKS.items() if v["format"]==fmt}
''')

total = len(entries) + len(EXTRA_STUBS)
print(f"Generated {out_path}: {len(entries)} from DB + {len(EXTRA_STUBS)} extra = {total} total")
for key, *_ in entries: print(f"  DB    {key}")
for key in EXTRA_STUBS: print(f"  EXTRA {key}")
