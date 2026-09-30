"""
fidelity.py -- per-deck card-support report + the strict-mode pre-flight.

Spec harness/specs/2026-09-30-strict-mode.md. For every nonland card the engine's
support tier is:
  verified  handler in engine.card_handlers_verified / engine.card_effects
  auto      handler generated from oracle text (engine.standard_auto_handlers /
            engine.sos_auto_handlers) -- an approximation (Codex review #6)
  family    only an effect-family registration (engine.effect_family_registry)
  vanilla   no rules text beyond evergreen keywords (needs no handler)
  none      has rules text and no handler: in the game it does nothing
Strict mode refuses a deck with a 'none' card, main != 60, sideboard > 15, an
unresolved card name, or no registered MatchAPL. 'auto' and 'family' are reported,
not blocked (the per-deck fidelity manifest is a later step).
"""
from __future__ import annotations

import contextlib
import io
import re
from collections import Counter

VERIFIED_MODULES = {"engine.card_handlers_verified", "engine.card_effects"}
AUTO_MODULES = {"engine.standard_auto_handlers", "engine.sos_auto_handlers"}

# Copy of scripts/full_audit.py::is_vanilla (that script runs its audit at import time).
STATIC_KW = {
    "flying", "trample", "vigilance", "lifelink", "first strike",
    "double strike", "deathtouch", "haste", "hexproof", "reach",
    "menace", "defender", "indestructible", "flash", "shadow",
    "skulk", "horsemanship", "banding", "phasing", "fear", "intimidate",
}


def is_vanilla(text: str) -> bool:
    if not (text or "").strip():
        return True
    for tok in re.split(r"[,\n;]| and ", text.lower()):
        t = tok.strip().rstrip(".")
        if not t or t in STATIC_KW or t.startswith("protection from "):
            continue
        if re.match(r"ward\s+\{?\d+\}?$", t):
            continue
        return False
    return True


def _resolves(db, name: str) -> bool:
    """CardDB.get is exact since 2026-09-30 (spec 2026-09-30-card-identity-gate):
    a name resolves iff it is a card or card-face name up to case/punctuation."""
    return db.get(name) is not None


def card_tier(name: str) -> str:
    from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
    from engine.effect_family_registry import CARD_TO_FAMILY
    from engine.card_db import CardDB
    fns = [d[name] for d in (SPELL_EFFECTS, ETB_EFFECTS) if name in d]
    if fns:
        mods = {getattr(f, "__module__", "") for f in fns}
        return "verified" if mods & VERIFIED_MODULES else "auto"
    if name in CARD_TO_FAMILY:
        return "family"
    data = CardDB().get(name) or {}
    return "vanilla" if is_vanilla(data.get("oracle_text", "")) else "none"


def deck_fidelity(key: str, fmt: str) -> dict:
    """Load the deck exactly as the launcher does and classify it."""
    from generate_matchup_data import load_deck_and_apl
    from engine.card_db import CardDB
    from apl import MATCH_APL_REGISTRY, _format_key, _normalize_key
    from engine.card_db import UnknownCardError
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            main, side, _ = load_deck_and_apl(key, fmt)
    except UnknownCardError as e:     # exact-name loading refuses the deck outright
        return {"deck": key, "format": fmt, "main": 0, "side": 0, "tier_counts": {}, "tiers": {},
                "copies": {}, "blocks": [f"unresolved cards: {e.names}"], "ok": False}
    main, side = main or [], side or []
    db = CardDB()
    names = Counter(c.name for c in main)
    unresolved = sorted({c.name for c in main + side if not _resolves(db, c.name)})
    tiers = {n: card_tier(n) for n in names if not db.is_land(n)}
    has_match_apl = bool(_format_key(key, fmt, MATCH_APL_REGISTRY)) or _normalize_key(key) in MATCH_APL_REGISTRY
    blocks = []
    if len(main) != 60:
        blocks.append(f"main has {len(main)} cards")
    if len(side) > 15:
        blocks.append(f"sideboard has {len(side)} cards")
    if unresolved:
        blocks.append(f"unresolved cards: {unresolved}")
    none = sorted(n for n, t in tiers.items() if t == "none")
    if none:
        blocks.append(f"cards with no handler: {none}")
    if not has_match_apl:
        blocks.append("no registered MatchAPL")
    return {"deck": key, "format": fmt, "main": len(main), "side": len(side),
            "tier_counts": dict(Counter(tiers.values())),
            "tiers": tiers, "copies": dict(names), "blocks": blocks, "ok": not blocks}


def preflight(key: str, fmt: str) -> None:
    """Raise StrictModeError if the deck may not be simulated in strict mode."""
    from engine.strict import StrictModeError
    rep = deck_fidelity(key, fmt)
    if not rep["ok"]:
        raise StrictModeError(f"fidelity pre-flight failed for {key} ({fmt}): " + "; ".join(rep["blocks"]))
