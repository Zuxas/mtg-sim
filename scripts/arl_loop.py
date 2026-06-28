#!/usr/bin/env python3
"""arl_loop.py -- main runner for the Autonomous Research Loop (ARL).

CONTRACT
========
The ARL explores the MTG metagame autonomously: it generates candidate
decklists, writes APL stubs, smoke-tests them, runs field gauntlets, evaluates
field-weighted win rate (FWR), promotes/mutates/discards, and logs everything
to loop_state.json. Jermey is the human-as-interrupt-handler: he can pause,
steer, or spot-check at any clean iteration boundary without stopping a run.

All loop state lives in mtg-sim/loop_state.json and is owned exclusively by
arl_state.py (atomic, Ctrl-C-safe writes). This runner NEVER runs git, NEVER
commits, NEVER touches engine/, and caps gauntlets at 200 games/matchup unless
a steer directive explicitly raises the cap.

ONE ITERATION (high level): load state -> (generate batch if queue empty) ->
pick pending item -> ensure deck file -> ensure APL file -> register APL ->
smoke -> resolution guard -> gauntlet x2 -> evaluate -> HITL gate -> apply
steer -> repeat (unless --once / max-iter / paused).

DOCUMENTED SPEC DEVIATIONS
==========================
B1 (real CLI flags): the spec's smoke/gauntlet command sketches were a guide.
   The real sim.py exposes --deck/--apl/--n/--no-chart/--no-claude/--seed and
   prints "Win rate       : X%"; the real parallel_launcher.py exposes
   --deck/--format/--n/--top-n/--cores/--seed and prints
   "Field-weighted match win%: X%". Those verified flags/parses are used here.

B2 (register-before-gauntlet, extended to register-before-smoke): the auto APL
   is registered into data/auto_apl_registry.json immediately after the APL
   file is ensured -- i.e. BEFORE the smoke as well as before the gauntlet.
   Reason: sim.py's --apl override resolves through apl.get_apl(), which only
   sees an auto APL once it is registered; registering first means the smoke
   actually exercises OUR APL instead of silently falling back to HumansAPL.
   The post-register RESOLUTION GUARD still runs before the gauntlet and uses
   the known class name as the discriminator (a GoldfishAdapter wrapping our
   class is correct resolution; anything else is apl_unresolved).

B3 (distillation rescoped + optimize/mutate materialization): the sequencing-
   telemetry distillation pass (arl_distill.py) is NOT auto-invoked from this
   loop; it stays a manual/▸separately-scheduled step. Relatedly, optimize and
   mutate do not re-enqueue identical re-tests (which would infinite-loop on a
   deterministic sim). Instead they MATERIALIZE distinct variant deck files
   (an OUT/IN swap, sourced from tuning_loop when Ollama is healthy, else a
   deterministic sideboard swap) and enqueue those as first-class candidates.
   Variant items are not themselves re-mutated, bounding recursion.

Seeds: gauntlet run 1 uses seed=42 (reproducible). Run 2 uses seed=43 so the
two runs are independent samples and the >8pp variance gate is live rather than
dead code (42/42 would always be identical on a deterministic engine).

ASCII-only output. Exit 0 on a clean stop (done/paused/no-work), 1 on a hard
internal error.
"""

import os
import re
import sys
import glob
import json
import shutil
import argparse
import subprocess
from datetime import datetime, timezone

# --- Mandatory cross-repo sys.path setup ---
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(
    os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts")
)
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Leaf ARL modules (light imports; safe at module load) ----------------------
import arl_state  # noqa: E402
import arl_generate_deck  # noqa: E402
import arl_generate_apl  # noqa: E402
import arl_profile  # noqa: E402  (heavy deps are lazy; safe at import time)

# ARL hardening trio: FP-validator (promote veto + cross-session memory) + approval
# gate. Sibling imports (scripts/ is sys.path[0] at launch). Guarded so the loop still
# runs if the modules are absent. Loop-state/backlog write-discipline is already enforced
# at the arl_state._persist_json chokepoint, so arl_write_verify isn't imported here.
try:
    import arl_fp_validator as fp  # noqa: E402
    import arl_approval as ap  # noqa: E402
except Exception:
    fp = None
    ap = None

# Optional hardening helpers -- import what truly exists, degrade gracefully.
# agent_hardening provides LoopController + check_ollama_health (NOT
# atomic_write_json -- that lives in engine.atomic_json). Guard the import so
# --help and read-only paths still work if the harness module is missing.
try:  # noqa: E402
    from agent_hardening import LoopController as _LoopController  # type: ignore
except Exception:  # noqa: BLE001
    _LoopController = None
try:  # noqa: E402
    from agent_hardening import check_ollama_health as _check_ollama_health  # type: ignore
except Exception:  # noqa: BLE001
    _check_ollama_health = None

DEFAULT_GAUNTLET_CAP = 200
DEFAULT_PROMOTE_THRESHOLD = getattr(arl_state, "DEFAULT_PROMOTE_THRESHOLD", 60.0)
MUTATE_LOW = 55.0  # [MUTATE_LOW, promote_threshold) -> mutate

WIN_RATE_RE = re.compile(r"Win rate\s*:\s*([\d.]+)%")
FWR_RE = re.compile(r"Field-weighted match win%\s*:\s*([\d.]+)%")
HUMANS_FALLBACK_MARKERS = ("Humans (fallback)", "not in registry",
                           "falling back to HumansAPL")


def _is_fallback_apl(resolved):
    """True if the resolved APL is the Humans/default fallback (not a real
    archetype APL). Checks the object and any wrapped .inner for a 'Humans' class
    name. Used by the resolution guard and the ensure-APL step so the loop never
    treats a silent HumansAPL fallback as real, and never regenerates over a
    legitimate canonical APL."""
    if resolved is None:
        return True
    names = [type(resolved).__name__]
    inner = getattr(resolved, "inner", None)
    if inner is not None:
        names.append(type(inner).__name__)
    return any("Humans" in n for n in names)


def _real_apl_class(resolved):
    """Best class-name for a resolved (non-fallback) APL, unwrapping adapters."""
    inner = getattr(resolved, "inner", None)
    if inner is not None and "Humans" not in type(inner).__name__:
        return type(inner).__name__
    return type(resolved).__name__


