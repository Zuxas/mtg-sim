"""Milestone three, phase 2: engine v2 as an explicit EXPERIMENTAL launcher option.

Proves: the legacy path is unchanged when v2 is not selected; an explicit selection reaches engine/v2;
a supported Burn mirror completes (single games and Bo3); unsupported / unknown cards and unsupported
sideboards are refused before play with their exact names; the same seed reproduces the same record;
replay reproduces the launcher result; a v2 engine error is reported and never falls back to a legacy
engine."""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import parallel_launcher as PL                                            # noqa: E402
import v2_launch                                                          # noqa: E402

BURN = "mono_red_aggro_modern"


class _Boom(AssertionError):
    pass


def _no_legacy(*a, **k):
    raise _Boom("the legacy launcher was called on the v2 path (fallback)")


def _run(argv, monkey=None):
    """main(argv) with the legacy launcher replaced by a tripwire; returns (exit code, stdout)."""
    import contextlib
    import io
    saved = PL.launch_all
    PL.launch_all = _no_legacy
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = PL.main(argv)
    finally:
        PL.launch_all = saved
    return code, buf.getvalue()


def _v2(tmp, *extra):
    return ["--engine", "v2", "--deck", BURN, "--opponent", BURN, "--record-dir", tmp, *extra]


def test_legacy_path_is_unchanged_when_v2_is_not_selected():
    import format_config
    calls = []
    saved_launch, saved_field, saved_v2 = PL.launch_all, format_config.get_field, v2_launch.run
    PL.launch_all = lambda *a, **k: calls.append((a, k))
    format_config.get_field = lambda fmt, top_n: {"Field Deck": 100.0, "_fmt": fmt, "_top": top_n}
    v2_launch.run = _no_legacy                                            # v2 must not be reached
    try:
        assert PL.main(["--deck", "Boros Energy", "--format", "modern", "--n", "7", "--seed", "3"]) == 0
        args = PL.build_parser().parse_args([])
    finally:
        PL.launch_all, format_config.get_field, v2_launch.run = saved_launch, saved_field, saved_v2
    (a, k), = calls
    assert a == ("Boros Energy", "modern", {"Field Deck": 100.0, "_fmt": "modern", "_top": 20}, 7, 20, 3)
    assert k == {"inner_workers": 1}
    assert (args.engine, args.deck, args.format, args.n, args.cores, args.top_n, args.seed) == \
        ("legacy", "Legacy Humans", "legacy", 1000, 20, 20, 42)          # the old defaults


def test_explicit_v2_selection_reaches_engine_v2_and_is_labelled_experimental():
    from engine.v2 import ENGINE_VERSION
    with tempfile.TemporaryDirectory() as tmp:
        code, out = _run(_v2(tmp, "--games", "2", "--seed", "11", "--pilot-a", "aggro"))
        assert code == 0 and "ENGINE V2 (EXPERIMENTAL)" in out
        s = json.load(open(os.path.join(tmp, "summary.json")))
        assert s["engine"] == "v2" and s["status"] == "EXPERIMENTAL" and s["engine_version"] == ENGINE_VERSION
        assert s["pilots"] == ["aggro", "random"] and s["count"] == 2
        rec = json.load(open(os.path.join(tmp, "game_0000.json")))
        assert rec["engine_version"] == ENGINE_VERSION and rec["config"]["deck_rules"] == "constructed"
    assert "engine.v2.game" in sys.modules


def test_v2_requires_both_explicit_decks_and_positive_limits():
    code, out = _run(["--engine", "v2", "--opponent", BURN])
    assert code == 2 and "needs explicit --deck and --opponent" in out
    code, out = _run(["--engine", "v2", "--deck", BURN])
    assert code == 2 and "needs explicit --deck and --opponent" in out
    with tempfile.TemporaryDirectory() as tmp:
        code, out = _run(_v2(tmp, "--games", "0"))
        assert code == 2 and "must be positive" in out and not os.path.exists(os.path.join(tmp, "summary.json"))


def test_missing_sideboard_is_a_pre_play_refusal():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = os.path.join(tmp, "run")
        code, out = _run(_v2(run_dir, "--mode", "bo3", "--side-a", "missing-sideboard", "--side-b", "none"))
        assert code == 2 and "REFUSED before play" in out and "missing-sideboard.txt" in out
        assert not os.path.exists(run_dir)


