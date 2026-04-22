#!/usr/bin/env bash
# fetch_rules.sh - download WotC Comprehensive Rules to data/comp_rules.txt
#
# The Comp Rules are a ~1 MB plain-text file that the APL correctness checks
# reference. They are not committed to this repo (see .gitignore) because
# they are third-party content that changes with every set release.
#
# WotC updates the canonical URL each release, so this script tries a small
# set of likely endpoints and falls back to a helpful error with pointers
# to the magic.wizards.com rules page.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/comp_rules.txt"
mkdir -p "$(dirname "$OUT")"

# WotC rotates the URL every release (it's date-stamped, e.g.
# MagicCompRules 20260417.txt). We scrape the canonical rules
# page to find the current .txt link automatically.
RULES_PAGE="https://magic.wizards.com/en/rules"
PROBE="/tmp/comp_rules_probe.html"

echo "Scraping current Comp Rules URL from $RULES_PAGE ..."
if ! curl -fsS -o "$PROBE" "$RULES_PAGE"; then
    echo "ERROR: failed to fetch $RULES_PAGE" >&2
    exit 1
fi
URL=$(grep -oE 'https://[^"]+MagicCompRules[^"]+\.txt' "$PROBE" | head -n1)
if [ -z "$URL" ]; then
    echo "ERROR: could not locate a .txt link on $RULES_PAGE" >&2
    echo "Visit the page manually and curl the link." >&2
    exit 1
fi

echo "Current URL: $URL"
# URL has a space in it — curl needs it percent-encoded
ENCODED_URL=$(printf %s "$URL" | sed 's/ /%20/g')
if curl -fsSL -o "$OUT" "$ENCODED_URL"; then
    size=$(wc -c < "$OUT")
    effective=$(head -3 "$OUT" | tail -n1 | tr -d '\r')
    echo "Downloaded $size bytes"
    echo "Effective date: $effective"
    exit 0
fi

echo "ERROR: download failed from $URL" >&2
exit 1