# ---------------------------------------------------------------------------
# Tiny logger (ASCII-only)
# ---------------------------------------------------------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    safe = str(msg).encode("ascii", errors="replace").decode("ascii")
    print("[%s] [arl_loop] %s" % (ts, safe), flush=True)


# ---------------------------------------------------------------------------
# Path / slug helpers
# ---------------------------------------------------------------------------
def _abs(rel_or_abs):
    if os.path.isabs(rel_or_abs):
        return rel_or_abs
    return os.path.join(SIM_ROOT, rel_or_abs)


def _rel_posix(path):
    return os.path.relpath(os.path.abspath(path), SIM_ROOT).replace(os.sep, "/")


def _path_to_module(apl_path):
    rel = os.path.relpath(os.path.abspath(apl_path), SIM_ROOT)
    if rel.lower().endswith(".py"):
        rel = rel[:-3]
    return rel.replace(os.sep, ".")


def _normalize_key(name):
    """Use apl/__init__._normalize_key so registry lookups resolve identically
    in this process and in subprocesses. Fallback mirrors its strict phase."""
    try:
        from apl import _normalize_key as nk
        return nk(name)
    except Exception:
        return name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")


def _matchup_slug(name):
    """Mirror matchup_jobs._slugify for reading vs_field directories."""
    try:
        from matchup_jobs import _slugify
        return _slugify(name)
    except Exception:
        return name.lower().replace(" ", "_").replace("'", "")


def _blocker(state, btype, **kw):
    entry = {"type": btype, "ts": _now_iso()}
    entry.update(kw)
    state.setdefault("blockers", []).append(entry)
    return entry


# ---------------------------------------------------------------------------
# Auto APL registry (write so sim.py / parallel_launcher subprocesses resolve)
# ---------------------------------------------------------------------------
def _registry_path():
    return os.path.join(SIM_ROOT, "data", "auto_apl_registry.json")


def _write_registry_entry(deck_name, apl_path, class_name, deck_file_rel):
    """Insert/replace an entry keyed by _normalize_key(deck_name) into
    data/auto_apl_registry.json. Atomic (temp + os.replace). Also clears the
    in-process apl._AUTO_REG_CACHE so a same-process get_apl() picks it up."""
    key = _normalize_key(deck_name)
    entry = {
        "module": _path_to_module(apl_path),
        "class": class_name,
        "deck_file": deck_file_rel,
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "source": "arl_loop",
    }
    reg_path = _registry_path()
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)

    # Prefer the repo's concurrency-safe RMW helper; fall back to inline atomic.
    wrote = False
    try:
        from engine.atomic_json import atomic_rmw_json
        atomic_rmw_json(reg_path, lambda reg: reg.update({key: entry}),
                        default_factory=dict)
        wrote = True
    except Exception:
        wrote = False
    if not wrote:
        reg = {}
        if os.path.exists(reg_path):
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg = json.load(f)
            except (OSError, ValueError):
                reg = {}
        reg[key] = entry
        tmp = reg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, reg_path)

    # Invalidate the lazy cache in apl/__init__ for this process.
    try:
        import apl as _aplpkg
        _aplpkg._AUTO_REG_CACHE = None
    except Exception:
        pass
    return key


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------
def _run(cmd, timeout):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run(cmd, cwd=SIM_ROOT, capture_output=True,
                              text=True, env=env, timeout=timeout)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as te:
        return 124, (te.stdout or ""), "TIMEOUT after %ss" % timeout


# ---------------------------------------------------------------------------
# Item helpers
# ---------------------------------------------------------------------------
def _derive_deck_name(item, fmt):
    """Human deck name used for registry key + parallel_launcher --deck."""
    if item.get("deck_name"):
        return item["deck_name"]
    df = item.get("deck_file")
    if df:
        stem = os.path.splitext(os.path.basename(df))[0]
        toks = stem.split("_")
        if toks and toks[-1].lower() == fmt.lower():
            toks = toks[:-1]
        return " ".join(t.capitalize() for t in toks) if toks else stem
    return item.get("id", "Unknown")


def _next_pending(state):
    for it in state.get("queue", []):
        if it.get("status") == "pending":
            return it
    return None


# ---------------------------------------------------------------------------
# Engine-fidelity gate helpers (Step 6.5 / Step 10)
# ---------------------------------------------------------------------------
def _real_deck_wr(deck_name, fmt):
    """Best-effort real-world win rate for `deck_name` from the meta DB.

    No single helper returns a deck's OVERALL real WR (get_real_matchup is
    per-opponent; get_all_matchups is a per-opponent dict). We therefore
    field-weight the real per-matchup WRs by real field share to produce the
    actual tournament-WR replication target the modelability backlog wants.

    Fully guarded: DB down, no matchup rows, or no field share -> None (the
    spec's 'else null'). NEVER a flat/unweighted mean (that would be a
    misleading number)."""
    try:
        from meta_bridge import get_all_matchups, get_real_field
        matchups = get_all_matchups(deck_name, fmt)  # {opp: win_pct}
        if not matchups:
            return None
        field = get_real_field(fmt, 30)  # {opp: share_pct}
        num = den = 0.0
        for opp, wp in matchups.items():
            try:
                share = float(field.get(opp, 0.0))
                w = float(wp)
            except (TypeError, ValueError):
                continue
            if share <= 0:
                continue
            num += w * share
            den += share
        if den <= 0:
            return None
        return round(num / den, 1)
    except Exception:  # noqa: BLE001 - replication target is best-effort
        return None


def _real_field_share(deck_name, fmt):
    """Best-effort real-world field share (%) for `deck_name` from the meta DB.

    This is the only deterministic component of the spec's
    'field-share x win-impact' priority that is actually available at enqueue
    time (win-impact has no deterministic source, and the spec forbids
    fabricating one). We therefore use field share alone as the backlog
    priority so the modelability backlog can be RANKED (fastest-payoff first)
    instead of carrying a permanently-null priority that can't be sorted.

    Matches the DB's archetype keys by normalized key so display-name drift
    (e.g. 'Jeskai Control' vs 'jeskai control') still resolves. Fully guarded:
    DB down / no match -> None (honest null, never a misleading number)."""
    try:
        from meta_bridge import get_real_field
        field = get_real_field(fmt, 30)  # {archetype: share_pct}
        if not isinstance(field, dict) or not field:
            return None
        want = _normalize_key(deck_name)
        for arch, share in field.items():
            if _normalize_key(arch) == want:
                try:
                    return round(float(share), 2)
                except (TypeError, ValueError):
                    return None
        return None
    except Exception:  # noqa: BLE001 - priority is best-effort
        return None


