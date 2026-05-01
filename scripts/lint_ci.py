#!/usr/bin/env python3
"""
lint-mtg-sim.py
================

Static-analysis lint for the mtg-sim project. Catches the class of bugs
that bit us 2026-04-26/27:

  - canonical-deck-mismatch: APL_REGISTRY entry points at a stub key that
    doesn't exist OR a .txt path that doesn't resolve
  - orphan-stub-deck: stub_decks._DB_DECKS entries that no APL_REGISTRY
    references (likely dead code, also possibly a registry pointing at
    the wrong key)
  - deck-file-bad: registered .txt deck file doesn't exist or doesn't have
    a parseable mainboard + sideboard
  - handler-deck-mismatch: APL has SPECIAL_MECHANICS handler for a card
    that isn't in its registered deck (orphan handler) OR deck has cards
    with no handler that are likely to need one

USAGE:
    python lint-mtg-sim.py                   # all checks, human-readable
    python lint-mtg-sim.py --json            # JSON output
    python lint-mtg-sim.py --check registry  # single check
    python lint-mtg-sim.py --strict          # warnings count as errors

EXIT CODES:
    0 = clean
    1 = warnings only
    2 = errors found

DESIGN NOTES:
    Pure AST parsing -- never imports from mtg-sim. Safe to run while
    Claude Code is actively editing the project (no module-state pollution,
    no .pyc collisions, no race conditions).

    Designed to be called from drift-detect.ps1 as well as standalone.

Last updated: 2026-04-27
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(r"E:\vscode ai project")
MTG_SIM_ROOT = PROJECT_ROOT / "mtg-sim"
APL_INIT     = MTG_SIM_ROOT / "apl" / "__init__.py"
STUB_DECKS   = MTG_SIM_ROOT / "data" / "stub_decks.py"
DECKS_DIR    = MTG_SIM_ROOT / "decks"
APL_DIR      = MTG_SIM_ROOT / "apl"


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str   # "INFO" | "WARN" | "ERROR"
    check:    str
    detail:   str
    fix:      str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARN")

    def add(self, severity: str, check: str, detail: str, fix: str = "") -> None:
        self.findings.append(Finding(severity, check, detail, fix))


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _safe_parse(path: Path) -> ast.Module | None:
    """Parse a .py file via AST; return None on read or parse error."""
    try:
        src = path.read_text(encoding="utf-8")
        return ast.parse(src, filename=str(path))
    except (OSError, SyntaxError) as e:
        return None


def _literal(node: ast.AST) -> Any:
    """Best-effort literal extraction from an AST node.

    Returns the literal value for ast.Constant / ast.Tuple / ast.List /
    ast.Dict / ast.Name (returns the name as a string sentinel
    'name:<identifier>' for identifier references).

    This intentionally doesn't use ast.literal_eval because we want to
    capture identifier references (e.g., a tuple like (module, cls, key)
    where module and cls are Names, not Constants).
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return f"name:{node.id}"
    if isinstance(node, ast.Tuple):
        return tuple(_literal(e) for e in node.elts)
    if isinstance(node, ast.List):
        return [_literal(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_literal(k): _literal(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Attribute):
        # Module attribute access like SomeModule.SomeAPL -- represent as
        # 'attr:Module.Name' so we can still spot-check structure
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return "attr:" + ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        # Some configs build entries via function calls. Mark as such.
        return f"call:{ast.dump(node, annotate_fields=False)[:80]}"
    return f"unknown:{type(node).__name__}"


def _find_assignment(tree: ast.Module, name: str) -> ast.AST | None:
    """Find a top-level assignment to `name` and return the value AST node."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return node.value
    return None


# ---------------------------------------------------------------------------
# Extract APL_REGISTRY
# ---------------------------------------------------------------------------

def _extract_apl_registry(path: Path) -> dict | None:
    """Parse apl/__init__.py and extract APL_REGISTRY as a dict.

    Returns None if file missing or registry not parseable.
    Each value is the literal-extracted form (typically a tuple of
    'attr:...' references and a string deck path / stub key).
    """
    tree = _safe_parse(path)
    if tree is None:
        return None
    val = _find_assignment(tree, "APL_REGISTRY")
    if val is None:
        return None
    if not isinstance(val, ast.Dict):
        return None
    out: dict = {}
    for k_node, v_node in zip(val.keys, val.values):
        k = _literal(k_node)
        v = _literal(v_node)
        out[k] = v
    return out


def _extract_db_decks(path: Path) -> set[str] | None:
    """Parse data/stub_decks.py and extract _DB_DECKS keys."""
    tree = _safe_parse(path)
    if tree is None:
        return None
    # Try _DB_DECKS first (private), then DB_DECKS
    val = _find_assignment(tree, "_DB_DECKS") or _find_assignment(tree, "DB_DECKS")
    if val is None or not isinstance(val, ast.Dict):
        return None
    keys: set[str] = set()
    for k_node in val.keys:
        if isinstance(k_node, ast.Constant) and isinstance(k_node.value, str):
            keys.add(k_node.value)
    return keys


# ---------------------------------------------------------------------------
# Deck file parsing
# ---------------------------------------------------------------------------

def _deck_is_audit_triaged(path: Path) -> tuple[bool, str]:
    """Check if a deck file has an audit-marker comment that means the
    count check should be skipped.

    Recognized markers (case-insensitive, in first 10 lines):
      // audit:intentional      -- count is intentional (e.g. Yorion 80+)
      // audit:custom_variant   -- non-canonical count was triaged + accepted

    Returns (is_triaged, marker_text). marker_text is empty if not triaged.

    Markers introduced 2026-04-25 via data/deck_triage_2026-04-25.md.
    Lint added 2026-04-27 (this commit) so drift-detect stops false-
    positive WARN-ing on triaged custom variants.
    """
    if not path.exists():
        return (False, "")
    try:
        with open(path, encoding="utf-8") as f:
            head = [next(f, "") for _ in range(10)]
    except OSError:
        return (False, "")
    blob = "".join(head).lower()
    if "audit:intentional" in blob:
        return (True, "audit:intentional")
    if "audit:custom_variant" in blob:
        return (True, "audit:custom_variant")
    if "audit:auto-generated" in blob:
        return (True, "audit:auto-generated")
    if "audit:stub" in blob:
        return (True, "audit:stub")
    return (False, "")


def _stub_decks_has_fuzzy_fallback_marker(path: Path) -> bool:
    """Check if data/stub_decks.py declares itself a fuzzy-fallback data store.

    Recognized marker (case-insensitive, in first 30 lines):
      # audit:fuzzy-fallback   -- _DB_DECKS entries are intentional safety-
                                  net data for runtime fuzzy lookups, not
                                  orphans to be deleted.

    When present, the orphan-stub check downgrades from emitting an INFO
    per unreferenced stub to silence. Documents the load-bearing contract
    that lint's "no APL_REGISTRY string ref" model misses (the runtime
    tier-2 fallback at generate_matchup_data.py:86-95 calls
    get_stub_deck_list(deck_name) for arbitrary names).

    Marker introduced 2026-04-28 via execution-chain S1.5 finding.
    Generalizes the audit:custom_variant pattern (see _deck_is_audit_triaged).
    """
    if not path.exists():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            head = [next(f, "") for _ in range(30)]
    except OSError:
        return False
    return "audit:fuzzy-fallback" in "".join(head).lower()


def _parse_deck_file(path: Path) -> tuple[list[str], list[str]] | None:
    """Parse a .txt deck file into (mainboard_cards, sideboard_cards).

    Each card is the card name (lines like '4 Ragavan, Nimble Pilferer' yield
    'Ragavan, Nimble Pilferer' once per copy or the name once -- here we
    return one entry per copy so 4 Ragavan -> 4 entries).

    Sideboard delimiter: blank line OR line starting with 'Sideboard' /
    'SB:' / '//' / '#'.

    Returns None if file missing or unparseable.
    """
    if not path.exists():
        return None

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    mainboard: list[str] = []
    sideboard: list[str] = []
    target = mainboard
    sb_seen = False

    for raw in lines:
        line = raw.strip()
        if not line:
            # Blank line = transition to SB on first occurrence
            if not sb_seen and mainboard:
                target = sideboard
                sb_seen = True
            continue

        lower = line.lower()
        if lower.startswith(("sideboard", "sb:", "// sideboard", "#sb")):
            target = sideboard
            sb_seen = True
            continue
        if line.startswith(("//", "#")):
            continue

        # Parse "<count> <name>" or just "<name>"
        parts = line.split(None, 1)
        if not parts:
            continue
        count = 1
        name = line
        try:
            count = int(parts[0])
            if len(parts) > 1:
                name = parts[1].strip()
        except ValueError:
            name = line

        # Strip set/collector tags like "Ragavan (MH2) 138"
        if "(" in name:
            name = name.split("(", 1)[0].strip()

        for _ in range(count):
            target.append(name)

    return mainboard, sideboard


# ---------------------------------------------------------------------------
# CHECK: Registry consistency
# ---------------------------------------------------------------------------

def check_registry(report: Report) -> None:
    """Each APL_REGISTRY entry's third tuple element is either:
       - a .txt path that exists and parses to a valid deck (60+15)
       - a stub key that exists in stub_decks._DB_DECKS"""

    if not APL_INIT.exists():
        report.add("ERROR", "registry", f"{APL_INIT} not found")
        return
    if not STUB_DECKS.exists():
        report.add("ERROR", "registry", f"{STUB_DECKS} not found")
        return

    registry = _extract_apl_registry(APL_INIT)
    if registry is None:
        report.add("ERROR", "registry",
                   "Could not parse APL_REGISTRY from apl/__init__.py",
                   "Check syntax / verify the global is named APL_REGISTRY")
        return

    db_keys = _extract_db_decks(STUB_DECKS)
    if db_keys is None:
        report.add("WARN", "registry",
                   "Could not parse _DB_DECKS from data/stub_decks.py",
                   "Stub-key checks will be skipped")
        db_keys = set()

    referenced_stubs: set[str] = set()
    referenced_decks: set[str] = set()

    for key, value in registry.items():
        if not isinstance(value, tuple) or len(value) < 3:
            report.add("WARN", "registry",
                       f"Entry '{key}' has unexpected shape: {value}",
                       "Each entry should be (module, cls, deck_path_or_stub)")
            continue

        deck_or_stub = value[2]

        # Skip Nones / non-strings (some registry entries may legitimately be None)
        if deck_or_stub is None:
            continue
        if not isinstance(deck_or_stub, str):
            report.add("WARN", "registry",
                       f"Entry '{key}' deck slot is non-string: {deck_or_stub!r}")
            continue

        # Path-like? .txt or contains slashes
        if deck_or_stub.endswith(".txt") or "/" in deck_or_stub or "\\" in deck_or_stub:
            referenced_decks.add(deck_or_stub)
            # Resolve relative paths from mtg-sim root
            deck_path = MTG_SIM_ROOT / deck_or_stub
            if not deck_path.exists():
                report.add("ERROR", "registry",
                           f"Entry '{key}' references deck '{deck_or_stub}' which doesn't exist",
                           f"Either fix the path or move {key} to a stub_decks entry")
                continue
            parsed = _parse_deck_file(deck_path)
            if parsed is None:
                report.add("ERROR", "registry",
                           f"Entry '{key}' deck file '{deck_or_stub}' couldn't be parsed",
                           f"Check encoding / format of {deck_path}")
                continue
            mb, sb = parsed

            # Check if this deck has been audit-triaged as a known custom
            # variant or intentional non-60 count. If so, downgrade count
            # WARNs to INFOs so drift-detect doesn't false-positive on
            # decks the 2026-04-25 triage explicitly accepted.
            triaged, marker = _deck_is_audit_triaged(deck_path)

            if len(mb) != 60:
                if triaged:
                    report.add("INFO", "registry",
                               f"Entry '{key}' deck has {len(mb)} mainboard cards (expected 60), "
                               f"but file is marked '{marker}' -- count accepted",
                               f"See data/deck_triage_2026-04-25.md for triage rationale")
                else:
                    report.add("WARN", "registry",
                               f"Entry '{key}' deck has {len(mb)} mainboard cards (expected 60)",
                               f"Audit {deck_or_stub} for missing/extra cards")
            if len(sb) != 15 and len(sb) != 0:
                if triaged:
                    report.add("INFO", "registry",
                               f"Entry '{key}' deck has {len(sb)} sideboard cards (expected 0 or 15), "
                               f"but file is marked '{marker}' -- count accepted")
                else:
                    report.add("WARN", "registry",
                               f"Entry '{key}' deck has {len(sb)} sideboard cards (expected 0 or 15)",
                               f"Audit {deck_or_stub} sideboard")
        else:
            # Treat as stub key
            referenced_stubs.add(deck_or_stub)
            if db_keys and deck_or_stub not in db_keys:
                report.add("ERROR", "registry",
                           f"Entry '{key}' references stub '{deck_or_stub}' not in _DB_DECKS",
                           f"Add stub to data/stub_decks.py OR fix the registry key")

    # CHECK: orphan stubs (in _DB_DECKS but no registry entry references them)
    # Suppressed when stub_decks.py declares # audit:fuzzy-fallback -- the
    # entries are intentional safety-net data for runtime fuzzy lookups, not
    # orphans. See generate_matchup_data.py:86-95 for the tier-2 fallback
    # that resolves arbitrary deck names via get_stub_deck_list(deck_name).
    if db_keys and not _stub_decks_has_fuzzy_fallback_marker(STUB_DECKS):
        orphans = db_keys - referenced_stubs
        for orphan in sorted(orphans):
            report.add("INFO", "registry-orphan-stub",
                       f"Stub '{orphan}' in _DB_DECKS has no APL_REGISTRY reference",
                       "Either delete the stub or wire it to an APL")


# ---------------------------------------------------------------------------
# CHECK: Deck files in decks/ are referenced
# ---------------------------------------------------------------------------

def check_orphan_decks(report: Report) -> None:
    """Decks in decks/*.txt that no APL_REGISTRY entry references.

    Stage S4 / 2026-04-28: also reads data/auto_apl_registry.json so
    auto-registered deck files don't show as orphans. Files marked with
    audit:auto-generated are also suppressed via _deck_is_audit_triaged
    as a backstop in case the JSON registry is missing.
    """

    if not DECKS_DIR.exists() or not APL_INIT.exists():
        return

    registry = _extract_apl_registry(APL_INIT)
    if registry is None:
        return

    referenced: set[str] = set()
    for key, value in registry.items():
        if isinstance(value, tuple) and len(value) >= 3:
            d = value[2]
            if isinstance(d, str) and d.endswith(".txt"):
                # Normalize the path
                p = (MTG_SIM_ROOT / d).resolve()
                referenced.add(str(p).lower())

    # Stage S4: include auto-registered deck files
    auto_reg_path = MTG_SIM_ROOT / "data" / "auto_apl_registry.json"
    if auto_reg_path.exists():
        try:
            import json
            auto_reg = json.loads(auto_reg_path.read_text(encoding="utf-8"))
            for key, entry in auto_reg.items():
                d = entry.get("deck_file", "")
                if d.endswith(".txt"):
                    p = (MTG_SIM_ROOT / d).resolve()
                    referenced.add(str(p).lower())
        except Exception:
            pass  # corrupt registry -> fall through to marker-based suppression

    for deck_file in DECKS_DIR.rglob("*.txt"):
        p = str(deck_file.resolve()).lower()
        if p in referenced:
            continue
        # Stage S4 backstop: suppress files with audit:auto-generated marker
        triaged, _ = _deck_is_audit_triaged(deck_file)
        if triaged:
            continue
        rel = deck_file.relative_to(MTG_SIM_ROOT)
        report.add("INFO", "orphan-deck",
                   f"Deck file '{rel}' has no APL_REGISTRY reference",
                   "Either wire to an APL or move to decks/archive/")


# ---------------------------------------------------------------------------
# CHECK: Handler/deck consistency
#
# For each APL file with a SPECIAL_MECHANICS / MATCH_REMOVAL dict, check that
# every handler key is a card name that appears in the registered deck.
# Orphan handlers waste lookup cycles and indicate stale APL code.
# ---------------------------------------------------------------------------

def check_handlers(report: Report) -> None:
    """Audit per-APL SPECIAL_MECHANICS handlers against registered deck."""

    if not APL_INIT.exists():
        return

    registry = _extract_apl_registry(APL_INIT)
    if registry is None:
        return

    for key, value in registry.items():
        if not isinstance(value, tuple) or len(value) < 3:
            continue

        # Module reference: 'attr:apl.boros_energy' or 'name:boros_energy'
        module_ref = value[0]
        deck_or_stub = value[2]

        # Find the module file
        mod_name = None
        if isinstance(module_ref, str):
            if module_ref.startswith("attr:"):
                # 'attr:apl.boros_energy' -> 'boros_energy'
                tail = module_ref[5:]
                mod_name = tail.split(".")[-1]
            elif module_ref.startswith("name:"):
                mod_name = module_ref[5:]

        if not mod_name:
            continue

        mod_path = APL_DIR / f"{mod_name}.py"
        if not mod_path.exists():
            report.add("WARN", "handler-deck",
                       f"Entry '{key}' references module '{mod_name}' but {mod_path} doesn't exist")
            continue

        # Get the deck card list for this entry
        if not isinstance(deck_or_stub, str) or not deck_or_stub.endswith(".txt"):
            # Stub -- can't easily get card names from stub via AST
            continue
        deck_path = MTG_SIM_ROOT / deck_or_stub
        parsed = _parse_deck_file(deck_path)
        if parsed is None:
            continue
        mb, sb = parsed
        deck_cards = set(c.lower() for c in mb + sb)

        # Parse the APL module for SPECIAL_MECHANICS / MATCH_REMOVAL
        tree = _safe_parse(mod_path)
        if tree is None:
            continue

        for handler_name in ("SPECIAL_MECHANICS", "MATCH_REMOVAL", "HANDLERS"):
            handler_dict_node = _find_assignment(tree, handler_name)
            if handler_dict_node is None:
                # Try looking in class bodies (handlers may be class attributes)
                for cls_node in (n for n in tree.body if isinstance(n, ast.ClassDef)):
                    for stmt in cls_node.body:
                        if isinstance(stmt, ast.Assign):
                            for tgt in stmt.targets:
                                if isinstance(tgt, ast.Name) and tgt.id == handler_name:
                                    handler_dict_node = stmt.value
                                    break
                        if handler_dict_node is not None:
                            break
                    if handler_dict_node is not None:
                        break

            if not isinstance(handler_dict_node, ast.Dict):
                continue

            for k_node in handler_dict_node.keys:
                if isinstance(k_node, ast.Constant) and isinstance(k_node.value, str):
                    card_name = k_node.value
                    # Strip any oracle-key suffixes like "Card | flag"
                    base = card_name.split("|")[0].strip().lower()
                    if base and base not in deck_cards:
                        # Don't flag handlers for tokens / temp cards
                        if "token" in base or base.startswith("_"):
                            continue
                        report.add("INFO", "handler-deck",
                                   f"{mod_name}.{handler_name}: handler for '{card_name}' but card not in '{deck_or_stub}'",
                                   "Either remove the orphan handler or audit the deck")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS = {
    "registry":      check_registry,
    "orphan-decks":  check_orphan_decks,
    "handlers":      check_handlers,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Static-analysis lint for mtg-sim project.")
    parser.add_argument("--check", choices=list(CHECKS.keys()) + ["all"],
                        default="all",
                        help="Which check to run (default: all)")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON report to stdout")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors")
    args = parser.parse_args()

    if not MTG_SIM_ROOT.exists():
        print(f"ERROR: mtg-sim root not found: {MTG_SIM_ROOT}", file=sys.stderr)
        return 2

    report = Report()

    if args.check == "all":
        for fn in CHECKS.values():
            fn(report)
    else:
        CHECKS[args.check](report)

    if args.json:
        out = {
            "errors":   report.errors,
            "warnings": report.warnings,
            "issues":   [f.to_dict() for f in report.findings],
        }
        print(json.dumps(out, indent=2))
    else:
        print("=== mtg-sim lint ===")
        print(f"Errors:   {report.errors}")
        print(f"Warnings: {report.warnings}")
        print(f"Total:    {len(report.findings)}")
        print()
        for f in report.findings:
            print(f"[{f.severity}] {f.check}: {f.detail}")
            if f.fix:
                print(f"          fix: {f.fix}")

    if report.errors > 0:
        return 2
    if args.strict and report.warnings > 0:
        return 2
    if report.warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
