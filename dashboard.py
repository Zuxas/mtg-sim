"""
dashboard.py — Multi-format matchup dashboard
Reads all parallel_results JSON files and prints a clean summary per format.

Usage:
    python dashboard.py                 # show latest run per format
    python dashboard.py --all           # show all historical runs
    python dashboard.py --deck "Boros Energy"
"""
import sys, os, json, glob, argparse
sys.path.insert(0, '.')

def latest_result_per_deck() -> dict:
    """Return {deck+format: result_dict} for most recent run of each deck."""
    files = sorted(glob.glob('data/parallel_results_*.json'), reverse=True)
    seen  = {}
    for f in files:
        with open(f) as fh:
            d = json.load(fh)
        key = f"{d.get('our_deck','')}_{d.get('format','')}"
        if key not in seen:
            seen[key] = d
    return seen


def print_run(d: dict, verbose: bool = False):
    deck    = d.get('our_deck', '?')
    fmt     = d.get('format', '?').upper()
    fw      = d.get('field_weighted_match', 0)
    elapsed = d.get('elapsed_s', 0)
    results = d.get('results', [])
    ok      = [r for r in results if not r.get('error')]
    errors  = [r for r in results if r.get('error')]

    print(f"\n{'═'*68}")
    print(f"  {deck}  ({fmt})  —  {fw:.1f}% field-weighted match win%  [{elapsed:.0f}s]")
    print(f"  {len(ok)} matchups  |  {len(errors)} errors  |  {sum(r.get('n',0) for r in ok):,} games")
    print(f"{'═'*68}")

    # Sort by field share
    for r in sorted(ok, key=lambda x: -x.get('field_pct', 0)):
        opp   = r.get('opp', '?')
        fp    = r.get('field_pct', 0)
        g1    = r.get('g1', 0)
        g2    = r.get('g2', 0)
        match = r.get('match', 0)
        src   = r.get('g1_source', r.get('type', '?'))[:3].upper()
        # Color coding via ASCII
        verdict = "✓" if match >= 55 else ("△" if match >= 45 else "✗")
        print(f"  {verdict} {opp:<28} {fp:>5.1f}%  G1={g1:>5.1f}%  G2={g2:>5.1f}%  M={match:>5.1f}%  [{src}]")

    if errors and verbose:
        print(f"\n  Errors:")
        for r in errors:
            print(f"    {r.get('opp','?')}: {r.get('error','?')[:50]}")

    # Tier breakdown
    strong  = [r for r in ok if r.get('match',0) >= 60]
    even    = [r for r in ok if 45 <= r.get('match',0) < 60]
    dogs    = [r for r in ok if r.get('match',0) < 45]
    fw_str  = f"{fw:.1f}%"
    print(f"\n  Favored (≥60%): {len(strong)}  |  Even (45-60%): {len(even)}  |  Dog (<45%): {len(dogs)}")
    print(f"  Field-weighted: {fw_str}  {'↑ POSITIVE EV' if fw >= 52 else ('→ BREAKEVEN' if fw >= 48 else '↓ NEGATIVE EV')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all',   action='store_true')
    ap.add_argument('--deck',  default=None)
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    if args.all:
        files = sorted(glob.glob('data/parallel_results_*.json'), reverse=True)
        for f in files[:12]:
            with open(f) as fh: d = json.load(fh)
            if args.deck and args.deck.lower() not in d.get('our_deck','').lower():
                continue
            print_run(d, verbose=args.verbose)
    else:
        latest = latest_result_per_deck()
        for key, d in sorted(latest.items()):
            if args.deck and args.deck.lower() not in d.get('our_deck','').lower():
                continue
            print_run(d, verbose=args.verbose)


if __name__ == '__main__':
    main()
