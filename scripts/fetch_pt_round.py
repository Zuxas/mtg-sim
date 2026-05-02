"""
fetch_pt_round.py — Fetch a PT round's results from magic.gg and append to data file.

Usage:
    python scripts/fetch_pt_round.py --round 6
    python scripts/fetch_pt_round.py --round 6 7 8
    python scripts/fetch_pt_round.py --standings 8
    python scripts/fetch_pt_round.py --check       # check which rounds are live

Requires: requests
"""
import sys, json, re, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

EVENT_SLUG = "pro-tour-secrets-of-strixhaven"
BASE_URL = f"https://magic.gg/news/{EVENT_SLUG}"
DATA_FILE = ROOT / "data" / "pt_sos_2026.json"


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)


def fetch_page(url):
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 mtg-sim-tracker"})
        if r.status_code == 404:
            return None, 404
        r.raise_for_status()
        return r.text, r.status_code
    except Exception as e:
        return None, str(e)


def parse_results_from_html(html):
    """
    Minimal HTML parser: find result rows in the magic.gg results table.
    Returns list of {p1, p2, winner, score} dicts.
    Handles both regular results and bye entries.
    """
    matches = []

    # Strip HTML tags for text extraction
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # Pattern: "Lastname, Firstname ... Lastname, Firstname ... 2-X-0" or "Bye"
    # The magic.gg page renders as a table; after stripping tags we get runs of text.
    # We look for the score pattern to anchor each result row.
    score_pat = re.compile(r'(\d-\d-\d)')
    bye_pat = re.compile(r'\bBye\b', re.IGNORECASE)

    # Split by score to find boundaries between matches
    parts = score_pat.split(text)

    for i in range(0, len(parts) - 1, 2):
        segment = parts[i].strip()
        score = parts[i + 1] if i + 1 < len(parts) else ""

        # Each segment contains "P1name ... P2name ... WinnerName"
        # This is tricky without proper HTML parsing; return raw data for manual review
        matches.append({"raw": segment[-200:], "score": score})

    return matches


def check_round(rnd):
    url = f"{BASE_URL}-round-{rnd}-results"
    _, status = fetch_page(url)
    return status == 200


def check_standings(rnd):
    url = f"{BASE_URL}-round-{rnd}-standings"
    _, status = fetch_page(url)
    return status == 200


def report_availability():
    """Check which rounds/standings are live."""
    print(f"\nChecking PT SOS round availability...")
    for rnd in range(1, 9):
        r_live = check_round(rnd)
        s_live = check_standings(rnd)
        r_str = "LIVE" if r_live else "---"
        s_str = "LIVE" if s_live else "---"
        print(f"  R{rnd}: results={r_str}  standings={s_str}")
    print()


def fetch_standings(rnd):
    url = f"{BASE_URL}-round-{rnd}-standings"
    html, status = fetch_page(url)
    if not html:
        print(f"  R{rnd} standings: not available (status {status})")
        return None

    # Extract table rows: rank, player, points
    # Pattern: rows in <tr> tags, but we'll use text extraction
    text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Find point values (3*N format) to anchor standings
    standings = []
    point_pat = re.compile(r'^(\d+)$')
    for i, line in enumerate(lines):
        # Look for lines that are just numbers (points) adjacent to player names
        if point_pat.match(line) and int(line) >= 9:
            # Find nearby player name (typically 1-2 lines before)
            for j in range(max(0, i-3), i):
                if ',' in lines[j] and len(lines[j]) > 5:
                    standings.append({"rank": len(standings)+1,
                                      "player": lines[j],
                                      "points": int(line)})
                    break

    print(f"  R{rnd} standings: {len(standings)} entries extracted")
    return standings if standings else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", "-r", type=int, nargs="+", help="Round number(s) to fetch")
    parser.add_argument("--standings", "-s", type=int, help="Fetch standings after round N")
    parser.add_argument("--check", "-c", action="store_true", help="Check which rounds are live")
    args = parser.parse_args()

    if args.check or (not args.round and not args.standings):
        report_availability()
        if not args.round and not args.standings:
            return

    d = load_data()

    if args.round:
        for rnd in args.round:
            rnd_str = str(rnd)
            if rnd_str in d["rounds"]:
                print(f"  R{rnd}: already in data file ({len(d['rounds'][rnd_str])} entries)")
                continue

            url = f"{BASE_URL}-round-{rnd}-results"
            print(f"  Fetching R{rnd} from {url} ...")
            html, status = fetch_page(url)
            if not html:
                print(f"  R{rnd}: not available (status {status})")
                continue

            # HTML parsing is complex without a proper parser.
            # Print status and instruct manual addition.
            print(f"  R{rnd}: page fetched ({len(html)} bytes, status {status})")
            print(f"  NOTE: HTML parsing requires BeautifulSoup for reliable extraction.")
            print(f"  Raw results page is live -- add manually via WebFetch in Claude Code.")

    if args.standings:
        rnd = args.standings
        print(f"\nFetching R{rnd} standings...")
        standings = fetch_standings(rnd)
        if standings:
            key = f"standings_r{rnd}"
            d[key] = standings[:50]  # top 50
            save_data(d)
            print(f"  Saved top {len(d[key])} standings to data file under '{key}'")
            print(f"  Top 10:")
            for s in d[key][:10]:
                print(f"    {s['rank']:>3}. {s['player']:<30} {s['points']} pts")

    save_data(d)
    print("\nData file updated.")


if __name__ == "__main__":
    main()
