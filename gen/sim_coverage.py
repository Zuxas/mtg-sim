"""
gen/sim_coverage.py -- Shared simulatability classifier.

Factored out of scripts/full_audit.py (classify_miss / is_vanilla) so the audit
and the deck-generation pool builder share ONE implementation and cannot drift.

A card is "simulatable" if the engine can faithfully advance the game with it:
  REGISTERED   -- has a hand-written ETB_EFFECTS / SPELL_EFFECTS handler
  FAMILY_ONLY  -- handled via the CARD_TO_FAMILY effect-family registry
  VANILLA      -- pure stats + static keywords only, nothing to implement
The unfaithful buckets are:
  HAS_EFFECTS  -- real triggered/activated text with no handler (engine ignores it)
  UNKNOWN_CARD -- not in the oracle DB at all

Usage:
    from gen.sim_coverage import classify_card, SIMULATABLE_BUCKETS
    bucket = classify_card("Lightning Bolt", db)        # "REGISTERED"
    ok = bucket in SIMULATABLE_BUCKETS                  # True
"""

import re
from typing import Optional

SIMULATABLE_BUCKETS = frozenset({"REGISTERED", "FAMILY_ONLY", "VANILLA"})
ALL_BUCKETS = ("REGISTERED", "FAMILY_ONLY", "VANILLA", "HAS_EFFECTS", "UNKNOWN_CARD")

# --- vanilla detection (verbatim from scripts/full_audit.py) ----------------
TRIGGER_RE = re.compile(
    r"\b(when|whenever|at the beginning|sacrifice this|"
    r"choose one|may search|reveal|create a|enters\b|dies\b|attacks\b|"
    r"deals damage|equipped creature|enchanted creature)\b",
    re.IGNORECASE,
)
ACTIVATED_RE = re.compile(r"\{[^}]+\}\s*[:,]")
STATIC_KW = {
    "flying", "trample", "vigilance", "lifelink", "first strike",
    "double strike", "deathtouch", "haste", "hexproof", "reach",
    "menace", "defender", "indestructible", "flash", "shadow",
    "skulk", "horsemanship", "banding", "phasing", "fear", "intimidate",
}


def is_vanilla(text: str) -> bool:
    """True if oracle text contains only static keywords (nothing to simulate)."""
    if not text.strip():
        return True
    tokens = re.split(r"[,\n;]| and ", text.lower())
    for tok in tokens:
        t = tok.strip().rstrip(".")
        if not t:
            continue
        if t in STATIC_KW:
            continue
        if t.startswith("protection from "):
            continue
        if re.match(r"ward\s+\{?\d+\}?$", t):
            continue
        return False
    return True


# --- lazy default registries ------------------------------------------------
_REGISTRIES = None


def _default_registries():
    """Load (ETB_EFFECTS, SPELL_EFFECTS, CARD_TO_FAMILY) once, lazily."""
    global _REGISTRIES
    if _REGISTRIES is None:
        from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
        from engine.effect_family_registry import CARD_TO_FAMILY
        _REGISTRIES = (ETB_EFFECTS, SPELL_EFFECTS, CARD_TO_FAMILY)
    return _REGISTRIES


def classify_card(
    name: str,
    db,
    etb=None,
    spell=None,
    family=None,
    card: Optional[dict] = None,
) -> str:
    """
    Return the coverage bucket for a card name (one of ALL_BUCKETS).

    Mirrors scripts/full_audit.py run_l1_for_format precedence:
      REGISTERED (ETB/SPELL) > FAMILY_ONLY > VANILLA / HAS_EFFECTS / UNKNOWN_CARD.

    `card` is an optional pre-fetched Scryfall dict (avoids a redundant db.get).
    """
    if etb is None or spell is None or family is None:
        d_etb, d_spell, d_family = _default_registries()
        etb = etb if etb is not None else d_etb
        spell = spell if spell is not None else d_spell
        family = family if family is not None else d_family

    if name in etb or name in spell:
        return "REGISTERED"
    if name in family:
        return "FAMILY_ONLY"

    if card is None:
        card = db.get(name)
    if not card:
        return "UNKNOWN_CARD"

    oracle = (card.get("oracle_text") or "").strip()
    if not oracle:
        # DFC / adventure: fall back to combined face text
        faces = card.get("card_faces") or []
        oracle = "\n".join(f.get("oracle_text", "") or "" for f in faces).strip()
    if is_vanilla(oracle):
        return "VANILLA"
    return "HAS_EFFECTS"


def is_simulatable(name: str, db, **kw) -> bool:
    """Convenience: True if the engine can faithfully advance the game with this card."""
    return classify_card(name, db, **kw) in SIMULATABLE_BUCKETS
