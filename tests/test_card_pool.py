"""
tests/test_card_pool.py -- Phase 0 unit tests for the legal+simulatable pool.

Hermetic: runs against a small fixture oracle DB (tests/fixtures/) so it needs
no network and no 37k-card bulk download. Full-DB validation is covered by the
Phase 6 smoke test against the real pool.

Run: python tests/test_card_pool.py
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from engine.card_db import CardDB
from engine.mana import parse_cost
from gen.card_pool import CardPool
from gen.ban_list import MODERN_BANNED
from gen.sim_coverage import is_vanilla

FIXTURE_DIR = os.path.join(REPO, "tests", "fixtures", "rules_reference")


def main():
    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    db = CardDB(rules_dir=FIXTURE_DIR)
    pool = CardPool.build("modern", db=db)
    print(f"Fixture Modern pool: {len(pool)} cards\n")

    # 1. A Modern-legal card is present with parsed pips + color identity.
    bolt = pool.get("Lightning Bolt")
    check(bolt is not None, "Lightning Bolt present in Modern pool")
    if bolt:
        check(bolt.color_identity == ["R"], f"Lightning Bolt CI is [R] (got {bolt.color_identity})")
        check(bolt.pips == {"generic": 0, "R": 1}, f"Lightning Bolt pips (got {bolt.pips})")
        check(not bolt.is_land, "Lightning Bolt is not a land")

    # 2. A vanilla creature is classified simulatable (engine-independent).
    bears = pool.get("Grizzly Bears")
    check(bears is not None and bears.sim_bucket == "VANILLA", "Grizzly Bears -> VANILLA")
    check(bears is not None and bears.simulatable, "Grizzly Bears is simulatable")

    # 3. Keyword-only creature is still vanilla/simulatable.
    serra = pool.get("Serra Angel")
    check(serra is not None and serra.simulatable, "Serra Angel (keywords only) simulatable")

    # 4. A card with real triggered text and no handler -> HAS_EFFECTS, unsimulatable.
    from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
    from engine.effect_family_registry import CARD_TO_FAMILY
    titan = pool.get("Primeval Titan")
    handled = ("Primeval Titan" in ETB_EFFECTS or "Primeval Titan" in SPELL_EFFECTS
               or "Primeval Titan" in CARD_TO_FAMILY)
    check(titan is not None, "Primeval Titan present")
    if titan and not handled:
        check(titan.sim_bucket == "HAS_EFFECTS", "unhandled Primeval Titan -> HAS_EFFECTS")
        check(not titan.simulatable, "unhandled Primeval Titan not simulatable")
    else:
        print("  note  Primeval Titan handled by engine; skipping HAS_EFFECTS assertion")

    # 5. Ban-list override excludes a Scryfall-legal card.
    check("The One Ring" in MODERN_BANNED, "The One Ring in override ban list")
    check(pool.get("The One Ring") is None, "The One Ring excluded despite Scryfall-legal")

    # 6. Legality filter excludes a not_legal card.
    check(pool.get("Black Lotus") is None, "Black Lotus excluded (not modern-legal)")

    # 7. Unknown/typo strings never leak in.
    check(pool.get("Notacard McFakeface") is None, "unknown string excluded")

    # 8. Lands present and flagged; duals carry multi-color identity.
    isl = pool.get("Island")
    check(isl is not None and isl.is_land, "Island present and flagged as land")
    steam = pool.get("Steam Vents")
    check(steam is not None and steam.is_land and set(steam.color_identity) == {"U", "R"},
          "Steam Vents is a U/R dual land")

    # 9. parse_cost wiring + is_vanilla sanity.
    check(parse_cost("{1}{R}{R}") == {"generic": 1, "R": 2}, "parse_cost {1}{R}{R}")
    check(is_vanilla("Flying, trample"), "is_vanilla on pure keywords")
    check(not is_vanilla("When this enters, draw a card."), "is_vanilla rejects triggered text")

    # 10. simulatable_names is a non-empty subset of all names.
    sim = pool.simulatable_names()
    check(sim and sim.issubset(pool.names()), "simulatable_names is a non-empty subset")

    # 11. save/load round-trip.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "modern_pool.json")
        pool.save(path)
        reloaded = CardPool.load("modern", path)
        check(len(reloaded) == len(pool), "save/load round-trips card count")
        rb = reloaded.get("Grizzly Bears")
        check(rb is not None and rb.simulatable, "save/load preserves a card")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("All card-pool checks passed.")


if __name__ == "__main__":
    main()
