#!/usr/bin/env python3
"""
Sleeve-time real-talk readout for variant deck testing.

Compares a variant deck against a canonical baseline by running
goldfish at user-specified n. Optionally runs a 1k Modern field
gauntlet on each. Prints a clean copy-to-clipboard readout.

Usage:
    python scripts/sleeve_check.py \\
        --variant "Boros Energy Variant Jermey" \\
        --canonical "Boros Energy" \\
        --n 1000 \\
        [--gauntlet]            # optional: also run 1k Modern field
        [--seed 42]             # default 42
        [--no-clipboard]        # skip pyperclip copy
        [--format modern]       # default modern
"""
from __future__ import annotations
import argparse, sys, time, json, subprocess
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))


def run_goldfish(deck_name: str, n: int, seed: int, format_name: str = "modern") -> dict:
    from generate_matchup_data import load_deck_and_apl
    from engine.runner import run_simulation

    mb, _, apl = load_deck_and_apl(deck_name, format_name)
    if not mb or not apl:
        raise SystemExit(
            f"sleeve_check: load failed for {deck_name!r} "
            f"(format={format_name}); check APL_REGISTRY"
        )
    r = run_simulation(apl=apl, mainboard=mb, n=n, on_play=True, seed=seed)

    dist = r.kill_turn_distribution()
    return {
        "wr":       r.win_rate() * 100,
        "avg":      r.avg_kill_turn() or 0.0,
        "median":   r.median_kill_turn() or 0.0,
        "t4_share": dist.get(4, 0.0),
        "dist":     dist,
    }


def run_gauntlet(deck_name: str, n: int, seed: int, format_name: str = "modern"):
    """Returns {field_weighted, matchups} dict, or None if launcher fails."""
    print(f"  [launching parallel_launcher.py for {deck_name}]")
    result = subprocess.run(
        [sys.executable, "parallel_launcher.py",
         "--deck", deck_name, "--format", format_name,
         "--n", str(n), "--top-n", "15", "--seed", str(seed)],
        cwd=str(REPO),
        capture_output=True, text=True, timeout=1800,
    )
    if result.returncode != 0:
        print(f"GAUNTLET FAILED for {deck_name}:", file=sys.stderr)
        print(result.stderr[-500:], file=sys.stderr)
        return None

    # Find the latest parallel_results JSON for this deck name
    results_dir = REPO / "data"
    candidates = sorted(
        results_dir.glob("parallel_results_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get("our_deck") == deck_name:
                return {
                    "field_weighted": data.get("field_weighted_match", 0.0),
                    "matchups": {
                        r["opp"]: {"wr": r.get("match", 0.0)}
                        for r in data.get("results", [])
                        if not r.get("error")
                    },
                }
        except Exception:
            continue
    print(f"GAUNTLET: no JSON found for {deck_name}", file=sys.stderr)
    return None


def format_readout(variant: str, canonical: str,
                   gf_v: dict, gf_c: dict,
                   ga_v=None, ga_c=None,
                   n: int = 1000, seed: int = 42) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(f"SLEEVE CHECK -- {variant} vs {canonical}")
    lines.append("=" * 60)
    lines.append(f"Goldfish ({n} games, seed={seed}):")
    lines.append(
        f"  Variant:   WR {gf_v['wr']:.1f}%, "
        f"T{gf_v['avg']:.2f} avg, T{gf_v['median']:.0f} median, "
        f"T4 share {gf_v['t4_share']:.1f}%"
    )
    lines.append(
        f"  Canonical: WR {gf_c['wr']:.1f}%, "
        f"T{gf_c['avg']:.2f} avg, T{gf_c['median']:.0f} median, "
        f"T4 share {gf_c['t4_share']:.1f}%"
    )
    lines.append(
        f"  Delta:     {gf_v['wr']-gf_c['wr']:+.1f}pp WR, "
        f"{gf_v['avg']-gf_c['avg']:+.2f} turn"
    )
    lines.append("")

    if ga_v and ga_c:
        lines.append("Modern field-weighted (1k samples):")
        lines.append(f"  Variant:   {ga_v['field_weighted']:.1f}%")
        lines.append(f"  Canonical: {ga_c['field_weighted']:.1f}%")
        lines.append(
            f"  Delta:     "
            f"{ga_v['field_weighted']-ga_c['field_weighted']:+.1f}pp"
        )
        lines.append("  Closest matchups (variant, sorted by WR ascending):")
        sorted_mu = sorted(
            ga_v["matchups"].items(), key=lambda kv: kv[1]["wr"]
        )
        for mu_name, mu_data in sorted_mu[:5]:
            lines.append(f"    {mu_name:.<30} {mu_data['wr']:5.1f}%")
        lines.append("")

    gf_wr_delta = gf_v["wr"] - gf_c["wr"]
    gf_avg_delta = gf_v["avg"] - gf_c["avg"]

    if abs(gf_wr_delta) < 1.0 and abs(gf_avg_delta) < 0.10:
        verdict = "VARIANTS ARE INDISTINGUISHABLE -- pick by play pattern"
    elif gf_avg_delta < -0.05 and gf_wr_delta >= -1.0:
        verdict = (
            "VARIANT IS FASTER -- sleeve up if expecting fast field, "
            "canonical if expecting grindy/control"
        )
    elif gf_avg_delta > 0.10 or gf_wr_delta < -2.0:
        verdict = (
            "VARIANT IS WEAKER -- sleeve up canonical "
            "unless variant has specific tech you need"
        )
    else:
        verdict = "VARIANT IS COMPETITIVE -- pick by play pattern"

    lines.append(f"VERDICT: {verdict}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant",   required=True)
    ap.add_argument("--canonical", required=True)
    ap.add_argument("--n",         type=int, default=1000)
    ap.add_argument("--gauntlet",  action="store_true")
    ap.add_argument("--seed",      type=int, default=42)
    ap.add_argument("--no-clipboard", action="store_true")
    ap.add_argument("--format",    default="modern")
    args = ap.parse_args()

    print(f"Running goldfish: {args.variant} (n={args.n})...")
    t0 = time.time()
    gf_v = run_goldfish(args.variant, args.n, args.seed, args.format)
    print(f"  done in {time.time()-t0:.1f}s")

    print(f"Running goldfish: {args.canonical} (n={args.n})...")
    t0 = time.time()
    gf_c = run_goldfish(args.canonical, args.n, args.seed, args.format)
    print(f"  done in {time.time()-t0:.1f}s")

    ga_v = ga_c = None
    if args.gauntlet:
        print(f"Running 1k gauntlet: {args.variant}...")
        ga_v = run_gauntlet(args.variant, 1000, args.seed, args.format)
        print(f"Running 1k gauntlet: {args.canonical}...")
        ga_c = run_gauntlet(args.canonical, 1000, args.seed, args.format)

    readout = format_readout(
        args.variant, args.canonical,
        gf_v, gf_c, ga_v, ga_c,
        n=args.n, seed=args.seed,
    )
    print()
    print(readout)

    if not args.no_clipboard:
        try:
            import pyperclip
            pyperclip.copy(readout)
            print("\n[copied to clipboard]")
        except ImportError:
            print("\n[pyperclip not installed; pip install pyperclip for auto-copy]")


if __name__ == "__main__":
    main()
