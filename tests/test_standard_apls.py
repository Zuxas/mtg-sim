"""Test all Standard APLs."""
import sys, os, traceback, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.deck import load_deck_from_file

STANDARD_FIELD = [
    ("Dimir Midrange",      11.3, "apl.generic_apl",       "GenericAPL",         "decks/dimir_midrange_standard.txt"),
    ("Mono Red Aggro",      10.6, "apl.standard_aggro",    "StandardAggroAPL",   "decks/mono_red_aggro_standard.txt"),
    ("Esper Raffine",        7.9, "apl.generic_apl",       "GenericAPL",         "decks/esper_raffine_standard.txt"),
    ("Dimir Aggro",          7.7, "apl.standard_aggro",    "StandardAggroAPL",   "decks/dimir_aggro_standard.txt"),
    ("Izzet Prowess",        5.8, "apl.standard_aggro",    "StandardAggroAPL",   "decks/izzet_prowess_standard.txt"),
    ("Gruul Aggro",          5.0, "apl.standard_aggro",    "StandardAggroAPL",   "decks/gruul_aggro_standard.txt"),
    ("Domain Ramp",          4.6, "apl.generic_apl",       "GenericAPL",         "decks/domain_ramp_standard.txt"),
    ("Mono Green Landfall",  4.5, "apl.generic_apl",       "GenericAPL",         "decks/mono_green_landfall_standard.txt"),
    ("Boros Aggro",          4.3, "apl.standard_aggro",    "StandardAggroAPL",   "decks/boros_aggro_standard.txt"),
    ("Grixis Discard",       3.9, "apl.generic_apl",       "GenericAPL",         "decks/grixis_discard_standard.txt"),
    ("Izzet Lessons",        3.8, "apl.generic_apl",       "GenericAPL",         "decks/izzet_lessons_standard.txt"),
    ("Esper Pixie",          3.6, "apl.generic_apl",       "GenericAPL",         "decks/esper_pixie_standard.txt"),
    ("Four-Color Overlords", 3.4, "apl.generic_apl",       "GenericAPL",         "decks/four_color_overlords_standard.txt"),
    ("Izzet Cauldron",       3.2, "apl.generic_apl",       "GenericAPL",         "decks/izzet_cauldron_standard.txt"),
]

def test(name, pct, mod, cls, deck_path, n=20):
    try:
        m = __import__(mod, fromlist=[cls])
        apl = getattr(m, cls)()
    except Exception as e:
        return f"IMPORT: {e}"
    try:
        main, sb = load_deck_from_file(deck_path)
    except Exception as e:
        return f"DECK: {e}"
    try:
        w = 0; t = 0
        for s in range(n):
            random.seed(s + 3000)
            r = apl.run_game(mainboard=main, on_play=True)
            if r.won: w += 1; t += r.kill_turn
        avg = t / max(w, 1)
        return f"OK  {100*w//n:>3}% win, avg T{avg:.1f}"
    except Exception as e:
        return f"RUN: {str(e)[:50]}"

if __name__ == "__main__":
    print(f"\n{'%':>5}  {'Deck':<25} Result")
    print("=" * 65)
    for name, pct, mod, cls, path in STANDARD_FIELD:
        r = test(name, pct, mod, cls, path)
        print(f"{pct:>5.1f}  {name:<25} {r}")
