"""test_sideboard_validation.py -- issue #18.

apply_sideboard_plan matched names by an 8-character prefix, so a plan could
bring in a different card, and it returned decks of any size without a word.
"""
import sys, os, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine import sideboard
from engine.sideboard import apply_sideboard_plan, _fuzzy_match, get_sb_plan


def _card(name, type_line="Instant"):
    return Card(name=name, mana_cost="{1}", cmc=1, type_line=type_line, oracle_text="", colors=[])


def _main():
    return ([_card("Lightning Bolt") for _ in range(4)] + [_card("Ragavan", "Creature") for _ in range(4)]
            + [_card("Mountain", "Basic Land - Mountain") for _ in range(52)])


def _side():
    return ([_card("Kozilek's Command") for _ in range(2)] + [_card("Blood Moon", "Enchantment") for _ in range(3)]
            + [_card("Wrath of the Skies", "Sorcery") for _ in range(2)])


def _apply(sb_in, sb_out):
    os.environ.pop("SIM_DEBUG", None)
    sideboard._WARNED.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        deck = apply_sideboard_plan(_main(), _side(), sb_in, sb_out)
    return deck, out.getvalue()


def _count(deck, name):
    return sum(c.name == name for c in deck)


def test_clean_plan_applies_quietly():
    deck, out = _apply(["2 Blood Moon"], ["2 Lightning Bolt"])
    assert len(deck) == 60 and _count(deck, "Blood Moon") == 2 and _count(deck, "Lightning Bolt") == 2
    assert out == "", out


def test_a_similar_name_is_not_swapped_in():
    # repro 1: Kozilek's Return is not in the sideboard; Kozilek's Command is
    deck, out = _apply(["2 Kozilek's Return"], ["2 Lightning Bolt"])
    assert _count(deck, "Kozilek's Command") == 0
    assert len(deck) == 60 and _count(deck, "Lightning Bolt") == 4, "nothing came in, so nothing goes out"
    assert "Kozilek's Return" in out and "Kozilek's Command" in out, out   # warned, with a hint


def test_typo_does_not_leave_a_58_card_deck():
    # repro 2
    deck, out = _apply(["2 Blod Moon"], ["2 Lightning Bolt"])
    assert len(deck) == 60, len(deck)
    assert "Blod Moon" in out and "does not balance" in out, out


def test_unbalanced_plan_keeps_size_and_applies_what_balances():
    deck, out = _apply(["3 Blood Moon"], ["2 Lightning Bolt"])
    assert len(deck) == 60 and _count(deck, "Blood Moon") == 2 and _count(deck, "Lightning Bolt") == 2
    assert "does not balance" in out


def test_asking_for_more_than_exist_is_reported():
    _, out = _apply(["4 Blood Moon"], ["4 Lightning Bolt"])
    assert "sideboard has 3" in out, out


def test_entry_without_a_quantity_is_reported():
    deck, out = _apply(["Blood Moon"], ["Lightning Bolt"])
    assert len(deck) == 60
    assert out.count("cannot read sideboard-") == 2 and "'Blood Moon'" in out, out


def test_warnings_print_once_and_are_ascii():
    os.environ.pop("SIM_DEBUG", None)
    sideboard._WARNED.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for _ in range(5):
            apply_sideboard_plan(_main(), _side(), ["2 Blod Moon"], ["2 Lightning Bolt"])
    text = out.getvalue()
    assert text.count("not found in the sideboard") == 1 and text.isascii(), text


def test_sim_debug_raises():
    os.environ["SIM_DEBUG"] = "1"
    try:
        apply_sideboard_plan(_main(), _side(), ["2 Blod Moon"], ["2 Lightning Bolt"])
        raise AssertionError("expected ValueError under SIM_DEBUG")
    except ValueError as e:
        assert "Blod Moon" in str(e)
    finally:
        del os.environ["SIM_DEBUG"]


def test_matcher_rules():
    names = ["Kozilek's Command", "Blood Moon", "Wrath of the Skies", "Wrath of God"]
    assert _fuzzy_match("blood moon", names) == "Blood Moon"            # case
    assert _fuzzy_match("Kozileks Command", names) == "Kozilek's Command"  # punctuation
    assert _fuzzy_match("Wrath of the", names) == "Wrath of the Skies"  # unique partial
    assert _fuzzy_match("Wrath", names) is None                         # ambiguous
    assert _fuzzy_match("Kozilek's Return", names) is None              # shared prefix only
    assert _fuzzy_match("Mo", names) is None                            # too short


def test_missing_playbook_folder_is_reported():
    os.environ.pop("SIM_DEBUG", None)
    os.environ["MTG_SIM_PLAYBOOK_DIR"] = "/nonexistent/playbooks"
    sideboard._WARNED.clear()
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            get_sb_plan("Boros Energy", "Elves", playbooks={})
    finally:
        del os.environ["MTG_SIM_PLAYBOOK_DIR"]
    assert "/nonexistent/playbooks" in out.getvalue() and "MTG_SIM_PLAYBOOK_DIR" in out.getvalue()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_sideboard_validation: OK")
