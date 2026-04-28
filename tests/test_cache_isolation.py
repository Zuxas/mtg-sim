"""test_cache_isolation.py — verify matchup_jobs paths key on (our_deck, opp).

Regression test for cache-collision-bug-2026-04-27. Prior layout used
opp-only path, which clobbered between concurrent variant + canonical
gauntlets. New layout: data/matchup_jobs/<our_deck_slug>/<opp_slug>.json.

Tests are unit-level (no subprocess invocation) because the bug class
is "two writers to same path" — proving paths differ for different
decks against the same opp is sufficient. Subprocess timing is OS
behavior, not what we're guarding.
"""
import json
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matchup_jobs import matchup_job_path, ensure_parent, _slugify


def test_paths_differ_per_our_deck():
    """Different our_deck against same opp must produce distinct paths."""
    p_canonical = matchup_job_path("Boros Energy", "Izzet Prowess")
    p_variant   = matchup_job_path("Boros Energy Variant Jermey", "Izzet Prowess")
    assert p_canonical != p_variant, (
        f"path collision: {p_canonical} == {p_variant} "
        "(this is the original cache-collision-bug-2026-04-27 failure mode)"
    )


def test_paths_match_when_same_pair():
    """Same (our_deck, opp) must produce identical paths (deterministic key)."""
    p1 = matchup_job_path("Boros Energy", "Izzet Prowess")
    p2 = matchup_job_path("Boros Energy", "Izzet Prowess")
    assert p1 == p2, f"non-deterministic path: {p1} != {p2}"


def test_slugify_handles_spaces_and_apostrophes():
    """Slug derivation matches prior inline logic in launcher + runner."""
    assert _slugify("Boros Energy") == "boros_energy"
    assert _slugify("Boros Energy Variant Jermey") == "boros_energy_variant_jermey"
    assert _slugify("Goryo's Vengeance") == "goryos_vengeance"
    assert _slugify("Izzet Prowess") == "izzet_prowess"


def test_path_layout_is_subdirectory():
    """our_deck slug must be a subdirectory, not flat-prefixed (avoids __ collision risk)."""
    p = matchup_job_path("Boros Energy", "Izzet Prowess")
    assert p.parent.name == "boros_energy"
    assert p.name == "izzet_prowess.json"


def test_isolation_under_both_write_orders():
    """Simulate the race condition: write A, write B, read both — each gets own value."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Order 1: A then B
        path_a = ensure_parent(matchup_job_path("Boros Energy", "Izzet Prowess", base_dir=base))
        path_b = ensure_parent(matchup_job_path("Boros Energy Variant Jermey", "Izzet Prowess", base_dir=base))
        path_a.write_text(json.dumps({"our_deck": "Boros Energy", "match": 48.5}))
        path_b.write_text(json.dumps({"our_deck": "Boros Energy Variant Jermey", "match": 93.8}))

        a = json.loads(path_a.read_text())
        b = json.loads(path_b.read_text())
        assert a["our_deck"] == "Boros Energy" and a["match"] == 48.5, f"A polluted: {a}"
        assert b["our_deck"] == "Boros Energy Variant Jermey" and b["match"] == 93.8, f"B polluted: {b}"

        # Order 2: B then A (reverse) — repeat with reused paths to confirm deterministic isolation
        path_b.write_text(json.dumps({"our_deck": "Boros Energy Variant Jermey", "match": 92.0}))
        path_a.write_text(json.dumps({"our_deck": "Boros Energy", "match": 49.1}))

        a2 = json.loads(path_a.read_text())
        b2 = json.loads(path_b.read_text())
        assert a2["our_deck"] == "Boros Energy" and a2["match"] == 49.1, f"A polluted reverse: {a2}"
        assert b2["our_deck"] == "Boros Energy Variant Jermey" and b2["match"] == 92.0, f"B polluted reverse: {b2}"


if __name__ == "__main__":
    test_paths_differ_per_our_deck()
    test_paths_match_when_same_pair()
    test_slugify_handles_spaces_and_apostrophes()
    test_path_layout_is_subdirectory()
    test_isolation_under_both_write_orders()
    print("ALL TESTS PASS")