def test_supported_burn_mirror_completes_single_games_and_bo3():
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = _run(_v2(tmp, "--games", "3", "--seed", "5", "--pilot-a", "aggro", "--pilot-b", "aggro"))
        s = json.load(open(os.path.join(tmp, "summary.json")))
        assert code == 0 and sum(v for k, v in s["results"].items() if k != "engine_error") == 3
        assert s["results"]["engine_error"] == 0 and set(s["results"]) == {
            "win_p0", "win_p1", "draw", "turn_limit_draw", "engine_error"}
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = _run(_v2(tmp, "--mode", "bo3", "--side-a", "none", "--side-b", "none", "--seed", "9"))
        s = json.load(open(os.path.join(tmp, "summary.json")))
        assert code == 0 and s["mode"] == "bo3" and os.path.exists(os.path.join(tmp, "match_0000.json"))


def test_unsupported_and_unknown_cards_are_refused_before_play_with_exact_names():
    with tempfile.TemporaryDirectory() as tmp:
        code, out = _run(["--engine", "v2", "--deck", "boros_energy_modern", "--opponent", BURN,
                          "--record-dir", os.path.join(tmp, "run")])
        assert code == 2 and "REFUSED before play" in out
        assert "Ragavan, Nimble Pilferer" in out and "Guide of Souls" in out
        assert not os.path.exists(os.path.join(tmp, "run"))                 # nothing started, nothing saved
        bad = os.path.join(tmp, "typo.txt")
        lines = open(os.path.join(ROOT, "decks", f"{BURN}.txt"), encoding="utf-8").read().replace(
            "4 Lightning Bolt", "4 Lightning Boltt")
        open(bad, "w", encoding="utf-8").write(lines)
        code, out = _run(["--engine", "v2", "--deck", bad, "--opponent", BURN, "--record-dir", os.path.join(tmp, "r2")])
        assert code == 2 and "unknown card names: Lightning Boltt" in out


def test_unsupported_sideboard_is_refused_before_a_bo3():
    with tempfile.TemporaryDirectory() as tmp:
        code, out = _run(_v2(os.path.join(tmp, "run"), "--mode", "bo3"))       # the real Burn sideboard
        assert code == 2 and "sideboard of mono_red_aggro_modern" in out
        for name in ("Chalice of the Void", "Deflecting Palm", "Sanctifier en-Vec"):
            assert name in out
        assert not os.path.exists(os.path.join(tmp, "run"))


def test_same_seed_reproduces_the_same_record():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        for d in (a, b):
            assert _run(_v2(d, "--games", "2", "--seed", "21", "--pilot-a", "aggro"))[0] == 0
        for name in ("game_0000.json", "game_0001.json"):
            assert open(os.path.join(a, name)).read() == open(os.path.join(b, name)).read()


def test_replay_reproduces_the_launcher_result():
    with tempfile.TemporaryDirectory() as tmp:
        assert _run(_v2(tmp, "--games", "1", "--seed", "31", "--pilot-a", "aggro", "--pilot-b", "aggro"))[0] == 0
        s = json.load(open(os.path.join(tmp, "summary.json")))
        rec = json.load(open(os.path.join(tmp, "game_0000.json")))
        code, out = _run(["--engine", "v2", "--replay", os.path.join(tmp, "game_0000.json")])
        assert code == 0 and "replay OK" in out and str(tuple(rec["result"])) in out
        won = "win_p0" if rec["result"][:2] == ["win", 0] else "win_p1" if rec["result"][0] == "win" else None
        assert won is None or s["results"][won] == 1
        rec["transition_hashes"][3] = "0" * 64                              # a tampered record fails loudly
        bad = os.path.join(tmp, "bad.json")
        json.dump(rec, open(bad, "w"))
        code, out = _run(["--engine", "v2", "--replay", bad])
        assert code == 1 and "REPLAY FAILED" in out


def test_a_v2_engine_error_is_reported_and_never_falls_back():
    from engine.v2 import game as G
    saved = G.Game.run

    def boom(self, policies, max_actions=200000):
        raise RuntimeError("injected v2 engine failure")
    G.Game.run = boom
    try:
        with tempfile.TemporaryDirectory() as tmp:
            code, out = _run(_v2(tmp, "--games", "2", "--seed", "1"))          # the tripwire forbids legacy
            s = json.load(open(os.path.join(tmp, "summary.json")))
    finally:
        G.Game.run = saved
    assert code == 1 and "ENGINE ERROR" in out and "ENGINE ERRORS 2" in out
    assert s["results"]["engine_error"] == 2 and s["engine_errors"][0]["error"].startswith("RuntimeError")
    assert s["results"]["win_p0"] == s["results"]["win_p1"] == s["results"]["draw"] == 0   # no floor, no fill-in


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("LAUNCHER V2 TESTS PASS")
