"""matchup_jobs.py — paths for per-matchup subprocess output files.

Layout: data/matchup_jobs/<our_deck_slug>/<opp_slug>.json

Keying by (our_deck, opp) prevents collision when multiple launchers
(e.g. variant + canonical) run concurrent gauntlets. Prior layout
keyed on opp only; concurrent runs against the same opp clobbered
each other's subprocess output. See
harness/knowledge/tech/cache-collision-bug-2026-04-27.md.
"""
from pathlib import Path

BASE_DIR = Path("data/matchup_jobs")


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


def matchup_job_path(our_deck: str, opp: str, base_dir: Path = BASE_DIR) -> Path:
    """Return per-matchup output path keyed by (our_deck, opp)."""
    return Path(base_dir) / _slugify(our_deck) / f"{_slugify(opp)}.json"


def ensure_parent(path: Path) -> Path:
    """Create parent directory if missing; return path unchanged."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
