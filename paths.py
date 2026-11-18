"""paths.py -- where mtg-sim looks for things that live outside this repo.

One place for the sibling-repo paths that used to be rebuilt by hand in a
dozen files (#21, #12). Each can be overridden with an environment variable.

Expected layout (the default when no variable is set):

    <workspace>/
        mtg-sim/                  this repo
        mtg-meta-analyzer/        data/mtg_meta.db
        TeamResolve/              modern/ standard/ pioneer/ playbooks, guides/
                                  (older checkouts: My-Website/ and "Team Resolve/")

    MTG_META_DB       full path to mtg_meta.db
    PLAYBOOK_DIR      folder holding the modern/ standard/ pioneer/ playbook folders
                      (MTG_SIM_PLAYBOOK_DIR is accepted too)
    TAC_GUIDES_DIR    folder holding the tac-team .txt guides
"""
import os
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
WORKSPACE = REPO_ROOT.parent


def _first_existing(candidates):
    """First candidate that exists, else the first one (so a 'not found'
    message names the preferred location)."""
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def meta_db_path() -> Path:
    """Path to the mtg-meta-analyzer SQLite DB. Not checked for existence."""
    override = os.environ.get("MTG_META_DB")
    return Path(override) if override else WORKSPACE / "mtg-meta-analyzer" / "data" / "mtg_meta.db"


def connect_meta_db(path=None) -> sqlite3.Connection:
    """Open the meta DB read-only.

    A plain sqlite3.connect() on a wrong path silently creates an empty file
    and every query then returns no rows, which looks like 'no data'. This
    raises FileNotFoundError instead and never creates anything.
    """
    path = Path(path) if path else meta_db_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"mtg-meta-analyzer DB not found at {path}. "
            f"Set MTG_META_DB or check out mtg-meta-analyzer next to mtg-sim.")
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def playbook_dir() -> Path:
    """Folder holding the modern/ standard/ pioneer/ HTML playbooks."""
    override = os.environ.get("PLAYBOOK_DIR") or os.environ.get("MTG_SIM_PLAYBOOK_DIR")
    if override:
        return Path(override)
    return _first_existing([WORKSPACE / "TeamResolve", WORKSPACE / "My-Website"])


def tac_guides_dir() -> Path:
    """Folder holding the tac-team .txt guides."""
    override = os.environ.get("TAC_GUIDES_DIR")
    if override:
        return Path(override)
    return _first_existing([WORKSPACE / "TeamResolve" / "guides",
                            WORKSPACE / "Team Resolve" / "guides"])
