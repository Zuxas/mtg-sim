import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generate_matchup_data import load_deck_and_apl

tests = [
    # Modern
    ("Boros Energy",      "modern"),
    ("Izzet Prowess",     "modern"),
    ("UW Blink",          "modern"),
    ("Esper Midrange",    "modern"),
    ("Esper Blink",       "modern"),
    ("Goryo Vengeance",   "modern"),
    ("Amulet Titan",      "modern"),
    ("Eldrazi Tron",      "modern"),
    ("Domain Zoo",        "modern"),
    ("Neoform",           "modern"),
    ("Jeskai Control",    "modern"),
    # Standard
    ("Dimir Midrange",    "standard"),
    ("Mono Red Aggro",    "standard"),
    # Pioneer
    ("Izzet Phoenix",     "pioneer"),
    ("Rakdos Midrange",   "pioneer"),
    # Legacy
    ("Legacy Humans",     "legacy"),
]

ok = 0; fail = 0
for deck, fmt in tests:
    try:
        main, _, apl = load_deck_and_apl(deck, fmt)
        if main and apl:
            print(f"  OK  {deck:<28} {len(main):>3} cards  APL: {apl.name}")
            ok += 1
        else:
            print(f"  ERR {deck:<28} no deck or APL")
            fail += 1
    except Exception as e:
        print(f"  ERR {deck:<28} {str(e)[:60]}")
        fail += 1

print(f"\n{ok}/{len(tests)} loaded  ({fail} failed)")
