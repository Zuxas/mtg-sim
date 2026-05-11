"""
engine/card_db.py — Local card database from Scryfall oracle cards + rulings

Replaces all Scryfall API calls with local lookups from:
  ./data/rules_reference/   (in this repo)

Populate this directory by running:
  ./scripts/fetch_scryfall_bulk.sh

Three data sources:
  - scryfall_oracle_cards.json  — 37k cards, full oracle text, CMC, types
  - scryfall_rulings.json       — 75k judge rulings by oracle_id
  - MagicCompRules.txt          — full comp rules (already in engine/rules_engine.py)

Usage:
    from engine.card_db import CardDB
    db = CardDB()                          # loads once, cached forever
    card = db.get("Guide of Souls")        # dict with all Scryfall fields
    rulings = db.rulings("Guide of Souls") # list of ruling comments
    oracle = db.oracle_text("Adeline, Resplendent Cathar")
    cmc = db.cmc("Thalia, Guardian of Thraben")
    is_human = db.is_type("Champion of the Parish", "Human")
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

# Path to this repo's own rules_reference directory
# (populate via scripts/fetch_scryfall_bulk.sh)
_RULES_DIR = Path(__file__).parent.parent / "data" / "rules_reference"

# Singleton cache
_db_instance = None


class CardDB:
    """
    Local Scryfall card database — zero network calls.
    Loads on first use, cached for the process lifetime.
    """

    def __init__(self, rules_dir: str = None):
        global _db_instance
        if _db_instance is not None and rules_dir is None:
            # Copy from singleton
            self._cards    = _db_instance._cards
            self._by_name  = _db_instance._by_name
            self._rulings  = _db_instance._rulings
            self._loaded   = True
            return

        self._rules_dir = Path(rules_dir) if rules_dir else _RULES_DIR
        self._cards:   list[dict] = []
        self._by_name: dict[str, dict] = {}    # normalized name → card
        self._rulings: dict[str, list[str]] = {}  # oracle_id → [comment]
        self._loaded   = False
        self._load()

        if rules_dir is None:
            _db_instance = self

    def _load(self):
        oracle_path  = self._rules_dir / "scryfall_oracle_cards.json"
        rulings_path = self._rules_dir / "scryfall_rulings.json"

        if not oracle_path.exists():
            print(f"[CardDB] Oracle cards not found at {oracle_path}")
            return

        print(f"[CardDB] Loading {oracle_path.stat().st_size//1048576}MB oracle database...")
        with open(oracle_path, encoding="utf-8") as f:
            self._cards = json.load(f)

        # Index by normalized name
        # Non-game set types to deprioritize (art series, tokens, promos, etc.)
        _SKIP_SET_TYPES = {"memorabilia", "token", "art_series", "minigame"}

        for card in self._cards:
            name = card.get("name", "")
            norm = self._norm(name)
            set_type = card.get("set_type", "")
            has_data = bool(card.get("mana_cost") or card.get("type_line", "") != "Card")

            # Only overwrite if new card has better data or existing has none
            existing = self._by_name.get(norm)
            if existing is None:
                self._by_name[norm] = card
            elif has_data and (not existing.get("mana_cost") and existing.get("type_line", "") == "Card"):
                # New card has real data, old one was an art series/blank — replace
                self._by_name[norm] = card
            elif has_data and set_type not in _SKIP_SET_TYPES:
                # Prefer game cards over memorabilia
                old_set_type = existing.get("set_type", "")
                if old_set_type in _SKIP_SET_TYPES:
                    self._by_name[norm] = card

            # Also index card faces for DFCs
            for face in card.get("card_faces", []):
                face_name = face.get("name", "")
                if face_name:
                    face_norm = self._norm(face_name)
                    merged = {**card, **face}
                    face_has_data = bool(face.get("mana_cost") or face.get("type_line", "") not in ("Card", ""))
                    existing_face = self._by_name.get(face_norm)
                    if existing_face is None:
                        self._by_name[face_norm] = merged
                    elif face_has_data and (not existing_face.get("mana_cost") and existing_face.get("type_line", "") in ("Card", "")):
                        self._by_name[face_norm] = merged

        print(f"[CardDB] {len(self._cards):,} cards indexed")

        # Load rulings
        if rulings_path.exists():
            with open(rulings_path, encoding="utf-8") as f:
                rulings_raw = json.load(f)

            # Build oracle_id → comments map
            for r in rulings_raw:
                oid = r.get("oracle_id", "")
                if oid:
                    self._rulings.setdefault(oid, []).append(r.get("comment", ""))

            print(f"[CardDB] {len(rulings_raw):,} rulings loaded")

        self._loaded = True

    @staticmethod
    def _norm(name: str) -> str:
        """Normalize card name for fuzzy lookup."""
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def get(self, card_name: str) -> Optional[dict]:
        """Get full Scryfall card dict by name. Fuzzy matches."""
        if not self._loaded:
            return None
        key = self._norm(card_name)
        if key in self._by_name:
            return self._by_name[key]
        # Partial match
        for norm_name, card in self._by_name.items():
            if key in norm_name or norm_name in key:
                return card
        return None

    def oracle_text(self, card_name: str) -> str:
        card = self.get(card_name)
        if not card:
            return ""
        text = card.get("oracle_text", "") or ""
        if text:
            return text
        # DFC / MDFC / Room / Adventure / Split cards: top-level oracle_text
        # is empty; combine the per-face oracle text. Use the " // " separator
        # Scryfall uses for compound names so face boundaries stay parseable.
        faces = card.get("card_faces") or []
        if faces:
            parts = [f.get("oracle_text", "") or "" for f in faces]
            parts = [p for p in parts if p]
            if parts:
                return "\n // \n".join(parts)
        return ""

    def cmc(self, card_name: str) -> float:
        card = self.get(card_name)
        if card:
            return float(card.get("cmc", 0))
        return 0.0

    def mana_cost(self, card_name: str) -> str:
        card = self.get(card_name)
        if card:
            return card.get("mana_cost", "") or ""
        return ""

    def type_line(self, card_name: str) -> str:
        card = self.get(card_name)
        if card:
            return card.get("type_line", "") or ""
        return ""

    def is_type(self, card_name: str, type_str: str) -> bool:
        return type_str.lower() in self.type_line(card_name).lower()

    def is_creature(self, card_name: str) -> bool:
        return self.is_type(card_name, "creature")

    def is_land(self, card_name: str) -> bool:
        return self.is_type(card_name, "land")

    def keywords(self, card_name: str) -> list[str]:
        card = self.get(card_name)
        if card:
            return card.get("keywords", [])
        return []

    def has_keyword(self, card_name: str, keyword: str) -> bool:
        return keyword.lower() in [k.lower() for k in self.keywords(card_name)]

    def power(self, card_name: str) -> Optional[str]:
        card = self.get(card_name)
        return card.get("power") if card else None

    def toughness(self, card_name: str) -> Optional[str]:
        card = self.get(card_name)
        return card.get("toughness") if card else None

    def colors(self, card_name: str) -> list[str]:
        card = self.get(card_name)
        return card.get("colors", []) if card else []

    def rulings(self, card_name: str) -> list[str]:
        """Get all official judge rulings for a card."""
        card = self.get(card_name)
        if not card:
            return []
        oid = card.get("oracle_id", "")
        return self._rulings.get(oid, [])

    def is_legal(self, card_name: str, format_name: str) -> bool:
        """Check if a card is legal in a format."""
        card = self.get(card_name)
        if not card:
            return True  # assume legal if unknown
        legalities = card.get("legalities", {})
        return legalities.get(format_name.lower(), "not_legal") == "legal"

    def search_by_oracle_text(self, query: str, limit: int = 20) -> list[dict]:
        """Find cards whose oracle text contains a query string."""
        q = query.lower()
        results = []
        for card in self._cards:
            text = (card.get("oracle_text") or "").lower()
            if q in text:
                results.append(card)
                if len(results) >= limit:
                    break
        return results

    def cards_with_keyword(self, keyword: str) -> list[str]:
        """Get all card names that have a specific keyword ability."""
        kw = keyword.lower()
        return [
            c["name"] for c in self._cards
            if kw in [k.lower() for k in c.get("keywords", [])]
        ]

    def get_creature_subtypes(self, card_name: str) -> list[str]:
        """Extract subtypes from type line (e.g. 'Human', 'Soldier')."""
        tl = self.type_line(card_name)
        if "—" in tl:
            subtypes_str = tl.split("—", 1)[1].strip()
            return [s.strip() for s in subtypes_str.split()]
        return []

    def summary(self) -> str:
        return (f"CardDB: {len(self._cards):,} cards, "
                f"{sum(len(v) for v in self._rulings.values()):,} rulings")


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def get_card(name: str) -> Optional[dict]:
    return CardDB().get(name)

def get_oracle(name: str) -> str:
    return CardDB().oracle_text(name)

def get_rulings(name: str) -> list[str]:
    return CardDB().rulings(name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    db = CardDB()
    print(db.summary())

    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
        card = db.get(name)
        if card:
            print(f"\n{card['name']}")
            print(f"  CMC: {card.get('cmc')}  Cost: {card.get('mana_cost')}")
            print(f"  Type: {card.get('type_line')}")
            print(f"  P/T: {card.get('power')}/{card.get('toughness')}")
            print(f"  Oracle: {card.get('oracle_text','')[:300]}")
            print(f"  Keywords: {card.get('keywords', [])}")
            rulings = db.rulings(name)
            if rulings:
                print(f"\n  Rulings ({len(rulings)}):")
                for r in rulings[:3]:
                    print(f"    - {r[:150]}")
        else:
            print(f"Card '{name}' not found")
            # Try oracle text search
            results = db.search_by_oracle_text(name, limit=5)
            if results:
                print(f"\nCards with '{name}' in oracle text:")
                for c in results:
                    print(f"  {c['name']}")
