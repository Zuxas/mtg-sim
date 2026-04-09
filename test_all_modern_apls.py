"""
test_all_modern_apls.py — Test every Modern field APL.
"""
import sys, os, traceback, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.deck import load_deck_from_file
from db_bridge import load_tournament_deck

MODERN_FIELD = [
    ("Boros Energy",      22.1, "apl.boros_energy",      "BorosEnergyAPL",     "decks/boros_energy_modern.txt"),
    ("Amulet Titan",       8.5, "apl.amulet_titan",      "AmuletTitanAPL",     "Amulet Titan"),
    ("Eldrazi Ramp",       7.4, "apl.eldrazi_tron",      "EldraziTronAPL",     "Gruul Eldrazi Ramp"),
    ("Izzet Prowess",      7.2, "apl.izzet_prowess",     "IzzetProwessAPL",    "Izzet Prowess"),
    ("Izzet Affinity",     6.8, "apl.izzet_affinity",    "IzzetAffinityAPL",   "Izzet Affinity"),
    ("Grinding Breach",    6.4, "apl.ruby_storm",        "RubyStormAPL",      "Teg"),
    ("Jeskai Blink",       6.4, "apl.generic_apl",       "GenericAPL",         "Jeskai Blink"),
    ("Orzhov Blink",       6.1, "apl.generic_apl",       "GenericAPL",         "Esper Blink"),
    ("Goryo's Vengeance",  5.6, "apl.goryo_vengeance",   "GoryoVengeanceAPL",  "Esper Reanimator"),
    ("Domain Zoo",         5.0, "apl.modern_domain_zoo", "ModernDomainZooAPL", "Domain Zoo"),
    ("Eldrazi Tron",       4.3, "apl.eldrazi_tron",      "EldraziTronAPL",     "Eldrazi Tron"),
    ("Mono Red Aggro",     4.1, "apl.burn",              "BurnAPL",            "Burn"),
    ("Temur Breach",       3.8, "apl.ruby_storm",        "RubyStormAPL",      "Teg"),
    ("Dimir Murktide",     3.5, "apl.dimir_murktide",    "MurktideAPL",        "Dimir Murktide"),
    ("Esper Blink",        2.8, "apl.esper_blink",       "EsperBlinkAPL",      "Esper Blink"),
]

def get_deck(name, db_archetype):
    if db_archetype.endswith(".txt") and os.path.exists(db_archetype):
        return load_deck_from_file(db_archetype)
    try:
        text = load_tournament_deck(db_archetype, "modern", top=32)
        safe = name.lower().replace("'", "").replace(" ", "_")
        path = f"decks/{safe}_modern.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return load_deck_from_file(path)
    except Exception as e:
        return None, None

def test_apl(name, pct, module_name, class_name, db_archetype, n_games=20):
    try:
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        apl = cls()
    except Exception as e:
        return f"IMPORT FAIL: {e}", None, None
    try:
        main, sb = get_deck(name, db_archetype)
        if main is None:
            return f"DECK FAIL", None, None
    except Exception as e:
        return f"DECK FAIL: {e}", None, None
    try:
        wins = 0
        total_kill = 0
        for seed in range(n_games):
            random.seed(seed + 2000)
            result = apl.run_game(mainboard=main, on_play=True)
            if result.won:
                wins += 1
                total_kill += result.kill_turn
        avg = total_kill / max(wins, 1)
        wr = 100 * wins / n_games
        return f"OK  {wr:>5.0f}% win, avg T{avg:.1f}", wins, avg
    except Exception as e:
        return f"RUN FAIL: {str(e)[:60]}", None, None

if __name__ == "__main__":
    print(f"\n{'%':>5}  {'Deck':<22} Result")
    print("=" * 70)
    for name, pct, mod, cls, db_arch in MODERN_FIELD:
        result, wins, avg = test_apl(name, pct, mod, cls, db_arch)
        print(f"{pct:>5.1f}  {name:<22} {result}")
