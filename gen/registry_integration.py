"""
gen/registry_integration.py -- Make generated decks runnable by existing tools.

apl/__init__.py reads data/auto_apl_registry.json as a name-keyed sidecar
(key = _normalize_key(deck_name) -> {module, class, deck_file}) consulted by
get_apl/get_match_apl/get_apl_entry on a miss. Registering a generated deck
there means `python sim.py --deck decks/auto/<id>_modern.txt` and
parallel_sim.py / full_audit.py all pick it up with no special-casing.

Generated APL files live at apl/auto_apls/gen_<hash>.py, importable as the
dotted module `apl.auto_apls.gen_<hash>` (apl/auto_apls is a package).
"""

import os
import re
import json

from gen import REPO_ROOT

CANONICAL_AUTO_REGISTRY = os.path.join(REPO_ROOT, "data", "auto_apl_registry.json")


def normalize_key(name: str) -> str:
    """Mirror apl/__init__._normalize_key strict phase (lower, strip separators)."""
    return name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")


def module_path_for_apl_file(apl_file: str) -> str:
    """apl/auto_apls/gen_<hash>.py -> 'apl.auto_apls.gen_<hash>'."""
    rel = os.path.relpath(os.path.abspath(apl_file), REPO_ROOT)
    return re.sub(r"\.py$", "", rel).replace(os.sep, ".")


def register_generated_deck(deck_key, deck_file, apl_file, apl_class,
                            source="auto_pipeline", smoke_avg_turns=None,
                            registry_path=None, generated_date=""):
    """
    Add/refresh a name-keyed row in data/auto_apl_registry.json so the deck is
    resolvable by name. Returns the written registry row.
    """
    registry_path = registry_path or CANONICAL_AUTO_REGISTRY
    reg = {}
    if os.path.exists(registry_path):
        try:
            with open(registry_path, encoding="utf-8") as f:
                reg = json.load(f)
        except Exception:
            reg = {}

    key = normalize_key(deck_key)
    row = {
        "module": module_path_for_apl_file(apl_file),
        "class": apl_class,
        "deck_file": os.path.relpath(os.path.abspath(deck_file), REPO_ROOT),
        "generated_date": generated_date,
        "source": source,
        "smoke_avg_turns": smoke_avg_turns,
    }
    reg[key] = row

    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    tmp = registry_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, registry_path)
    return {key: row}
