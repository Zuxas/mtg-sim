#!/usr/bin/env bash
# fetch_scryfall_bulk.sh - download Scryfall bulk data for local use.
#
# Uses the official /bulk-data manifest (documented and intended for this
# use case). Downloads oracle_cards + rulings to data/rules_reference/.
# Skips download if the local copy is fresher than STALE_DAYS (default 7).
#
# Card data courtesy of Scryfall (https://scryfall.com). Magic: The Gathering
# is (c) Wizards of the Coast.
set -eu

STALE_DAYS="${STALE_DAYS:-7}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/data/rules_reference"
mkdir -p "$DEST"

fetch_one() {
    local type="$1" out="$2"
    local now mtime age_days
    now=$(date +%s)
    if [ -f "$DEST/$out" ]; then
        mtime=$(stat -c %Y "$DEST/$out" 2>/dev/null || stat -f %m "$DEST/$out")
        age_days=$(( (now - mtime) / 86400 ))
        if [ "$age_days" -lt "$STALE_DAYS" ]; then
            echo "$out is $age_days days old (< $STALE_DAYS) - skipping"
            return 0
        fi
        echo "$out is $age_days days old (>= $STALE_DAYS) - refreshing"
    fi

    local uri
    uri=$(curl -fsSL -A "mtg-sim/1.0" \
        "https://api.scryfall.com/bulk-data" \
        | python3 -c "
import json, sys
data = json.load(sys.stdin)
for b in data['data']:
    if b['type'] == '$type':
        print(b['download_uri'])
        break
")
    if [ -z "$uri" ]; then
        echo "ERROR: no download_uri found for type=$type" >&2
        return 1
    fi

    echo "Fetching $type from $uri"
    curl -fsSL --compressed -A "mtg-sim/1.0" -o "$DEST/$out" "$uri"
    local size
    size=$(stat -c %s "$DEST/$out" 2>/dev/null || stat -f %z "$DEST/$out")
    echo "  wrote $size bytes to $DEST/$out"
}

echo "Fetching Scryfall bulk data to $DEST ..."
fetch_one oracle_cards scryfall_oracle_cards.json
fetch_one rulings      scryfall_rulings.json
echo "Done."
