"""test_gauntlet_snapshot.py -- gauntlet_snapshot.py reads the snapshots
mtg-meta-analyzer saves (Tournament Prep > GAUNTLET, schema gauntlet@1).

The fixture was written by mtg-meta-analyzer's own save_gauntlet() from a
synthetic database (fake players and events), so this checks the real
cross-repo contract: schema tag, content hash, field shape, decklist text.

Run: python tests/test_gauntlet_snapshot.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gauntlet_snapshot import (SCHEMA, decklist_text, describe, field,  # noqa: E402
                               load_snapshot, missing_lists)

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "gauntlet_snapshot_modern.json")


def _write(data):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, f)
    f.close()
    return f.name


def test_loads_the_analyzer_fixture():
    snap = load_snapshot(FIXTURE)
    assert snap["schema"] == SCHEMA
    assert field(snap) == {"Boros Energy": 60.0, "Eldrazi Tron": 30.0, "Living End": 10.0}
    assert list(field(snap, top_n=2)) == ["Boros Energy", "Eldrazi Tron"]
    assert abs(sum(field(snap).values()) - 100) < 0.2


def test_decklist_text_parses_as_a_decklist():
    snap = load_snapshot(FIXTURE)
    text = decklist_text(snap, "boros energy")            # case-insensitive
    assert text.splitlines()[0] == "20 Mountain"
    main, side = text.split("\n\nSideboard\n")
    assert sum(int(ln.split(" ", 1)[0]) for ln in main.splitlines()) == 60
    assert side.strip() == "15 Wear // Tear"
    assert decklist_text(snap, "Not A Deck") is None
    assert missing_lists(snap) == []


def test_edited_file_is_rejected():
    data = json.load(open(FIXTURE, encoding="utf-8"))
    data["field"]["Living End"] = 50.0
    path = _write(data)
    try:
        load_snapshot(path)
        raise AssertionError("an edited snapshot must not load")
    except ValueError as e:
        assert "hash mismatch" in str(e)
    finally:
        os.unlink(path)


def test_wrong_schema_is_rejected():
    path = _write({"schema": "something/else@1", "field": {}})
    try:
        load_snapshot(path)
        raise AssertionError("a foreign file must not load")
    except ValueError as e:
        assert "not a" in str(e)
    finally:
        os.unlink(path)


def test_selected_deck_without_a_list_is_reported():
    data = json.load(open(FIXTURE, encoding="utf-8"))
    for e in data["entries"]:
        if e["archetype"] == "Living End":
            e["decklist"] = None
    snap = dict(data)
    assert missing_lists(snap) == ["Living End"]
    assert any("NO LIST" in ln for ln in describe(snap))
    assert all(ln.isascii() for ln in describe(snap))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS: {name}")
    print("ALL GAUNTLET SNAPSHOT TESTS PASS")
