"""Format-aware registry lookup (spec harness/specs/2026-09-30-format-aware-registry.md).

The Standard field key "Izzet Prowess" used to resolve to the MODERN entry
(`izzetprowess`): Modern decklist (Lightning Bolt) + Modern MatchAPL. With a
format, a registered '<key><format>' entry now wins; without one, nothing changes.
"""
import contextlib
import io
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apl
from data.deck import load_deck_from_file
from generate_matchup_data import load_deck_and_apl


def _load(name, fmt):
    with contextlib.redirect_stdout(io.StringIO()):
        return load_deck_and_apl(name, fmt)


def _names(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return Counter(c.name for c in load_deck_from_file(path)[0])


def test_standard_izzet_prowess_loads_the_standard_deck_and_pilot():
    main, _, _ = _load("Izzet Prowess", "standard")
    assert Counter(c.name for c in main) == _names("decks/izzet_prowess_standard.txt")
    assert not any(c.name == "Lightning Bolt" for c in main)
    assert type(apl.get_match_apl("Izzet Prowess", "standard")).__name__ == "IzzetProwessStandardMatchAPL"


def test_modern_izzet_prowess_unchanged():
    main, _, _ = _load("Izzet Prowess", "modern")
    assert Counter(c.name for c in main) == _names("decks/izzet_prowess_modern.txt")
    assert type(apl.get_match_apl("Izzet Prowess", "modern")).__name__ == "IzzetProwessMatchAPL"


def test_no_format_is_the_old_behaviour():
    assert apl.get_apl_entry("Izzet Prowess") == apl.APL_REGISTRY["izzetprowess"]
    assert type(apl.get_match_apl("Izzet Prowess")).__name__ == "IzzetProwessMatchAPL"


def test_format_key_is_per_registry():
    # present in both registries
    assert apl._format_key("Izzet Prowess", "standard", apl.APL_REGISTRY) == "izzetprowessstandard"
    assert apl._format_key("Izzet Prowess", "standard", apl.MATCH_APL_REGISTRY) == "izzetprowessstandard"
    # goldfish-only twin: the match lookup must not pick it
    assert apl._format_key("Dimir Tempo", "legacy", apl.APL_REGISTRY) == "dimirtempolegacy"
    assert apl._format_key("Dimir Tempo", "legacy", apl.MATCH_APL_REGISTRY) is None
    # no twin / no format
    assert apl._format_key("Boros Energy", "modern", apl.APL_REGISTRY) is None
    assert apl._format_key("Izzet Prowess", None, apl.APL_REGISTRY) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL FORMAT-AWARE REGISTRY TESTS PASS")