def _blocking_mechanic_pairs(profile):
    """Return [(mechanic, imperfection_id), ...] for a profile's blocking set.

    Inverts data/engine_fidelity_map.json (the single source of truth) to map
    each blocking imperfection back to its mechanic. GUARANTEES at least one
    pair when the deck is unmodelable -- even if the map is missing/incomplete
    so blocking_imperfections came back empty -- by falling back to the
    unmodelable-causing mechanic from the raw counts. This is what keeps
    'unmodelable' from ever being a silent dead-end (spec requirement)."""
    ef = profile.get("engine_fidelity", {}) if isinstance(profile, dict) else {}
    blocking = list(ef.get("blocking_imperfections", []) or [])
    try:
        fmap = arl_profile._load_fidelity_map()
    except Exception:  # noqa: BLE001
        fmap = {}
    inv = {imp: mech for mech, imp in fmap.items()} \
        if isinstance(fmap, dict) else {}

    pairs = [(inv.get(imp, imp), imp) for imp in blocking]
    if not pairs:
        # Unmodelable but no mapped imperfection -> recover the mechanic that
        # forced the verdict from the counts, so we ALWAYS enqueue real work.
        counts = ef.get("mechanic_counts", {}) or {}
        if counts.get("warp", 0) >= 1:
            pairs.append(("warp", fmap.get("warp")))
        elif counts.get("counterspell_on_stack", 0) >= 4:
            pairs.append(
                ("counterspell_on_stack", fmap.get("counterspell_on_stack")))
        else:
            pairs.append(("unmodeled_core", None))
    return pairs


# ---------------------------------------------------------------------------
# Batch generation (explore / optimize / refactor)
# ---------------------------------------------------------------------------
def _enqueue_explore(state, fmt):
    """Query real DB field shares; enqueue archetypes >0.5% not yet promoted."""
    try:
        from meta_bridge import get_real_field
    except Exception as e:
        log("explore: meta_bridge unavailable (%s)" % e)
        return 0
    try:
        field = get_real_field(fmt, 30)  # {archetype: share_pct}
    except Exception as e:
        log("explore: get_real_field failed (%s)" % e)
        return 0

    promoted_keys = {_normalize_key(p if isinstance(p, str) else p.get("id", ""))
                     for p in state.get("promoted", [])}
    queued_keys = {_normalize_key(it.get("deck_name") or it.get("id", ""))
                   for it in state.get("queue", [])}
    top_n_keys = {_normalize_key(a) for a in field.keys()}  # DB top-N set

    added = 0
    for arch, pct in sorted(field.items(), key=lambda x: -x[1]):
        if added >= 5:
            break
        try:
            share = float(pct)
        except (TypeError, ValueError):
            continue
        if share <= 0.5:
            continue
        k = _normalize_key(arch)
        if k in promoted_keys or k in queued_keys:
            continue
        # HITL flag if novel/off-meta (not in DB top-N). Sourcing from the DB
        # top-N means this is normally False; kept for steer-injected items.
        novel = k not in top_n_keys
        item = arl_state.new_queue_item(
            id=arl_generate_deck.slugify(arch),
            hitl=novel,
            notes="explore: %.1f%% meta share" % share,
        )
        item["deck_name"] = arch
        state.setdefault("queue", []).append(item)
        queued_keys.add(k)
        added += 1
        log("  explore enqueued: %s (%.1f%%)%s"
            % (arch, share, " [HITL]" if novel else ""))
    return added


