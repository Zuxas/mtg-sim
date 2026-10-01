"""Milestone three, phase 1: engine v2 vs real MTGO gameplay. Parser unit tests on synthetic log
lines, and re-execution of every committed comparison fixture (data/v2_gameplay_fixtures.json):
each must reproduce its stored outcome, and no supported, reconstructable episode may have an
unexplained rules divergence."""
import collections
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from calibration.v2_gameplay import FIXTURES, extract                     # noqa: E402
from calibration.v2_gameplay_exec import run_fixture                      # noqa: E402

ENGINE_CLASSES = ("unexplained", "engine_rules_bug", "card_implementation_bug")


def _dat(lines) -> str:
    """A synthetic MTGO game log: '@P'-prefixed text runs separated by binary noise."""
    blob = b""
    for ln in lines:
        blob += b"\x00\x01" + b"@P" + ln.encode("ascii") + b"\x02"
    d = tempfile.mkdtemp()
    p = os.path.join(d, "Match_GameLog_test0000-0000-0000-0000-000000000000.dat")
    open(p, "wb").write(blob)
    return p


def _card(name, n):
    return f"@[{name}@:1,{n}:@]"


def test_parser_turns_with_digit_names_mulligans_and_suspend():
    p = _dat([
        "medic8923 chooses to play first.",
        "medic8923 mulligans to six cards.",
        "medic8923 mulligans to six cards.",                                  # duplicated line in real logs
        "medic8923 puts a card on the bottom of their library and begins the game with six cards in hand.",
        "Zaxos begins the game with seven cards in hand.",
        "Turn 1: medic8923",
        f"medic8923 plays {_card('Mountain', 10)}.",
        f"medic8923 exiles {_card('Rift Bolt', 11)} with 1 time counter.",
        "Turn 1: Zaxos",
        "Turn 2: medic8923",
        f"medic8923 puts a triggered ability from {_card('Rift Bolt', 12)} onto the stack (Suspend 1@-{{R}}).",
        f"medic8923 removes a time counter from {_card('Rift Bolt', 12)}.",
        f"medic8923 puts a triggered ability from {_card('Rift Bolt', 12)} onto the stack (Suspend 1@-{{R}}).",
        f"medic8923 casts {_card('Rift Bolt', 13)} without paying its mana cost with suspend targeting Zaxos.",
        "medic8923 wins the game.",
    ])
    fx = extract(p)
    mull = next(f for f in fx if f["mechanic"] == "mulligan")
    assert mull["prestate"]["mulligans"] == 1 and mull["action"] == {"bottom": 1, "final_hand": 6}
    sus = next(f for f in fx if f["mechanic"] == "suspend")
    assert sus["prestate"]["own_turn"] is True                               # 'medic8923' resolved, digits kept
    assert sus["action"]["free_cast_target_kind"] == "player" and len(sus["action"]["observed_follow_up"]) == 4
    for f in (mull, sus):
        assert run_fixture(f)["status"] == "pass"


def test_parser_searing_blaze_relationship_and_play_draw_chooser():
    p = _dat([
        "Ann chooses to play first.",
        "Turn 1: Ann",
        f"Ann plays {_card('Mountain', 1)}.",
        f"Ann casts {_card('Goblin Guide', 2)}.",
        "Turn 1: Bob",
        f"Bob plays {_card('Mountain', 3)}.",
        f"Bob casts {_card('Searing Blaze', 4)} targeting Ann, and {_card('Goblin Guide', 2)}.",
        "Bob wins the game.",
        "Ann chooses to play first.",                                          # game 2: the loser (Ann) chooses
        "Turn 1: Ann",
        "Ann has conceded from the game.",
    ])
    fx = extract(p)
    blaze = next(f for f in fx if f["mechanic"] == "searing_blaze")
    assert blaze["prestate"]["creature_controller"] == "PlayerA" and blaze["expected"]["relationship_ok"] is True
    assert blaze["expected"]["landfall_damage"] == 3                          # Bob played a land this turn
    pd = next(f for f in fx if f["mechanic"] == "play_draw_choice")
    assert pd["prestate"]["previous_loser"] == "PlayerA" and pd["action"]["chooser"] == "PlayerA"
    assert run_fixture(blaze)["status"] == "pass" and run_fixture(pd)["status"] == "pass"
    payload = json.dumps(fx)
    assert "Ann" not in payload and "Bob" not in payload and "Match_GameLog_" not in payload


def test_every_committed_fixture_reproduces_its_outcome():
    fx = json.load(open(FIXTURES, encoding="utf-8"))
    assert len(fx) > 1000
    changed, engine = [], []
    for f in fx:
        r = run_fixture(f)
        if (r["status"], r["classification"]) != (f["result"]["status"], f["result"]["classification"]):
            changed.append((f["id"], f["result"]["status"], r["status"], r["detail"][:120]))
        if r["status"] != "pass" and r["classification"] in ENGINE_CLASSES:
            engine.append((f["id"], r["detail"][:160]))
    assert not engine, engine[:5]                                             # the comparison gate
    assert not changed, changed[:5]


def test_fixtures_are_traceable_and_self_contained():
    fx = json.load(open(FIXTURES, encoding="utf-8"))
    need = {"id", "mechanic", "source", "observed", "prestate", "legal_actions_expected", "selected_action",
            "expected_result", "result", "passed", "unobservable", "substitutions"}
    for f in fx:
        assert need <= set(f), (f["id"], need - set(f))
        assert {"file", "match", "game", "lines"} <= set(f["source"])
        assert f["source"]["file"] == f"match_{f['source']['match']}.dat"
        assert len(f["source"]["match"]) == 12
    classes = collections.Counter(f["result"]["classification"] for f in fx if not f["passed"])
    assert set(classes) <= {"unsupported_mechanic", "parser_data_ambiguity", "strategic_choice"}, classes


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("GAMEPLAY COMPARISON TESTS PASS")
