"""test_paths.py -- issues #21 and #12.

Sibling-repo paths (the meta DB, the playbooks) were rebuilt by hand in a
dozen files, one with a hardcoded E:\\ drive and one relative to the working
directory, and the playbook path still pointed at the old My-Website repo.
"""
import sys, os, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import paths

ENV = ("MTG_META_DB", "PLAYBOOK_DIR", "MTG_SIM_PLAYBOOK_DIR", "TAC_GUIDES_DIR")


def _clean_env(fn):
    saved = {k: os.environ.pop(k, None) for k in ENV}
    real_ws = paths.WORKSPACE
    try:
        return fn()
    finally:
        paths.WORKSPACE = real_ws
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_defaults_are_siblings_of_the_repo():
    def check():
        assert paths.meta_db_path() == paths.REPO_ROOT.parent / "mtg-meta-analyzer" / "data" / "mtg_meta.db"
        assert paths.playbook_dir().parent == paths.REPO_ROOT.parent
    _clean_env(check)


def test_env_overrides():
    def check():
        os.environ["MTG_META_DB"] = "/x/meta.db"
        os.environ["TAC_GUIDES_DIR"] = "/x/guides"
        assert paths.meta_db_path() == Path("/x/meta.db")
        assert paths.tac_guides_dir() == Path("/x/guides")
        os.environ["MTG_SIM_PLAYBOOK_DIR"] = "/x/alias"
        assert paths.playbook_dir() == Path("/x/alias")
        os.environ["PLAYBOOK_DIR"] = "/x/books"
        assert paths.playbook_dir() == Path("/x/books"), "PLAYBOOK_DIR wins over the alias"
    _clean_env(check)


def test_current_teamresolve_layout_is_found():
    """#12: a checkout next to the TeamResolve repo (modern/ standard/ pioneer/
    at its top level) must find its playbooks."""
    def check():
        with tempfile.TemporaryDirectory() as ws:
            ws = Path(ws)
            (ws / "TeamResolve" / "modern").mkdir(parents=True)
            (ws / "TeamResolve" / "guides").mkdir()
            book = ws / "TeamResolve" / "modern" / "boros-energy-playbook.html"
            book.write_text("<html></html>", encoding="utf-8")
            (ws / "My-Website" / "modern").mkdir(parents=True)     # old layout also present
            paths.WORKSPACE = ws
            assert paths.playbook_dir() == ws / "TeamResolve", "current repo name wins"
            assert book in list((paths.playbook_dir() / "modern").glob("*playbook*.html"))
            assert paths.tac_guides_dir() == ws / "TeamResolve" / "guides"
    _clean_env(check)


def test_old_layout_still_works():
    def check():
        with tempfile.TemporaryDirectory() as ws:
            ws = Path(ws)
            (ws / "My-Website" / "standard").mkdir(parents=True)
            (ws / "Team Resolve" / "guides").mkdir(parents=True)
            paths.WORKSPACE = ws
            assert paths.playbook_dir() == ws / "My-Website"
            assert paths.tac_guides_dir() == ws / "Team Resolve" / "guides"
    _clean_env(check)


def test_missing_db_raises_and_creates_nothing():
    with tempfile.TemporaryDirectory() as d:
        missing = Path(d) / "nope.db"
        try:
            paths.connect_meta_db(missing)
            raise AssertionError("expected FileNotFoundError")
        except FileNotFoundError as e:
            assert "MTG_META_DB" in str(e)
        assert not missing.exists(), "a failed open must not create an empty DB"


def test_db_is_opened_read_only():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "with space" / "meta.db"
        db.parent.mkdir()
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE t (x)")
        con.execute("INSERT INTO t VALUES (1)")
        con.commit(); con.close()
        ro = paths.connect_meta_db(db)
        assert ro.execute("SELECT x FROM t").fetchall() == [(1,)]
        try:
            ro.execute("INSERT INTO t VALUES (2)")
            raise AssertionError("expected a read-only error")
        except sqlite3.OperationalError:
            pass
        finally:
            ro.close()


def test_override_set_after_import_still_applies():
    import meta_bridge
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "meta.db"
        sqlite3.connect(db).close()
        os.environ["MTG_META_DB"] = str(db)
        try:
            con = meta_bridge._conn()
            assert con is not None, "bridge kept the path it saw at import"
            con.close()
        finally:
            del os.environ["MTG_META_DB"]


def test_no_hand_built_paths_left():
    """The copies the issue lists must go through paths.py."""
    root = paths.REPO_ROOT
    for rel in ("meta_bridge.py", "db_bridge.py", "sim_pt_sos_swiss.py",
                "scripts/build_stubs.py", "scripts/arl_generate_deck.py",
                "scripts/build_meta_shares.py", "scripts/build_priority_queue.py",
                "scripts/cast_weighted_coverage.py", "scripts/consensus_75.py",
                "tests/test_modern_apls.py", "apl/playbook_parser.py", "engine/sideboard.py"):
        src = (root / rel).read_text(encoding="utf-8")
        code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("#", '"', "'")))
        assert "paths." in code, rel
        for banned in ('"mtg-meta-analyzer"', "'mtg-meta-analyzer'", "E:\\\\vscode", '"My-Website"',
                       "../mtg-meta-analyzer"):
            assert banned not in code, f"{rel} still builds a path by hand: {banned}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_paths: OK")
