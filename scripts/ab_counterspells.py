"""A/B test: Dimir Jermey WR with vs without the counterspell resolver.

The resolver is wired into engine.game_state.cast_spell. To disable for
the B run, we monkeypatch try_counter_spell to return False before any
match runs. Same seeds for both arms -- WR delta measures the resolver's
impact on tempo matchups.

Counter-heavy field: Izzet Lessons, Spellementals, Prowess, Jeskai
Control, Selesnya Landfall (lots of cheap noncreature spells).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Counter-relevant matchups (lots of noncreature spells = many windows)
MATCHUPS = [
    ("Izzet Prowess",       "izzetprowessstandard",  "decks/izzet_prowess_standard.txt"),
    ("Izzet Lessons",       "izzetlesson",            "decks/izzet_lesson_standard.txt"),
    ("Izzet Spellementals", "izzetspellementals",     "decks/izzet_spellementals_standard.txt"),
    ("Jeskai Control",      "jeskaicontrol",          "decks/jeskai_control_standard.txt"),
    ("Selesnya Landfall",   "selesnyalandfall",       "decks/selesnya_landfall_standard.txt"),
    ("Mono Green Landfall", "monogreenlandfall",      "decks/mono_green_landfall_standard.txt"),
    ("Sultai Reanimator",   "sultaireanimator",       "decks/sultai_reanimator_standard.txt"),
    ("Gruul Aggro",         "gruulaggro",             "decks/gruul_aggro_standard.txt"),
]
DECK = "decks/dimir_midrange_jermey_standard.txt"
APL_KEY = "dimirmidrangejermey"
GAMES = 500  # bigger N -- noise floor at 100 was masking small WR shifts


def run_arm(disable_counters: bool):
    """Run the gauntlet. If disable_counters, no-op the resolver."""
    import engine.counter_resolver as cr
    if disable_counters:
        cr.try_counter_spell = lambda *a, **kw: False

    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    apl_a = get_match_apl(APL_KEY)
    deck_a, _ = load_deck_from_file(DECK)
    results = {}

    for name, opp_key, opp_path in MATCHUPS:
        try:
            apl_b = get_match_apl(opp_key)
        except Exception as e:
            print(f"  {name:<22} SKIP (no APL: {e})")
            continue
        deck_b, _ = load_deck_from_file(opp_path)
        wins = 0
        t0 = time.time()
        for s in range(GAMES):
            try:
                r = run_match(apl_a, deck_a, apl_b, deck_b,
                              seed=s, on_play=(s % 2 == 0))
                if r.won:
                    wins += 1
            except Exception:
                pass
        results[name] = (wins, time.time() - t0)
    return results


def main():
    arm = sys.argv[1] if len(sys.argv) > 1 else "with"
    if arm not in ("with", "without"):
        print("usage: ab_counterspells.py [with|without]")
        sys.exit(1)

    disable = (arm == "without")
    print(f"\n=== ARM: {'WITHOUT' if disable else 'WITH'} counterspell resolver ===")
    print(f"Deck: {DECK} ({GAMES}g/matchup, total {GAMES * len(MATCHUPS)} games)\n")

    res = run_arm(disable)
    for name, _, _ in MATCHUPS:
        if name in res:
            w, dt = res[name]
            print(f"  {name:<22} {w:>3}/{GAMES} = {w*100/GAMES:>5.1f}%  ({dt:>5.1f}s)")
    avg_wr = sum(w for w, _ in res.values()) / (GAMES * len(res)) * 100
    print(f"\n  Avg WR: {avg_wr:.1f}%  ({sum(dt for _, dt in res.values()):.1f}s total)")


if __name__ == "__main__":
    main()
