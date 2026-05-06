"""
scripts/rc_swiss_gauntlet.py -- Full Standard RC Swiss tournament simulation

Simulates a realistic Regional Championship:
  - Every registered Standard archetype (deduplicated by deck file)
  - 10-25 players per deck based on metagame share
  - Bo3 matchup matrix built from live run_match games
  - 8-round Swiss, multiple events to find stable EV
  - Reports: avg record, top8%, X-2%, field EV vs expectation

Usage:
    python scripts/rc_swiss_gauntlet.py [--games N] [--events N] [--cores N] [--rounds N]
"""
import sys, os, argparse, random
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from format_config import get_field
from engine.tournament import simulate_rc, print_rc_report, TournamentResult


# ── Canonical Standard deck roster ─────────────────────────────────────────
# Deduplicated: one entry per unique deck. Key = display name, value = registry key.
# Aliases and stubs excluded. Field share from PT Lorwyn Eclipsed + PT SOS 2026.
STANDARD_ROSTER = {
    # ── High-share PT Lorwyn Eclipsed archetypes ───
    "Simic Rhythm":          "simicrhythm",
    "Bant Rhythm":           "bantrhythm",
    "Sultai Reanimator":     "sultaireanimator",
    "Izzet Prowess":         "izzetprowessstandard",
    "Bant Airbending":       "bantairbending",
    "Izzet Spellementals":   "izzetspellementals",
    "Selesnya Landfall":     "selesnyalandfall",
    "Mono Green Landfall":   "monogreenlandfall",
    "Izzet Lessons":         "izzetlesson",
    "Five-Color Rhythm":     "fivecolorrhythm",
    "Grixis Elementals":     "grixiselementals",
    "Jeskai Control":        "jeskaicontrol",
    "Dimir Excruciator":     "dimirexcruciator",
    "Selesnya Ouroboroid":   "selesnyaouroboroid",
    "Azorius Momo":          "azoriusmomo",
    # ── PT SOS / fringe archetypes ────────────────
    "Esper Pixie":           "esperpixie",
    "Esper Raffine":         "esperraffine",
    "Azorius Control":       "azoriuscontrol",
    "Azorius Tempo":         "azoriustempo",
    "Azorius Blink":         "azoriusblink",
    "Golgari Midrange":      "golgarimidrange",
    "Golgari Kona":          "golgarikona",
    "Golgari Control":       "golgaricontrol",
    "Dimir Midrange":        "dimirmidrangestd",
    "Four-Color Control":    "fourcolorcontrol",
    "Four-Color Elemental":  "fourcolorelemental",
    "Four-Color Overlords":  "fourcoloroverlords",
    "Temur Lute":            "temurlute",
    "Selesnya Rhythm":       "selesnyarhythm",
    "Mardu Discard":         "mardudiscard",
    "Rakdos Discard":        "rakdosdiscard",
    "Boros Discard":         "borosdiscard",
    "Boros Dragons":         "borosdragons",
    "Gruul Aggro":           "gruulaggro",
    "Mono Green Aggro":      "monogreenaggro",
    "Simic Cub":             "simiccub",
    "Izzet Maestro":         "izzetmaestro",
    "Jeskai Oculus":         "jeskaioculus",
    "Domain Ramp":           "domainramp",
    "Roaming Elementals":    "roamingelementals",
    "Superior Doomsday":     "doomsday",
}

# Explicit field share overrides for decks not in format_config
# (fringe decks assumed ~0.5-1% each at a real RC)
FRINGE_SHARE = 0.8   # % per fringe deck


def _get_deck_file(key):
    """Return deck file path from APL_REGISTRY, or None."""
    from apl import APL_REGISTRY
    entry = APL_REGISTRY.get(key)
    if entry and isinstance(entry, tuple) and len(entry) >= 3:
        path = entry[2]
        if path and path.endswith('.txt') and os.path.exists(path):
            return path
    return None


