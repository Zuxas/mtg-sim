"""
gen/apl_cache.py -- Decklist-hash keyed auto-APL reuse (cost control).

"Always auto-generate an APL per candidate" is only affordable if generation is
cached and reused aggressively. This layer keys an APL on the DECKLIST HASH (not
the deck name), with a three-tier reuse hierarchy:

  1. exact decklist-hash hit   -> load apl/auto_apls/gen_<hash>.py (free)
  2. package-set sibling hit    -> a previously generated deck with the SAME package
                                   set (differs only in mana base / flex slots) shares
                                   its APL; combo lines are package-driven (free)
  3. miss                       -> generate via Claude using a SYNTHETIC PlaybookData
                                   built from the package synergy notes, bypassing the
                                   find_playbook requirement in apl/auto_apl.py (paid)

Generation is injectable (`generate_fn`) so the reuse logic is unit-testable
offline without any network call.

Cache: apl/auto_apls/gen_<hash>.py + a row in data/auto_apl_registry.json.
"""

import os
import re
import sys
import json
import hashlib
import importlib.util

from gen import REPO_ROOT, PIPELINE_DATA

AUTO_APL_DIR = os.path.join(REPO_ROOT, "apl", "auto_apls")
# Hash-keyed index of generated APLs (decklist_hash -> module). Kept separate
# from data/auto_apl_registry.json (the name-keyed sidecar apl/__init__ reads)
# so the two schemas never collide. Name-keyed registration lives in
# gen/registry_integration.py.
AUTO_REGISTRY = os.path.join(PIPELINE_DATA, "apl_index.json")


def decklist_hash(mainboard: dict) -> str:
    """Stable, order-independent hash of a mainboard {name: qty}."""
    lines = "\n".join(f"{qty} {name}" for name, qty in sorted(mainboard.items()))
    return hashlib.sha1(lines.encode("utf-8")).hexdigest()[:16]


def package_set_key(packages) -> str:
    return hashlib.sha1("+".join(sorted(packages)).encode("utf-8")).hexdigest()[:12]


def build_synthetic_playbook(cand, packages=None, fmt="modern"):
    """
    Construct a PlaybookData from a DeckCandidate + its packages so the existing
    apl/auto_apl Claude path can run without a hand-authored playbook file.
    """
    from apl.playbook_parser import PlaybookData

    engines, notes, role = [], [], "Midrange"
    if packages:
        for pid in cand.packages:
            pkg = packages.get(pid)
            if not pkg:
                continue
            if pkg.role in ("combo-core", "aggro-core"):
                role = "Combo" if pkg.role == "combo-core" else "Aggro"
            if pkg.synergy_notes:
                notes.append(f"[{pkg.name}] {pkg.synergy_notes}")
                engines.append({"title": pkg.name, "body": pkg.synergy_notes})

    return PlaybookData(
        deck_name=cand.name,
        format_name=fmt,
        role=role,
        kill_turn=str(cand.metadata.get("kill_turn", "4-6")),
        colors="".join(cand.color_identity),
        mainboard=dict(cand.mainboard),
        sideboard=dict(cand.sideboard),
        game_plan=" ".join(notes)[:1200] or "Execute the deck's core synergy and close the game.",
        strengths="",
        weaknesses="",
        mulligan="Keep hands with a workable land count and a path to the core plan.",
        engines=engines,
    )


def _default_generate(pb) -> str:
    """Generate APL source via the existing Claude path in apl/auto_apl.py."""
    from apl.auto_apl import _build_prompt, _call_claude, _clean_code
    prompt = _build_prompt(pb)
    return _clean_code(_call_claude(prompt))


def _load_apl_from_file(path, mod_tag):
    """Import a cached .py and return an instantiated BaseAPL subclass (or None)."""
    from apl.base_apl import BaseAPL
    try:
        spec = importlib.util.spec_from_file_location(f"gen_apl_{mod_tag}", str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, BaseAPL) and obj is not BaseAPL:
                return obj()
    except Exception as e:
        print(f"[apl_cache] load failed for {path}: {e}")
    return None


def _read_registry(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _write_registry(path, reg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, path)


def get_apl_for_candidate(cand, packages=None, fmt="modern",
                          generate_fn=None, cache_dir=None, registry_path=None,
                          allow_fallback=True):
    """
    Return (apl_instance, info). info: {source, hash, package_key, fidelity}.
      source in {"hash_hit","sibling","generated","fallback"}.

    generate_fn(playbook)->source lets tests avoid the network; defaults to Claude.
    """
    cache_dir = cache_dir or AUTO_APL_DIR
    registry_path = registry_path or AUTO_REGISTRY
    generate_fn = generate_fn or _default_generate
    os.makedirs(cache_dir, exist_ok=True)

    h = decklist_hash(cand.mainboard)
    pkey = package_set_key(cand.packages)
    reg = _read_registry(registry_path)
    cache_file = os.path.join(cache_dir, f"gen_{h}.py")
    fidelity = cand.metadata.get("fidelity", "high")
    info = {"hash": h, "package_key": pkey, "fidelity": fidelity}

    # tier 1: exact decklist hash
    if h in reg and os.path.exists(os.path.join(REPO_ROOT, reg[h]["deck_module"])):
        apl = _load_apl_from_file(os.path.join(REPO_ROOT, reg[h]["deck_module"]), h)
        if apl:
            info["source"] = "hash_hit"
            return apl, info
    if os.path.exists(cache_file):
        apl = _load_apl_from_file(cache_file, h)
        if apl:
            info["source"] = "hash_hit"
            return apl, info

    # tier 2: package-set sibling
    for khash, row in reg.items():
        if row.get("package_key") == pkey:
            sib = os.path.join(REPO_ROOT, row["deck_module"])
            if os.path.exists(sib):
                apl = _load_apl_from_file(sib, h)
                if apl:
                    reg[h] = {**row, "package_key": pkey, "source": "sibling_of:" + khash}
                    _write_registry(registry_path, reg)
                    info["source"] = "sibling"
                    return apl, info

    # tier 3: generate
    try:
        pb = build_synthetic_playbook(cand, packages, fmt)
        source = generate_fn(pb)
        header = (f"# Auto-generated APL (gen pipeline) for {cand.name}\n"
                  f"# decklist_hash={h} package_key={pkey}\n\n")
        tmp = cache_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(header + source)
        os.replace(tmp, cache_file)
        apl = _load_apl_from_file(cache_file, h)
        if apl:
            try:
                deck_module = os.path.relpath(cache_file, REPO_ROOT)
            except ValueError:
                # Windows: cache dir and repo can be on different drives
                # (e.g. C:\ temp vs E:\ repo) -> relpath raises. Store the
                # absolute path instead so generation does not silently fail.
                deck_module = os.path.abspath(cache_file)
            reg[h] = {
                "deck_module": deck_module,
                "class": type(apl).__name__,
                "package_key": pkey,
                "source": "auto_pipeline",
            }
            _write_registry(registry_path, reg)
            info["source"] = "generated"
            return apl, info
    except Exception as e:
        print(f"[apl_cache] generation failed for {cand.name}: {e}")

    # fallback
    if allow_fallback:
        from apl.generic_apl import GenericAPL
        role = "combo" if any((packages or {}).get(p) and
                              (packages or {})[p].role == "combo-core"
                              for p in cand.packages) else "aggro"
        info["source"] = "fallback"
        info["fidelity"] = "low"
        return GenericAPL(deck_name=cand.name, role=role), info
    return None, info
