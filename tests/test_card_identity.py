"""Exact card identity (spec harness/specs/2026-09-30-card-identity-gate.md).
No substring / closest-match substitution anywhere in lookup or deck loading."""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.card_db import CardDB, UnknownCardError

DB = CardDB()


def _name(n):
    c = DB.get(n)
    return c.get("name") if c else None


def test_split_card_spellings():
    assert _name("Wear // Tear") == "Wear // Tear"
    assert _name("Wear / Tear") == "Wear // Tear"
    assert _name("wear//tear") == "Wear // Tear"


def test_dfc_front_face_and_full_name():
    front = DB.get("Tamiyo, Inquisitive Student")
    assert front is not None
    full = front.get("name")
    assert DB.get(full) is not None


def test_punctuation_and_case():
    assert _name("jace the mind sculptor") == "Jace, the Mind Sculptor"
    assert _name("ORCISH BOWMASTERS") == "Orcish Bowmasters"


def test_no_substring_substitution():
    # These used to return "_____", "Hellion", "Assemble" via the partial-match loop.
    for missing in ("Totally Unknown Card Zzq", "Kinetic Hellionx", "Avengers Disassembledx"):
        assert DB.get(missing) is None
    assert DB.get("Hellion") is None or DB.get("Hellion").get("name") == "Hellion"
    assert _name("Thor") in (None, "Thor")      # never "Thor, God of Thunder" or anything else


def test_loaders_raise_with_suggestions():
    from data.deck import load_deck_from_text
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            load_deck_from_text("4 Lightning Bolt\n4 Lightnig Bolt\n52 Mountain\n")
            raised = None
        except UnknownCardError as e:
            raised = e
    assert raised is not None and raised.names == ["Lightnig Bolt"]
    assert "Lightning Bolt" in raised.suggestions["Lightnig Bolt"]


def test_dict_loader_no_placeholder():
    import generate_matchup_data as gmd
    import data.stub_decks as sd
    orig = sd.get_stub_deck_list
    sd.get_stub_deck_list = lambda name: {"Lightning Bolt": 4, "Made Up Card Qq": 56}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                gmd.load_deck_and_apl("Some Unregistered Deck Name Qq", "modern")
                raised = False
            except UnknownCardError:
                raised = True
        assert raised
    finally:
        sd.get_stub_deck_list = orig


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL CARD IDENTITY TESTS PASS")