def _build_field(valid_decks, field_shares, min_players=10, max_players=25):
    """
    Assign player counts per deck.
    Proportional to field share, floored at min_players, capped at max_players.
    Total player count is whatever results from the per-deck assignment.
    """
    # Get total share covered by valid decks
    total_share = sum(field_shares.get(name, FRINGE_SHARE) for name in valid_decks)

    # Assign proportional counts, apply floor/cap
    player_counts = {}
    for name in valid_decks:
        share = field_shares.get(name, FRINGE_SHARE)
        raw = (share / total_share) * len(valid_decks) * 15   # target ~15 avg
        count = max(min_players, min(max_players, round(raw)))
        player_counts[name] = count

    return player_counts


def _g1_to_bo3(p):
    """
    Convert G1 win probability p to Bo3 match win probability.
    Formula: p^2 * (3 - 2p) — exact for independent games with constant p.
    G2/G3 are assumed symmetric (sideboard effects approximated as wash
    given current Bo3 recursion bug in match_runner).
    """
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def _run_g1_matchup(args):
    """
    Worker: run N G1 games of deck_a vs deck_b (alternating on_play).
    Returns (name_a, name_b, wins, total).
    G1 WR is converted to Bo3 WR by caller via _g1_to_bo3().
    """
    name_a, key_a, name_b, key_b, n_games, seed_base = args

    from apl import get_match_apl, APL_REGISTRY
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    def load(key):
        deck_file = _get_deck_file(key)
        if not deck_file:
            return None, None
        try:
            deck, _ = load_deck_from_file(deck_file)
            apl = get_match_apl(key)
            return deck, apl
        except Exception:
            return None, None

    deck_a, apl_a = load(key_a)
    deck_b, apl_b = load(key_b)
    if deck_a is None or deck_b is None:
        return name_a, name_b, 0, 0

    wins = 0
    total = 0
    for i in range(n_games):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b,
                          seed=seed_base + i,
                          on_play=(i % 2 == 0))
            wins += 1 if r.won else 0
            total += 1
        except Exception:
            pass

    return name_a, name_b, wins, total


