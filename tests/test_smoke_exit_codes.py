"""
test_smoke_exit_codes.py -- regression for mtg-sim #9.

tests/test_match_engine.py used to catch an exception in its 1000-game phase, print
it, print the success banner, and exit 0. These checks force each phase to fail in
turn (engine calls replaced by fast fakes) and require a nonzero result with no
success banner. Runs standalone (`python tests/test_smoke_exit_codes.py`) or under
pytest.
"""
import contextlib, io, os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_match_engine as tme


def _fake_result():
    return types.SimpleNamespace(winner=1, kill_turn=5, final_life_a=20, final_life_b=0,
                                 damage_by_a=20, damage_by_b=0, win_method="damage")


def _run(fail_phase=None):
    """Run tme.main() with fake engine calls; `fail_phase` in {None, 'single', 100, 1000}."""
    def run_match(*a, **k):
        if fail_phase == "single":
            raise RuntimeError("forced single-match failure")
        return _fake_result()

    def run_match_set(*a, n, seed, **k):
        if fail_phase == n:
            raise RuntimeError(f"forced {n}-game failure")
        return [_fake_result()] * 3

    saved = (tme.run_match, tme.run_match_set, tme.print_match_report)
    tme.run_match, tme.run_match_set = run_match, run_match_set
    tme.print_match_report = lambda *a, **k: None
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = tme.main()
    finally:
        tme.run_match, tme.run_match_set, tme.print_match_report = saved
    return code, out.getvalue()


def test_all_phases_pass_exits_zero_with_banner():
    code, out = _run(None)
    assert code == 0, out
    assert tme.SUCCESS_BANNER in out


def test_1000_game_failure_exits_nonzero_without_banner():
    code, out = _run(1000)
    assert code != 0, out
    assert tme.SUCCESS_BANNER not in out
    assert "forced 1000-game failure" in out


def test_100_game_failure_exits_nonzero_without_banner():
    code, out = _run(100)
    assert code != 0 and tme.SUCCESS_BANNER not in out


def test_single_match_failure_exits_nonzero_without_banner():
    code, out = _run("single")
    assert code != 0 and tme.SUCCESS_BANNER not in out


def test_importing_the_smoke_script_runs_nothing():
    # main() is only called under __main__, so pytest collection is free of side effects
    assert callable(tme.main) and not hasattr(tme, "results")


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as e:
                failed += 1
                print(f"  FAIL {name}: {e}")
    print(f"\n{'ALL PASS' if not failed else f'{failed} FAILED'}")
    sys.exit(1 if failed else 0)