def _parse_deck_file(deck_abspath):
    """Return (header_lines, main[(qty,name)], side[(qty,name)])."""
    header, main, side = [], [], []
    in_side = False
    with open(deck_abspath, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s:
                continue
            if s.startswith("//") or s.startswith("#"):
                if not main and not side:
                    header.append(line)
                continue
            if s.lower() in ("sideboard", "sb:"):
                in_side = True
                continue
            m = re.match(r"^(\d+)x?\s+(.+)$", s)
            if not m:
                continue
            qty, name = int(m.group(1)), m.group(2).strip()
            (side if in_side else main).append([qty, name])
    return header, main, side


def _apply_swap(main, side, out_name, in_name):
    """Return a new main list with one copy of out_name swapped for in_name."""
    new_main = [list(e) for e in main]
    # remove one copy of out_name
    for e in new_main:
        if e[1].lower() == out_name.lower():
            e[0] -= 1
            break
    new_main = [e for e in new_main if e[0] > 0]
    # add one copy of in_name
    for e in new_main:
        if e[1].lower() == in_name.lower():
            e[0] += 1
            break
    else:
        new_main.append([1, in_name])
    return new_main


def _write_variant_deck(base_abspath, base_id, fmt, idx, out_name, in_name):
    """Materialize a variant deck file under decks/auto/. Returns
    (variant_id, variant_abspath, deck_name) or None on no-op."""
    if not out_name or not in_name or out_name.lower() == in_name.lower():
        return None
    header, main, side = _parse_deck_file(base_abspath)
    if not main:
        return None
    new_main = _apply_swap(main, side, out_name, in_name)
    if new_main == main:
        return None
    variant_id = "%s_opt%d" % (base_id, idx)
    deck_dir = os.path.join(SIM_ROOT, "decks", "auto")
    os.makedirs(deck_dir, exist_ok=True)
    out_path = os.path.join(deck_dir, "%s_%s.txt" % (variant_id, fmt))
    deck_name = " ".join(t.capitalize() for t in variant_id.split("_"))
    lines = ["// audit:auto-generated:%s:%s"
             % (deck_name, datetime.now().strftime("%Y-%m-%d")),
             "// ARL optimize variant of %s: -%s +%s"
             % (base_id, out_name, in_name), ""]
    for qty, name in new_main:
        lines.append("%d %s" % (qty, name))
    if side:
        lines.append("")
        lines.append("Sideboard")
        for qty, name in side:
            lines.append("%d %s" % (qty, name))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return variant_id, out_path, deck_name


def _propose_swaps(base_deck_name, fmt, want):
    """Best-effort OUT/IN swaps. Try tuning_loop (needs Ollama); fall back to
    deterministic sideboard swaps so variants always DIFFER from the base."""
    swaps = []
    ollama_ok = _check_ollama_health() if _check_ollama_health else False
    if ollama_ok:
        try:
            from tuning_loop import run_tuning_loop
            res = run_tuning_loop(base_deck_name, fmt, iterations=1,
                                  n_per=100, max_field=8, dry_run=False)
            if isinstance(res, dict):
                for e in res.get("experiments", []):
                    if (e.get("out") and e.get("in")
                            and e.get("status") != "card_not_found"):
                        swaps.append({"out": e["out"], "in": e["in"]})
                    if len(swaps) >= want:
                        break
        except Exception as e:
            log("  optimize: tuning_loop unavailable (%s); using deterministic swaps" % e)
    return swaps


def _enqueue_optimize(state, fmt, base_id, base_deck_name, base_deck_file,
                      count):
    """Materialize up to `count` DISTINCT variant decks and enqueue them.
    Returns number enqueued. Never enqueues identical re-tests."""
    base_abspath = _abs(base_deck_file) if base_deck_file else None
    if not base_abspath or not os.path.isfile(base_abspath):
        log("  optimize: base deck file missing for %s" % base_id)
        return 0
    _, main, side = _parse_deck_file(base_abspath)
    swaps = _propose_swaps(base_deck_name, fmt, count)

    added = 0
    for k in range(count):
        if k < len(swaps):
            out_name, in_name = swaps[k]["out"], swaps[k]["in"]
        else:
            # Deterministic fallback: swap a mainboard slot for a sideboard
            # card (or the next distinct mainboard card if no sideboard).
            if side and main:
                out_name = main[k % len(main)][1]
                in_name = side[k % len(side)][1]
            elif len(main) > k + 1:
                out_name = main[k][1]
                in_name = main[k + 1][1]
            else:
                continue
        made = _write_variant_deck(base_abspath, base_id, fmt, k + 1,
                                   out_name, in_name)
        if not made:
            continue
        variant_id, variant_abspath, deck_name = made
        if any(it.get("id") == variant_id for it in state.get("queue", [])):
            continue
        item = arl_state.new_queue_item(
            id=variant_id,
            deck_file=_rel_posix(variant_abspath),
            notes="optimize variant of %s: -%s +%s" % (base_id, out_name, in_name),
        )
        item["deck_name"] = deck_name
        state.setdefault("queue", []).append(item)
        added += 1
        log("  optimize enqueued: %s (-%s +%s)" % (variant_id, out_name, in_name))
    return added


def _enqueue_optimize_top_promoted(state, fmt):
    """optimize mode: take top promoted, materialize variants."""
    promoted = state.get("promoted", [])
    if not promoted:
        log("optimize: no promoted decks to optimize")
        return 0
    top = promoted[-1]  # most recently promoted
    base_id = top if isinstance(top, str) else top.get("id")
    # locate the result record to recover deck_file + deck_name
    base_deck_file, base_deck_name = None, None
    for r in reversed(state.get("results", [])):
        if r.get("id") == base_id:
            base_deck_file = r.get("deck_file")
            base_deck_name = r.get("deck_name") or _derive_deck_name(
                {"deck_file": base_deck_file}, fmt)
            break
    if not base_deck_file:
        # fall back to conventional auto path
        base_deck_file = "decks/auto/%s_%s.txt" % (base_id, fmt)
        base_deck_name = " ".join(t.capitalize() for t in str(base_id).split("_"))
    return _enqueue_optimize(state, fmt, base_id, base_deck_name,
                             base_deck_file, count=5)


def _do_refactor(state):
    """refactor mode: no gauntlets. Write a proposal note and pause."""
    docs_dir = os.path.join(SIM_ROOT, "docs", "refactor_proposals")
    os.makedirs(docs_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = os.path.join(docs_dir, "refactor_%s.md" % stamp)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ARL refactor proposal (%s)\n\n" % _now_iso())
        f.write("Mode 'refactor' runs no gauntlets. Structural change proposals\n")
        f.write("should be authored here and reviewed by a human before any\n")
        f.write("engine/ or APL base-class changes. The loop is paused pending\n")
        f.write("that review.\n\n")
        f.write("- Current hypothesis: %s\n" % state.get("hypothesis", "(none)"))
        f.write("- Promoted decks: %s\n" % ", ".join(
            (p if isinstance(p, str) else p.get("id", "?"))
            for p in state.get("promoted", [])) or "(none)")
    state["status"] = "paused"
    _blocker(state, "refactor_review", note="proposal at %s" % _rel_posix(path))
    log("refactor: wrote %s; paused for review" % _rel_posix(path))
    return path


def _generate_batch(state, fmt):
    """Dispatch batch generation by mode. Returns number enqueued (refactor
    returns 0 and sets status=paused)."""
    mode = state.get("mode", "explore")
    if mode == "refactor":
        _do_refactor(state)
        return 0
    if mode == "optimize":
        return _enqueue_optimize_top_promoted(state, fmt)
    # default: explore
    return _enqueue_explore(state, fmt)


# ---------------------------------------------------------------------------
# Smoke + gauntlet
# ---------------------------------------------------------------------------
def _smoke(deck_rel, deck_name, smoke_n, timeout=900):
    """Run sim.py smoke. Returns (ok, win_rate_or_None, detail)."""
    cmd = [sys.executable, "sim.py", "--deck", deck_rel, "--apl", deck_name,
           "--n", str(smoke_n), "--no-chart", "--no-claude", "--seed", "42"]
    rc, out, err = _run(cmd, timeout)
    if any(mk in out for mk in HUMANS_FALLBACK_MARKERS):
        return False, None, "apl_unresolved (fell back to default APL)"
    if rc != 0:
        return False, None, "sim.py rc=%s: %s" % (rc, (err or out)[-200:])
    m = WIN_RATE_RE.search(out)
    if not m:
        return False, None, "no Win rate parsed: %s" % out[-200:]
    return True, float(m.group(1)), "win_rate=%.1f%%" % float(m.group(1))


def _gauntlet_once(deck_name, fmt, n, top_n, cores, seed, timeout=3600):
    """Run one parallel_launcher gauntlet. Returns (fwr_or_None, vs_field)."""
    cmd = [sys.executable, "parallel_launcher.py", "--deck", deck_name,
           "--format", fmt, "--n", str(n), "--top-n", str(top_n),
           "--cores", str(cores), "--seed", str(seed)]
    rc, out, err = _run(cmd, timeout)
    fwr = None
    m = FWR_RE.search(out)
    if m:
        fwr = float(m.group(1))
    vs_field = {}
    job_dir = os.path.join(SIM_ROOT, "data", "matchup_jobs",
                           _matchup_slug(deck_name))
    for jp in glob.glob(os.path.join(job_dir, "*.json")):
        try:
            with open(jp, "r", encoding="utf-8") as f:
                r = json.load(f)
            if not r.get("error"):
                vs_field[r.get("opp", os.path.basename(jp))] = r.get("match", 0)
        except (OSError, ValueError):
            continue
    if fwr is None:
        log("  gauntlet(seed=%s): no FWR parsed rc=%s %s"
            % (seed, rc, (err or out)[-160:]))
    return fwr, vs_field


# ---------------------------------------------------------------------------
# Steer directive interpretation (step 12)
# ---------------------------------------------------------------------------
def _directive_text(entry):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("directive") or entry.get("text") or ""
    return ""


def _apply_steer(state):
    """Drain steer_queue, interpret directives, log applied effects."""
    queue = state.get("steer_queue", [])
    if not queue:
        return
    state["steer_queue"] = []
    for entry in queue:
        directive = _directive_text(entry).strip()
        if not directive:
            continue
        norm = directive.lower()
        applied = None

        if norm == "pause":
            state["status"] = "paused"
            applied = "status=paused"
        elif norm == "resume":
            state["status"] = "running"
            applied = "status=running"
        elif re.search(r"set\s+promote_threshold\s+to\s+([0-9]*\.?[0-9]+)", norm):
            v = float(re.search(r"set\s+promote_threshold\s+to\s+([0-9]*\.?[0-9]+)",
                                norm).group(1))
            state["promote_threshold"] = v
            applied = "promote_threshold=%s" % v
        elif re.search(r"(raise|set)\s+gauntlet\s+cap\s+to\s+(\d+)", norm):
            v = int(re.search(r"(raise|set)\s+gauntlet\s+cap\s+to\s+(\d+)",
                              norm).group(2))
            state["gauntlet_cap"] = v
            applied = "gauntlet_cap=%d" % v
        elif re.search(r"\bmode\b", norm) or norm.startswith("switch to"):
            for mode in ("explore", "optimize", "refactor", "format_expand"):
                if mode in norm:
                    state["mode"] = mode
                    applied = "mode=%s" % mode
                    break
        elif norm.startswith("hypothesis:") or norm.startswith("hypothesis "):
            hyp = directive.split(":", 1)[1].strip() if ":" in directive \
                else directive[len("hypothesis"):].strip()
            state["hypothesis"] = hyp
            applied = "hypothesis set"
        elif re.search(r"flag\s+(\S+)\s+for\s+review", norm):
            tid = re.search(r"flag\s+(\S+)\s+for\s+review", directive,
                            re.IGNORECASE).group(1)
            for it in state.get("queue", []):
                if it.get("id") == tid:
                    it["hitl"] = True
            applied = "flagged %s for review" % tid
        elif re.search(r"requeue\s+(\S+)", norm):
            tid = re.search(r"requeue\s+(\S+)", directive, re.IGNORECASE).group(1)
            hit = False
            for it in state.get("queue", []):
                if it.get("id") == tid:
                    it["status"] = "pending"
                    hit = True
            applied = "requeued %s" % tid if hit else "requeue %s (not found)" % tid
        elif re.search(r"discard\s+(\S+)", norm):
            # Record a cross-session false positive so the fp-validator vetoes any
            # FUTURE promote of this deck. Completes the documented "discard <slug>"
            # steer (CLAUDE.md example) + populates data/arl_false_positives.json.
            slug = re.search(r"discard\s+(\S+)", directive, re.IGNORECASE).group(1).rstrip(",")
            if fp is not None:
                fp.record_false_positive({"slug": slug, "verdict": "promote"},
                                         reason=directive)
                applied = "recorded false positive: %s" % slug
            else:
                applied = "discard %s (fp-validator unavailable)" % slug

        log("steer applied: %r -> %s" % (directive, applied or "stored/none"))


# ---------------------------------------------------------------------------
# One iteration
# ---------------------------------------------------------------------------
def run_iteration(args):
    """Execute one ARL cycle. Returns True if the loop should continue, False
    to stop (paused / no-work / done-and-once)."""
    state = arl_state.load_state()

    # Step 1: paused -> clean exit.
    if state.get("status") == "paused":
        log("status=paused; nothing to do. Steer 'resume' to continue.")
        return False

    fmt = state.get("target_format") or args.target_format

    # Step 2/3: pick pending; if none, generate a batch.
    item = _next_pending(state)
    if item is None:
        log("queue empty; generating batch (mode=%s, fmt=%s)"
            % (state.get("mode", "explore"), fmt))
        n_added = _generate_batch(state, fmt)
        arl_state.write_state(state)
        if state.get("status") == "paused":
            return False  # refactor or steer-paused
        if n_added == 0:
            _blocker(state, "no_work",
                     note="batch generation produced no candidates "
                          "(mode=%s)" % state.get("mode", "explore"))
            state["status"] = "paused"
            arl_state.write_state(state)
            log("no candidates generated; paused.")
            return False
        item = _next_pending(state)
        if item is None:
            return False

    item_id = item.get("id", "?")
    deck_name = _derive_deck_name(item, fmt)
    item["deck_name"] = deck_name
    log("=== iteration %d: item %s (%s) ==="
        % (state.get("iteration", 0) + 1, item_id, deck_name))

    # Step 4: mark running, persist.
    item["status"] = "running"
    state["iteration"] = state.get("iteration", 0) + 1
    arl_state.write_state(state)

    # Step 5: ensure deck file.
    deck_rel = item.get("deck_file")
    if not deck_rel or not os.path.isfile(_abs(deck_rel)):
        try:
            path = arl_generate_deck.generate_deck(deck_name, fmt)
        except Exception as e:  # noqa: BLE001
            path = None
            log("deck gen raised: %s" % e)
        if not path:
            _blocker(state, "deck_gen_failed", id=item_id, deck=deck_name)
            item["status"] = "error"
            state["status"] = "paused"
            arl_state.write_state(state)
            log("deck generation failed for %s; paused." % deck_name)
            return False
        deck_rel = _rel_posix(path)
        item["deck_file"] = deck_rel
    deck_abspath = _abs(deck_rel)

    # Step 6.5: CAPABILITY PROFILE + ENGINE-FIDELITY GATE (deterministic).
    # Built BEFORE the APL is ensured/smoked. engine_fidelity is computed with
    # NO LLM so the gate is reliable even with Ollama down. FAIL-SAFE design:
    # conf is initialized to "low" and only upgraded on a clean build, so any
    # build failure -- or a card DB that didn't load -- can never read as a
    # trustworthy "high" and silently promote off an FWR we can't represent.
    conf = "low"
    blocking = []
    profile = None
    try:
        profile = arl_profile.build_profile(deck_abspath, fmt)
        ef = profile.get("engine_fidelity", {}) or {}
        conf = arl_state._coerce_quality(ef.get("confidence"), default="low")
        blocking = list(ef.get("blocking_imperfections", []) or [])
        item["profile_file"] = _rel_posix(
            os.path.join(arl_profile.PROFILES_DIR, profile["slug"] + ".json"))
        # DB-down guard: if the card DB didn't load, every mainboard card lands
        # in unresolved_cards and confidence reads a false "high". If most of
        # the mainboard is unresolved, downgrade high->low (same fail-safe
        # direction) so a DB-down run can't promote off FWR.
        unresolved = ef.get("unresolved_cards", []) or []
        try:
            _, _main_dbg, _ = _parse_deck_file(deck_abspath)
            main_distinct = len(_main_dbg)
        except Exception:  # noqa: BLE001
            main_distinct = 0
        if (conf == "high" and main_distinct
                and len(unresolved) >= (main_distinct + 1) // 2):
            conf = "low"
            log("profile: %d/%d mainboard names unresolved (card DB likely "
                "unavailable); downgrading high->low (fail-safe)."
                % (len(unresolved), main_distinct))
        log("profile: %s confidence=%s blocking=%s"
            % (item.get("profile_file"), conf, ", ".join(blocking) or "(none)"))
    except Exception as e:  # noqa: BLE001 - gate fails SAFE to low, never high
        conf = "low"
        blocking = []
        log("profile build FAILED for %s (%s); gating as low (fail-safe)."
            % (deck_name, e))

    # Step 6.5 gate -- UNMODELABLE: the deck's core depends on an unmodeled
    # mechanic. Do NOT smoke or gauntlet (no trustworthy FWR exists). Enqueue a
    # real modelability work item (with a replication target) for EACH blocking
    # mechanic -- never a silent dead-end -- record an 'unmodelable' result, set
    # the item done, and CONTINUE to the next item. The whole loop is NOT paused
    # (only --once stops after this iteration; a steered 'pause' is still honored
    # below). hitl is left as-is: an auto-enqueued backlog item does not require
    # human input, so we do not force a review pause here.
    if conf == "unmodelable":
        pairs = _blocking_mechanic_pairs(profile) if profile \
            else [("unmodeled_core", None)]
        real_wr = _real_deck_wr(deck_name, fmt)
        # Deterministic, honest priority: real-world field share (%). The spec's
        # full priority is field-share x win-impact, but win-impact has no
        # deterministic source here (and fabricating one is forbidden). Field
        # share alone still lets the backlog be ranked fastest-payoff first;
        # None only when the DB has no share for this deck.
        priority = _real_field_share(deck_name, fmt)
        slug = profile.get("slug") if profile else item_id
        for mech, imp in pairs:
            bl = arl_state.new_backlog_item(
                slug=slug, archetype=deck_name, mechanic=mech,
                blocking_imperfection=imp, priority=priority,
                real_wr=real_wr, known_line="")
            arl_state.append_backlog(bl)
            log("  modelability backlog += %s (mechanic=%s, imp=%s, real_wr=%s)"
                % (deck_name, mech, imp, real_wr))
        result = arl_state.new_result(
            id=item_id, deck_file=item.get("deck_file"), fwr=None,
            vs_field={}, hypothesis=state.get("hypothesis", ""),
            verdict="unmodelable", hitl=bool(item.get("hitl")),
            notes=("unmodelable: " + (", ".join(blocking)
                   or "core mechanic not modeled")),
            data_quality="unmodelable", confidence="unmodelable",
            blocking_imperfections=blocking)
        result["deck_name"] = deck_name
        if item.get("profile_file"):
            result["profile_file"] = item.get("profile_file")
        state.setdefault("results", []).append(result)
        item["fwr"] = None
        item["status"] = "done"
        arl_state.write_state(state)
        log("UNMODELABLE: %s -> %d backlog item(s); skipped smoke/gauntlet; "
            "continuing (not promoting, not pausing)." % (deck_name, len(pairs)))
        # Still drain steer so a user 'pause' directive is honored.
        _apply_steer(state)
        arl_state.write_state(state)
        if state.get("status") == "paused":
            log("steer paused the loop.")
            return False
        return True

    # Step 6: ensure APL. Prefer an EXISTING canonical (non-fallback) APL; only
    # generate a new one when the archetype has no real APL yet. Never clobber a
    # hand-written canonical APL (spec: the loop does not delete/modify existing
    # APLs). This is the fix for registered archetypes (e.g. Boros Energy) that
    # already ship a MatchAPL -- previously the loop generated a redundant APL and
    # the resolution guard then failed on the class-name mismatch.
    using_existing = False
    class_name = None
    apl_notes = None
    try:
        from apl import get_match_apl as _gma_pre
        _resolved_pre = _gma_pre(deck_name)
    except Exception:  # noqa: BLE001
        _resolved_pre = None
    if _resolved_pre is not None and not _is_fallback_apl(_resolved_pre):
        class_name = _real_apl_class(_resolved_pre)
        apl_notes = "existing-canonical"
        using_existing = True
        log("APL: using existing canonical %s for %s (no generation)"
            % (class_name, deck_name))
    else:
        try:
            apl_path, class_name, apl_notes = arl_generate_apl.generate_apl_file(
                deck_abspath, use_claude=args.use_claude, format_name=fmt)
        except Exception as e:  # noqa: BLE001
            _blocker(state, "apl_gen_failed", id=item_id, error=str(e)[:200])
            item["status"] = "error"
            arl_state.write_state(state)
            log("APL generation failed for %s: %s" % (deck_name, e))
            return True
        item["apl_file"] = _rel_posix(apl_path)
        log("APL: %s (class=%s, notes=%s)"
            % (item["apl_file"], class_name, apl_notes))
        # Register (B2) so subprocesses + in-process guard resolve our APL.
        _write_registry_entry(deck_name, apl_path, class_name, deck_rel)

    # Step 7: SMOKE (sim.py). Up to 2 auto-fix (regen) attempts.
    ok, wr, detail = _smoke(deck_rel, deck_name, args.smoke_n)
    attempts = 0
    # Only auto-fix-by-regenerate for generated APLs; never regenerate over a
    # canonical APL (using_existing) -- if a canonical smoke fails that is a real
    # signal, not something to paper over by clobbering the hand-written APL.
    while not ok and attempts < 2 and not using_existing:
        attempts += 1
        log("smoke failed (%s); auto-fix attempt %d/2 (regenerate APL)"
            % (detail, attempts))
        try:
            apl_path, class_name, apl_notes = arl_generate_apl.generate_apl_file(
                deck_abspath, use_claude=args.use_claude, format_name=fmt,
                force=True)
            item["apl_file"] = _rel_posix(apl_path)
            _write_registry_entry(deck_name, apl_path, class_name, deck_rel)
        except Exception as e:  # noqa: BLE001
            log("  regen raised: %s" % e)
        ok, wr, detail = _smoke(deck_rel, deck_name, args.smoke_n)
    if not ok:
        _blocker(state, "smoke_fail", id=item_id, detail=detail)
        item["status"] = "error"
        arl_state.write_state(state)
        log("smoke gate failed for %s after %d auto-fix attempts; continuing."
            % (deck_name, attempts))
        return True
    log("smoke OK: %s" % detail)

    # Step 8: RESOLUTION GUARD (post-register) using class_name discriminator.
    try:
        from apl import get_match_apl
        resolved = get_match_apl(deck_name)
    except Exception as e:  # noqa: BLE001
        resolved = None
        log("resolution guard import/call raised: %s" % e)
    resolved_cls = type(resolved).__name__ if resolved is not None else None
    inner_cls = type(getattr(resolved, "inner", None)).__name__ \
        if resolved is not None else None
    # Pass if the slug resolves to ANY real archetype APL (canonical or freshly
    # generated). Fail only on the Humans/default fallback -- that is the actual
    # "garbage FWR" risk (B2). Do NOT require equality with the generated class:
    # a registered archetype legitimately resolves to its own canonical MatchAPL.
    if _is_fallback_apl(resolved):
        _blocker(state, "apl_unresolved", id=item_id,
                 resolved=resolved_cls, inner=inner_cls, expected=class_name)
        item["status"] = "error"
        arl_state.write_state(state)
        log("resolution guard FAILED for %s (resolved=%s inner=%s -> Humans/"
            "fallback); skipping gauntlet."
            % (deck_name, resolved_cls, inner_cls))
        return True
    log("resolution guard OK (resolved=%s inner=%s)" % (resolved_cls, inner_cls))

    # Step 9: GAUNTLET x2 (seed 42 then 43). Hard cap 200 unless steer raised.
    cap = int(state.get("gauntlet_cap", DEFAULT_GAUNTLET_CAP))
    n = min(args.gauntlet_n, cap)
    log("gauntlet n=%d (requested %d, cap %d), top-n=%d, cores=%d"
        % (n, args.gauntlet_n, cap, args.top_n, args.cores))
    fwr1, vs1 = _gauntlet_once(deck_name, fmt, n, args.top_n, args.cores, 42)
    fwr2, vs2 = _gauntlet_once(deck_name, fmt, n, args.top_n, args.cores, 43)

    if fwr1 is None and fwr2 is None:
        _blocker(state, "gauntlet_fail", id=item_id, note="no FWR parsed")
        item["status"] = "error"
        arl_state.write_state(state)
        log("gauntlet failed for %s (no FWR); continuing." % deck_name)
        return True

    fwrs = [x for x in (fwr1, fwr2) if x is not None]
    avg_fwr = round(sum(fwrs) / len(fwrs), 1)
    variance = abs(fwr1 - fwr2) if (fwr1 is not None and fwr2 is not None) else 0.0
    vs_field = vs1 or vs2
    log("gauntlet FWR: run1=%s run2=%s avg=%.1f variance=%.1fpp"
        % (fwr1, fwr2, avg_fwr, variance))

    # Step 10: EVALUATE -- gated by the profile's engine-fidelity confidence.
    #   high   : normal promote/mutate/discard at promote_threshold.
    #   medium : may promote, but the result is stamped data_quality="medium"
    #            (downstream must not auto-feed it into playbooks unvalidated).
    #   low    : NEVER promote regardless of FWR -> verdict="low_confidence";
    #            the FWR is still recorded for reference, with the blocking
    #            imperfections, so the data is honest rather than discarded.
    # ('unmodelable' was handled in step 6.5 and never reaches here.)
    threshold = float(state.get("promote_threshold", DEFAULT_PROMOTE_THRESHOLD))
    is_variant = str(item.get("notes", "")).startswith("optimize variant")
    result_data_quality = conf  # high|medium|low mirrors the gate verdict

    if conf == "low":
        verdict = "low_confidence"
        log("verdict=low_confidence: FWR=%.1f%% recorded for reference, but "
            "confidence=low (blocking: %s); NOT promoting %s."
            % (avg_fwr, ", ".join(blocking) or "(none)", deck_name))
    elif variance > 8.0:
        _blocker(state, "fwr_variance", id=item_id, run1=fwr1, run2=fwr2,
                 variance=round(variance, 1))
        verdict = "discard"
        log("FWR variance %.1fpp > 8pp; NOT promoting %s." % (variance, deck_name))
    elif avg_fwr > threshold:
        # FP-validator veto: reject a promote whose signature is a known false
        # positive (recorded via a prior "discard <slug>" steer) or implausible.
        # Cross-session memory in data/arl_false_positives.json.
        _ok, _fp_reason = (True, "")
        if fp is not None:
            _ok, _fp_reason = fp.validate_promote(
                {"slug": item_id, "verdict": "promote", "fwr": avg_fwr, "confidence": conf})
        if not _ok:
            verdict = "discard"
            log("verdict=discard: promote vetoed by fp-validator (%s) for %s"
                % (_fp_reason, deck_name))
        else:
            verdict = "promote"
            if item_id not in [p if isinstance(p, str) else p.get("id")
                               for p in state.get("promoted", [])]:
                state.setdefault("promoted", []).append(item_id)
            log("verdict=promote (%.1f%% > %.1f, confidence=%s)"
                % (avg_fwr, threshold, conf))
    elif avg_fwr >= MUTATE_LOW:
        verdict = "mutate"
        if is_variant:
            log("verdict=mutate but item is already a variant; not re-mutating.")
        else:
            added = _enqueue_optimize(state, fmt, item_id, deck_name,
                                      item.get("deck_file"), count=4)
            log("verdict=mutate (%.1f%%); enqueued %d variants" % (avg_fwr, added))
    else:
        verdict = "discard"
        log("verdict=discard (%.1f%% < %.1f)" % (avg_fwr, MUTATE_LOW))

    result = arl_state.new_result(
        id=item_id, deck_file=item.get("deck_file"), fwr=avg_fwr,
        vs_field=vs_field, hypothesis=state.get("hypothesis", ""),
        verdict=verdict, hitl=bool(item.get("hitl")),
        notes=item.get("notes", ""),
        data_quality=result_data_quality, confidence=conf,
        blocking_imperfections=blocking)
    result["deck_name"] = deck_name
    result["fwr_runs"] = [fwr1, fwr2]
    if item.get("profile_file"):
        result["profile_file"] = item.get("profile_file")
    state.setdefault("results", []).append(result)
    item["fwr"] = avg_fwr
    item["status"] = "done"
    arl_state.write_state(state)

    # Step 11: HITL gate.
    if item.get("hitl"):
        state["status"] = "paused"
        _blocker(state, "hitl_review", id=item_id, fwr=avg_fwr,
                 suggested="review candidate, then steer resume")
        arl_state.write_state(state)
        log("HITL item %s finished (FWR=%.1f); paused for review." % (item_id, avg_fwr))
        return False

    # Step 12: apply steer directives.
    _apply_steer(state)
    arl_state.write_state(state)
    if state.get("status") == "paused":
        log("steer paused the loop.")
        return False

    return True


# ---------------------------------------------------------------------------
# Crash recovery + main loop
# ---------------------------------------------------------------------------
def _recover_running(state):
    """Reset any item stranded at status=='running' (a prior Ctrl-C between
    step 4 and step 10) back to 'pending' so it is reprocessed."""
    n = 0
    for it in state.get("queue", []):
        if it.get("status") == "running":
            it["status"] = "pending"
            n += 1
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Autonomous Research Loop (ARL) runner for mtg-sim.")
    parser.add_argument("--target-format", default="modern")
    parser.add_argument("--smoke-n", type=int, default=100)
    parser.add_argument("--gauntlet-n", type=int, default=200,
                        help="Games per matchup (hard cap 200 unless a steer "
                             "directive raises gauntlet_cap).")
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--once", action="store_true",
                        help="Run exactly one iteration then stop.")
    parser.add_argument("--max-iter", type=int, default=0,
                        help="Max iterations (0 = unbounded until paused/no-work).")
    parser.add_argument("--use-claude", action="store_true",
                        help="Prefer Claude APL generation (default off -> Gemma/local).")
    parser.add_argument("--cores", type=int, default=2)
    args = parser.parse_args(argv)

    # Startup: seed target_format + crash recovery.
    state = arl_state.load_state()
    if not state.get("target_format"):
        state["target_format"] = args.target_format
    recovered = _recover_running(state)
    if recovered:
        log("crash recovery: reset %d stranded 'running' item(s) to pending"
            % recovered)
    arl_state.write_state(state)

    # Loop controller (use our own stop conditions; keep budgets effectively
    # unbounded so a long autonomous run isn't killed mid-flight).
    ctrl = None
    if _LoopController is not None:
        max_steps = args.max_iter if args.max_iter > 0 else 10 ** 9
        ctrl = _LoopController(max_steps=max_steps, time_budget=10 ** 9,
                              stall_limit=10 ** 9)

    iters = 0
    rc = 0
    try:
        while True:
            if ctrl is not None and not ctrl.can_continue():
                log("loop controller stop: %s" % ctrl.stop_reason)
                break
            cont = run_iteration(args)
            iters += 1
            if ctrl is not None:
                ctrl.step(progress=True)
            if args.once:
                break
            if not cont:
                break
            if args.max_iter and iters >= args.max_iter:
                log("reached --max-iter=%d" % args.max_iter)
                break
    except KeyboardInterrupt:
        # Clean pause: never corrupt loop_state.json mid-write.
        try:
            st = arl_state.load_state()
            st["status"] = "paused"
            _recover_running(st)
            _blocker(st, "interrupted", note="KeyboardInterrupt; paused cleanly")
            arl_state.write_state(st)
            log("KeyboardInterrupt: status set to paused; state written cleanly.")
        except Exception as e:  # noqa: BLE001
            log("KeyboardInterrupt during shutdown write: %s" % e)
            rc = 1
    except Exception as e:  # noqa: BLE001
        log("FATAL: %s" % e)
        import traceback
        traceback.print_exc()
        rc = 1
    finally:
        log("loop exit after %d iteration(s)." % iters)

    return rc


if __name__ == "__main__":
    sys.exit(main())