def main():
    ap = argparse.ArgumentParser(description="Full Standard RC Swiss gauntlet")
    ap.add_argument("--games",  type=int, default=200, help="G1 games per pairing (converted to Bo3 via p^2*(3-2p)")
    ap.add_argument("--events", type=int, default=2000, help="Swiss tournaments to simulate")
    ap.add_argument("--cores",  type=int, default=12)
    ap.add_argument("--rounds", type=int, default=8, help="Swiss rounds per event")
    ap.add_argument("--min-players", type=int, default=10)
    ap.add_argument("--max-players", type=int, default=25)
    args = ap.parse_args()

    field_shares = get_field("standard")

    # ── Validate roster: check deck files exist ──────────────────────────
    valid = {}     # display_name -> registry_key
    skipped = []
    seen_files = set()

    for name, key in STANDARD_ROSTER.items():
        deck_file = _get_deck_file(key)
        if deck_file is None:
            skipped.append(f"{name} ({key}): no deck file")
            continue
        # Skip duplicate deck files (aliases)
        if deck_file in seen_files:
            continue
        seen_files.add(deck_file)
        valid[name] = key

    if skipped:
        print(f"[SKIP] {len(skipped)} decks:")
        for s in skipped:
            print(f"  {s}")

    print(f"\nRoster: {len(valid)} unique Standard archetypes")

    # ── Assign player counts ──────────────────────────────────────────────
    player_counts = _build_field(valid, field_shares,
                                 args.min_players, args.max_players)
    total_players = sum(player_counts.values())
    print(f"Field:  {total_players} total players ({args.min_players}-{args.max_players} per deck)")
    print(f"\nDeck composition:")
    for name in sorted(valid, key=lambda n: -player_counts[n]):
        share = field_shares.get(name, FRINGE_SHARE)
        print(f"  {name:<28} {player_counts[name]:3d} players  ({share:.1f}% field)")

    # Build field_shares dict for tournament: fractions 0-1 (build_field expects this)
    tourney_field = {name: player_counts[name] / total_players
                     for name in valid}

    # ── Build Bo3 matchup matrix ──────────────────────────────────────────
    names = list(valid.keys())
    keys  = [valid[n] for n in names]
    n_pairs = len(names) * (len(names) - 1)
    print(f"\nBuilding matrix: {n_pairs} pairings x {args.games} G1 games -> Bo3 WR via p^2*(3-2p)")
    print(f"Total G1 games: ~{n_pairs * args.games:,}  Cores: {args.cores}")

    jobs = []
    for i, (na, ka) in enumerate(zip(names, keys)):
        for j, (nb, kb) in enumerate(zip(names, keys)):
            if i == j:
                continue
            seed_base = (i * 997 + j * 101 + 42) % 99991
            jobs.append((na, ka, nb, kb, args.games, seed_base))

    # {(name_a, name_b): bo3_match_wr_pct}
    matrix = {}
    completed = 0
    report_every = max(1, n_pairs // 25)

    with ProcessPoolExecutor(max_workers=args.cores) as pool:
        futures = {pool.submit(_run_g1_matchup, j): j for j in jobs}
        for fut in as_completed(futures):
            na, nb, w, t = fut.result()
            g1_wr = (w / t) if t > 0 else 0.5
            bo3_wr = _g1_to_bo3(g1_wr) * 100
            matrix[(na, nb)] = bo3_wr
            completed += 1
            if completed % report_every == 0:
                pct = completed / n_pairs * 100
                print(f"  {pct:5.1f}%  ({completed}/{n_pairs})", flush=True)

    print(f"\nMatrix complete. Running {args.events:,} Swiss events ({args.rounds} rounds each)...\n")

    # ── Run Swiss tournament simulation ───────────────────────────────────
    results = simulate_rc(
        field_shares=tourney_field,
        matrix=matrix,
        n_events=args.events,
        n_players=total_players,
        n_rounds=args.rounds,
        seed=42,
    )

    # ── Report ────────────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  RC SWISS GAUNTLET -- Standard  ({args.events:,} events, {args.rounds} rounds, "
          f"{total_players} players)")
    print(f"{'='*80}")
    print(f"  {'Deck':<28} {'Players':>7}  {'Avg Rec':>8}  {'Top8%':>6}  "
          f"{'X-1%':>6}  {'X-2%':>6}  {'EV':>6}")
    print(f"  {'-'*28} {'-'*7}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}")

    for r in results:
        pcount = player_counts.get(r.deck, 0)
        expected_top8 = 8 / total_players * 100
        ev_delta = r.top8_pct - expected_top8
        sign = "+" if ev_delta >= 0 else ""
        tag = ""
        if ev_delta > 8 and pcount < 15:
            tag = "  << UNDERPLAYED"
        elif ev_delta > 5:
            tag = "  << STRONG"
        elif ev_delta < -5 and pcount >= 15:
            tag = "  TRAP"
        rec = f"{r.avg_wins:.1f}-{r.avg_losses:.1f}"
        print(f"  {r.deck:<28} {pcount:>7}  {rec:>8}  {r.top8_pct:>5.1f}%  "
              f"{r.x1_pct:>5.1f}%  {r.x2_pct:>5.1f}%  {sign}{ev_delta:.1f}%{tag}")

    print(f"{'='*80}")
    print(f"\n  Expected top8 rate (random): {8/total_players*100:.1f}%")
    print(f"  Field-weighted avg record:   {sum(r.avg_wins for r in results)/len(results):.1f} wins\n")

    # ── Full matchup matrix ───────────────────────────────────────────────
    print("\n--- Bo3 Match WR matrix (row beats col % -- converted from G1 via p^2*(3-2p)) ---\n")
    cw = 7
    hdr = " " * 30
    for n in names:
        hdr += f" {n[:cw]:>{cw}}"
    print(hdr)
    for na in names:
        row = f"  {na:<28}"
        for nb in names:
            if na == nb:
                row += f" {'---':>{cw}}"
            else:
                wr = matrix.get((na, nb), 0.0)
                row += f" {wr:>{cw}.1f}%"
        print(row)
    print()


if __name__ == "__main__":
    main()
