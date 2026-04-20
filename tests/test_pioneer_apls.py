"""Test all Pioneer APLs."""
import sys, os, traceback, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.deck import load_deck_from_file

PIONEER_FIELD = [
    ("Izzet Prowess",       15.0, "apl.standard_aggro",  "StandardAggroAPL",  "decks/izzet_prowess_pioneer.txt"),
    ("Abzan Greasefang",    10.0, "apl.generic_apl",     "GenericAPL",        "decks/abzan_greasefang_pioneer.txt"),
    ("Mono Red Aggro",       9.0, "apl.burn",            "BurnAPL",           "decks/mono_red_aggro_pioneer.txt"),
    ("Selesnya Company",     7.0, "apl.generic_apl",     "GenericAPL",        "decks/selesnya_company_pioneer.txt"),
    ("Azorius Control",      6.5, "apl.generic_apl",     "GenericAPL",        "decks/azorius_control_pioneer.txt"),
    ("Izzet Phoenix",        6.0, "apl.generic_apl",     "GenericAPL",        "decks/izzet_phoenix_pioneer.txt"),
    ("Rakdos Demons",        5.5, "apl.generic_apl",     "GenericAPL",        "decks/rakdos_demons_pioneer.txt"),
    ("Gruul Prowess",        5.0, "apl.standard_aggro",  "StandardAggroAPL",  "decks/gruul_prowess_pioneer.txt"),
    ("Golgari Midrange",     4.5, "apl.generic_apl",     "GenericAPL",        "decks/golgari_midrange_pioneer.txt"),
    ("Lotus Combo",          4.0, "apl.generic_apl",     "GenericAPL",        "decks/lotus_combo_pioneer.txt"),
    ("Orzhov Midrange",      3.5, "apl.generic_apl",     "GenericAPL",        "decks/orzhov_midrange_pioneer.txt"),
    ("Green Devotion",       3.0, "apl.generic_apl",     "GenericAPL",        "decks/green_devotion_pioneer.txt"),
    ("Izzet Lessons",        2.5, "apl.generic_apl",     "GenericAPL",        "decks/izzet_lessons_pioneer.txt"),
    ("Boros Convoke",        2.0, "apl.standard_aggro",  "StandardAggroAPL",  "decks/boros_convoke_pioneer.txt"),
    ("5C Niv-Mizzet",        2.0, "apl.generic_apl",     "GenericAPL",        "decks/5_color_niv_mizzet_pioneer.txt"),
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
            random.seed(s + 5000)
            r = apl.run_game(mainboard=main, on_play=True)
            if r.won: w += 1; t += r.kill_turn
        avg = t / max(w, 1)
        return f"OK  {100*w//n:>3}% win, avg T{avg:.1f}"
    except Exception as e:
        return f"RUN: {str(e)[:50]}"

if __name__ == "__main__":
    print(f"\n{'%':>5}  {'Deck':<25} Result")
    print("=" * 65)
    for name, pct, mod, cls, path in PIONEER_FIELD:
        r = test(name, pct, mod, cls, path)
        print(f"{pct:>5.1f}  {name:<25} {r}")
