"""
arl_generate_apl.py -- standalone APL stub/code writer for the ARL loop.

Given a deck file, produce an Action Priority List (APL) Python module under
mtg-sim/apl/auto_apls/<slug>.py.

PREFERRED path: reuse auto_pipeline.generate_apl() (real entry point), which
encodes the defensive Card/GameState patterns and invalid-API fixups and
writes under apl/auto_apls/.

FALLBACK path (Ollama down / generation throws / returns error): write a
MINIMAL valid APL stub that subclasses BaseAPL with defensive getattr and just
enough keep()/bottom()/main_phase() to pass a goldfish smoke. notes="stub_fallback".

This script does NOT register the APL -- registration is the loop's job after
the smoke gate passes.

CLI:
    python arl_generate_apl.py <deck_file> [--use-claude] [--force]

Importable:
    generate_apl_file(deck_file, use_claude=False, format_name="modern", force=False)
        -> (apl_path, class_name, notes)
"""

import sys
import os
import re
import ast

# --- Mandatory cross-repo sys.path setup ---
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts"))
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

AUTO_APLS_DIR = os.path.join(SIM_ROOT, "apl", "auto_apls")

# Known format suffixes for filename-based detection.
KNOWN_FORMATS = {
    "standard", "modern", "pioneer", "legacy", "vintage", "pauper",
    "commander", "historic", "explorer", "alchemy", "timeless", "pchampions",
}


# ---------------------------------------------------------------------------
# Naming helpers (mirror auto_pipeline conventions without importing heavy code)
# ---------------------------------------------------------------------------

def _safe_slug(deck_name):
    """Mirror auto_pipeline._safe_slug so output paths match the pipeline."""
    return (deck_name.lower()
            .replace(" ", "_").replace("-", "_").replace("'", ""))


def _class_name_for(deck_name):
    """Mirror auto_pipeline._assemble_apl class-name derivation."""
    base = "".join(w.capitalize() for w in
                   deck_name.replace("-", " ").replace("'", "").split())
    return (base or "Auto") + "APL"


def _derive_deck_meta(deck_file):
    """Return (deck_name, format_name_or_None) from a deck file.

    Prefers the canonical archetype name embedded in an
    '// audit:auto-generated:<name>:<date>' header. Otherwise derives a name
    from the filename, stripping a trailing known-format token.
    """
    deck_name = None
    fmt = None

    # Try the auto-generated header marker for the canonical archetype name.
    try:
        with open(deck_file, "r", encoding="utf-8") as fh:
            for _ in range(8):
                line = fh.readline()
                if not line:
                    break
                m = re.search(r"audit:auto-generated:([^:]+):", line)
                if m:
                    deck_name = m.group(1).strip()
                    break
    except OSError:
        pass

    stem = os.path.splitext(os.path.basename(deck_file))[0]
    tokens = stem.split("_")
    if tokens and tokens[-1].lower() in KNOWN_FORMATS:
        fmt = tokens[-1].lower()
        tokens = tokens[:-1]

    if not deck_name:
        deck_name = " ".join(t.capitalize() for t in tokens) if tokens else stem

    return deck_name, fmt


