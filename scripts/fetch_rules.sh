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

# Known-good base and fallback URLs. Update CURRENT_URL when a new release
# makes the prior one 404.
CURRENT_URL="https://media.wizards.com/2025/downloads/MagicCompRules.txt"
FALLBACK_RULES_PAGE="https://magic.wizards.com/en/rules"

echo "Fetching Comprehensive Rules to $OUT ..."
if curl -fsSL -o "$OUT" "$CURRENT_URL"; then
    size=$(wc -c < "$OUT")
    echo "Downloaded $size bytes from $CURRENT_URL"
    exit 0
fi

cat <<EOF >&2

ERROR: could not download from $CURRENT_URL

WotC changes this URL each release. Steps:
  1. Visit $FALLBACK_RULES_PAGE
  2. Find the current "Comprehensive Rules" .txt download link
  3. Re-run: curl -fsSL -o "$OUT" "<that URL>"

Alternatively, edit this script's CURRENT_URL and open a PR.
EOF
exit 1
