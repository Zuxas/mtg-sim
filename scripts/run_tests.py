"""run_tests.py -- run the stand-alone test scripts in tests/ (issue #10).

Tests in this repo are scripts, not pytest (see CONVENTIONS.md). This runs
each one as `python tests/<name>.py`, reports every script by name, and exits
1 if any failed.

    python scripts/run_tests.py            fast tier: what CI runs on every push/PR
    python scripts/run_tests.py --all      everything, including the tiers below
    python scripts/run_tests.py NAME ...   just these (with or without .py)

Tiers other than fast are skipped by default and listed in the summary, so a
skip is never silent. Under --all they run, and a missing data file or DB is
a failure.
"""
import os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
TIMEOUT = 600   # seconds per script

# name -> why it is not in the fast tier
EXCLUDED = {
    "test_run_match_set_workers": "slow: n=10000 runs and a wall-clock speedup assertion",
    "test_api":                   "needs card data: fetches from Scryfall when the local bulk is missing",
    "test_anchor_amulet":         "needs card data: scripts/fetch_scryfall_bulk.sh",
    "test_modern_apls":           "needs the mtg-meta-analyzer DB",
    "test_all_modern_apls":       "needs the mtg-meta-analyzer DB (db_bridge)",
    "test_pioneer_apls":          "needs the mtg-meta-analyzer DB (db_bridge)",
    "test_standard_apls":         "needs the mtg-meta-analyzer DB (db_bridge)",
}


def run_one(name):
    path = os.path.join(TESTS, name + ".py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if "def test_" in src and "__main__" not in src:
        return False, 0.0, ("pytest-style file with no `if __name__ == \"__main__\"` block: "
                            "as a script it would pass without running anything")
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, path], cwd=ROOT, capture_output=True,
                           text=True, timeout=TIMEOUT)
        ok, out = p.returncode == 0, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired as e:
        ok, out = False, f"timed out after {TIMEOUT}s\n{e.stdout or ''}"
    return ok, time.time() - t0, out


def main(argv):
    everything = sorted(f[:-3] for f in os.listdir(TESTS)
                        if f.startswith("test_") and f.endswith(".py"))
    picked = [a[:-3] if a.endswith(".py") else a for a in argv if not a.startswith("-")]
    unknown = [n for n in picked if n not in everything]
    if unknown:
        print(f"unknown test script(s): {', '.join(unknown)}")
        return 2
    if picked:
        names, skipped = picked, []
    elif "--all" in argv:
        names, skipped = everything, []
    else:
        names = [n for n in everything if n not in EXCLUDED]
        skipped = [n for n in everything if n in EXCLUDED]

    failed = []
    for name in names:
        ok, secs, out = run_one(name)
        print(f"{'PASS' if ok else 'FAIL'}  {secs:6.1f}s  {name}", flush=True)
        if not ok:
            failed.append(name)
            for line in out.strip().splitlines()[-25:]:
                print("      | " + line.encode("ascii", "replace").decode())

    print()
    for name in skipped:
        print(f"SKIP  {name}: {EXCLUDED[name]}")
    print(f"\n{len(names) - len(failed)} passed, {len(failed)} failed, {len(skipped)} skipped")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
