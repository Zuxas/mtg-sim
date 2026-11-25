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

    # Windows installs (the self-hosted runner) ship `python`, not `python3`.
    local PY=python3
    command -v python3 >/dev/null 2>&1 || PY=python
    # Scryfall's bulk index dropped `download_uri` (one JSON array) for
    # `jsonl_download_uri` (gzipped, one card per line). The loaders read a
    # JSON array, so convert on the way in. The old field is used if present.
    local uri
    uri=$(curl -fsSL -A "mtg-sim/1.0" \
        "https://api.scryfall.com/bulk-data" \
        | "$PY" -c "
import json, sys
data = json.load(sys.stdin)
for b in data['data']:
    if b['type'] == '$type':
        print(b.get('download_uri') or b['jsonl_download_uri'])
        break
")
    if [ -z "$uri" ]; then
        echo "ERROR: no download uri found for type=$type" >&2
        return 1
    fi

    echo "Fetching $type from $uri"
    curl -fsSL -A "mtg-sim/1.0" -o "$DEST/$out.part" "$uri"
    # Write the array to a temp file and move it into place, so a failed
    # download never leaves a half-written oracle file behind.
    "$PY" - "$DEST/$out.part" "$DEST/$out.tmp" <<'PYEOF'
import gzip, json, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, 'rb') as f:
    gz = f.read(2) == b'\x1f\x8b'
opener = gzip.open if gz else open
with opener(src, 'rt', encoding='utf-8') as f:
    head = f.read(1)
    f.seek(0)
    rows = json.load(f) if head == '[' else [json.loads(line) for line in f if line.strip()]
if not rows:
    sys.exit('ERROR: downloaded bulk file is empty')
with open(dst, 'w', encoding='utf-8') as f:
    json.dump(rows, f)
print(f'  {len(rows)} records')
PYEOF
    mv "$DEST/$out.tmp" "$DEST/$out"
    rm -f "$DEST/$out.part"
    local size
    size=$(stat -c %s "$DEST/$out" 2>/dev/null || stat -f %z "$DEST/$out")
    echo "  wrote $size bytes to $DEST/$out"
}

echo "Fetching Scryfall bulk data to $DEST ..."
fetch_one oracle_cards scryfall_oracle_cards.json
fetch_one rulings      scryfall_rulings.json
echo "Done."