def _extract_class_name(apl_path):
    """Parse an APL file's AST and return the first class ending in 'APL'.

    Falls back to a regex scan, then None.
    """
    try:
        with open(apl_path, "r", encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return None
    try:
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.endswith("APL") \
                    and node.name != "BaseAPL":
                return node.name
    except SyntaxError:
        pass
    m = re.search(r"class\s+(\w+APL)\s*\(", src)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Deck-file card extraction (for fallback KEY_CARDS)
# ---------------------------------------------------------------------------

def _read_deck_card_names(deck_file, limit=4):
    """Pull up to `limit` mainboard card names from a deck file for KEY_CARDS.

    Best-effort: parses '<qty> <name>' lines, skips comments / blank lines /
    the Sideboard section. Returns [] on any failure.
    """
    names = []
    try:
        with open(deck_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("//") or line.startswith("#"):
                    continue
                if line.lower() in ("sideboard", "sb:"):
                    break
                m = re.match(r"^(\d+)x?\s+(.+)$", line)
                if m:
                    names.append(m.group(2).strip())
                if len(names) >= limit:
                    break
    except OSError:
        return []
    return names


# ---------------------------------------------------------------------------
# Fallback stub writer
# ---------------------------------------------------------------------------

def _write_stub(deck_name, deck_file, format_name):
    """Write a minimal valid APL stub mirroring apl/auto_apls structure.

    Subclasses BaseAPL, defensive getattr for card attributes, just enough
    keep()/bottom()/main_phase()/main_phase2() to pass a goldfish smoke.
    Returns (apl_path, class_name).
    """
    os.makedirs(AUTO_APLS_DIR, exist_ok=True)
    init_file = os.path.join(AUTO_APLS_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w", encoding="utf-8") as fh:
            fh.write("# Auto-generated APL package; populated by ARL.\n")

    safe = _safe_slug(deck_name)
    apl_path = os.path.join(AUTO_APLS_DIR, safe + ".py")
    class_name = _class_name_for(deck_name)

    card_names = _read_deck_card_names(deck_file, limit=4)
    if card_names:
        key_cards_literal = "{" + ", ".join(
            '"' + c.replace('"', "'") + '"' for c in card_names) + "}"
    else:
        key_cards_literal = "set()"

    code = '''# Auto-generated APL for {deck_name} (stub_fallback)
# Source deck: {deck_file}
# notes: stub_fallback -- generator unavailable; minimal goldfish-valid stub.

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {key_cards}


class {class_name}(BaseAPL):
    AUTO_GENERATED = True  # stub_fallback -- flagged for rewrite
    name = "{deck_name}"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if getattr(x, "name", "") in KEY_CARDS]
        return len(lands) >= 2 and (bool(threats) or mulligans >= 2)

    def bottom(self, hand, n):
        excess = sorted([x for x in hand if x.is_land()],
                        key=lambda x: getattr(x, "name", ""))
        to_bottom = excess[3:] if len(excess) > 3 else []
        rest = sorted([x for x in hand if not x.is_land() and x not in to_bottom],
                      key=lambda x: -float(getattr(x, "cmc", 0) or 0))
        for s in rest:
            if len(to_bottom) >= n:
                break
            to_bottom.append(s)
        return to_bottom[:n]

    def main_phase(self, gs):
        self._play_land_if_able(gs)
        hand = [x for x in gs.hand() if not x.is_land()]
        for c in sorted(hand, key=lambda x: float(getattr(x, "cmc", 0) or 0)):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

    def main_phase2(self, gs):
        self._cast_all_castable(gs)
'''.format(
        deck_name=deck_name.replace('"', "'"),
        deck_file=os.path.basename(deck_file),
        key_cards=key_cards_literal,
        class_name=class_name,
    )

    with open(apl_path, "w", encoding="utf-8") as fh:
        fh.write(code)

    # Sanity-check the stub itself parses before returning.
    try:
        ast.parse(code)
    except SyntaxError as se:
        raise RuntimeError("stub_fallback produced invalid Python: %s" % se)

    return apl_path, class_name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_apl_file(deck_file, use_claude=False, format_name="modern",
                      force=False):
    """Generate an APL module for the archetype described by `deck_file`.

    Returns (apl_path, class_name, notes).

    notes is one of:
      - the generator's method (e.g. "claude", "decomposed-qwen2.5-coder:14b")
      - "reused_existing"  (file already present and force=False)
      - "stub_fallback"    (generator unavailable; minimal stub written)

    Non-destructive by default: if the target slug already exists and force is
    False, the existing file is reused (matches the ARL loop contract:
    "ensure APL file exists; if not, write one"). Pass force=True to regenerate.
    """
    if not os.path.isfile(deck_file):
        raise FileNotFoundError("deck file not found: %s" % deck_file)

    deck_name, detected_fmt = _derive_deck_meta(deck_file)
    fmt = detected_fmt or format_name

    safe = _safe_slug(deck_name)
    apl_path = os.path.join(AUTO_APLS_DIR, safe + ".py")

    # Non-destructive reuse short-circuit.
    if os.path.exists(apl_path) and not force:
        cls = _extract_class_name(apl_path) or _class_name_for(deck_name)
        return apl_path, cls, "reused_existing"

    # PREFERRED: reuse the real pipeline generator. Import lazily so --help and
    # read-only use don't drag in Ollama/anthropic-dependent code paths.
    result = None
    try:
        import auto_pipeline  # stdlib-only at import time; heavy deps are lazy
        result = auto_pipeline.generate_apl(
            deck_name,
            use_claude=use_claude,
            dry_run=False,
            force=True,          # we've already done our own reuse gating above
            format_name=fmt,
        )
    except Exception as exc:  # generator import/call blew up -> fall back
        sys.stderr.write("[arl_generate_apl] generator raised: %s\n" % exc)
        result = None

    status = (result or {}).get("status") if isinstance(result, dict) else None

    if status in ("generated", "draft") and os.path.exists(apl_path):
        cls = _extract_class_name(apl_path) or _class_name_for(deck_name)
        notes = (result.get("method") or status)
        return apl_path, cls, notes

    # FALLBACK: generation failed, returned error, or wrote nothing.
    apl_path, cls = _write_stub(deck_name, deck_file, fmt)
    return apl_path, cls, "stub_fallback"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Standalone APL stub/code writer for the ARL loop.")
    parser.add_argument("deck_file", help="Path to the deck (.txt) file")
    parser.add_argument("--use-claude", action="store_true",
                        help="Prefer Claude generation (falls back to Gemma/stub)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if an APL already exists")
    parser.add_argument("--format", default="modern",
                        help="Format hint if not inferable from filename")
    args = parser.parse_args(argv)

    try:
        apl_path, class_name, notes = generate_apl_file(
            args.deck_file,
            use_claude=args.use_claude,
            format_name=args.format,
            force=args.force,
        )
    except Exception as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        return 1

    # Stable, parseable two-line output for the loop.
    print("APL_PATH: %s" % apl_path)
    print("APL_CLASS: %s" % class_name)
    print("NOTES: %s" % notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
