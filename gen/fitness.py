"""
gen/fitness.py -- Score a generated deck: "good or ass?"

Two passes combined into one fitness scalar:
  goldfish  -- run_simulation() on the auto-generated APL: win rate, kill speed,
               consistency (engine/runner.py)
  field     -- race our kill-turn distribution vs measured Modern opponent clocks
               (sim_bridge.ARCHETYPE_CLOCKS via race_win_pct). Modern has no
               two-player match APLs, so this is an explicit RACE PROXY, weighted
               below the dominant term.

A fidelity gate caps the verdict: if the APL fell back to GenericAPL, or the
deck has non-simulatable load-bearing cards, the engine cannot pilot it
faithfully, so it can never be crowned "strong".

evaluate() takes an injectable `sim_runner` and `apl_provider` so the scalar /
verdict / field math is unit-testable without the oracle DB or a Claude call.
"""

import statistics
from dataclasses import dataclass, field, asdict

from sim_bridge import ARCHETYPE_CLOCKS, race_win_pct

# Curated Modern field: (clock key in ARCHETYPE_CLOCKS, metagame share).
# Shares are an approximation of a recent Modern field; rebuildable from
# mtg_meta.db later. Keys chosen from the *measured* clocks where possible.
_FIELD_RAW = {
    "Boros Energy":    ("borosenergy", 0.20),
    "Amulet Titan":    ("amulettitan", 0.10),
    "Golgari Yawgmoth":("golgariyawgmoth", 0.10),
    "Eldrazi Tron":    ("eldrazitron", 0.10),
    "Living End":      ("livingend", 0.08),
    "Murktide":        ("murktide", 0.10),
    "Tron":            ("tron", 0.08),
    "Domain Zoo":      ("domainzoo", 0.08),
    "Dimir Midrange":  ("dimirmidrange", 0.08),
    "Izzet Prowess":   ("izzetprowess", 0.08),
}


def modern_field():
    """Resolve {label: (clock_dict, share)} from ARCHETYPE_CLOCKS, normalized."""
    out, total = {}, 0.0
    for label, (key, share) in _FIELD_RAW.items():
        clock = ARCHETYPE_CLOCKS.get(key)
        if clock:
            out[label] = [clock, share]
            total += share
    if total:
        for label in out:
            out[label][1] /= total
    return {k: (v[0], v[1]) for k, v in out.items()}


MODERN_FIELD = modern_field()

# Verdict thresholds on field win-rate (race proxy, percent).
VERDICT_THRESHOLDS = [(58.0, "strong"), (52.0, "playable"), (46.0, "weak"), (0.0, "ass")]
# Fidelity gate: low-fidelity decks cannot rank above this verdict.
FIDELITY_CAP = "playable"
_VERDICT_ORDER = ["ass", "weak", "playable", "strong"]


@dataclass
class FitnessReport:
    deck_id: str
    fitness: float
    verdict: str
    fidelity: str
    field_wr: float
    goldfish: dict = field(default_factory=dict)
    field: dict = field(default_factory=dict)
    apl_source: str = ""

    def to_dict(self):
        return asdict(self)


def field_winrate(our_dist: dict, field_clocks=None, n: int = 20000):
    """Field-weighted race win % of our kill distribution vs Modern opponents."""
    field_clocks = field_clocks or MODERN_FIELD
    if not our_dist:
        return 0.0, {}
    per = {}
    overall = 0.0
    for label, (clock, share) in field_clocks.items():
        wp = race_win_pct(our_dist, clock, n=n)
        per[label] = wp
        overall += wp * share
    return round(overall, 1), per


def speed_score(dist: dict) -> float:
    """0-100: faster, more reliable kills score higher (win-by-turn-6 proxy)."""
    if not dist:
        return 0.0
    by_t6 = sum(p for t, p in dist.items() if t <= 6)
    by_t8 = sum(p for t, p in dist.items() if t <= 8)
    return round(min(100.0, 0.7 * by_t6 + 0.3 * by_t8), 1)


def consistency_score(res) -> float:
    """0-100: reward low mulligan rate and a tight kill band."""
    mull = res.mull_rate() if hasattr(res, "mull_rate") else 0.0
    kills = getattr(res, "kill_turns", []) or []
    spread = statistics.pstdev(kills) if len(kills) > 1 else 3.0
    tightness = max(0.0, 100.0 - spread * 18.0)
    return round(max(0.0, 0.5 * (100.0 - mull) + 0.5 * tightness), 1)


def compute_fitness(field_wr, win_rate_pct, speed, consistency) -> float:
    return round(0.45 * field_wr + 0.25 * win_rate_pct
                 + 0.20 * speed + 0.10 * consistency, 2)


def verdict_for(field_wr: float, fidelity: str) -> str:
    v = "ass"
    for threshold, label in VERDICT_THRESHOLDS:
        if field_wr >= threshold:
            v = label
            break
    if fidelity == "low" and _VERDICT_ORDER.index(v) > _VERDICT_ORDER.index(FIDELITY_CAP):
        v = FIDELITY_CAP
    return v


def _default_sim_runner(cand, n, fmt, packages, apl):
    """Real path: render -> load Card objects -> run_simulation. Needs the oracle DB."""
    from gen.deck_writer import render_deck_text
    from data.deck import load_deck_from_text
    from engine.runner import run_simulation
    text = render_deck_text(cand, fmt=fmt)
    mainboard, _ = load_deck_from_text(text)
    return run_simulation(apl, mainboard, n=n, mixed_play_draw=True)


def evaluate(cand, *, packages=None, fmt="modern", n_goldfish=5000,
             sim_runner=None, apl_provider=None, deck_id=None):
    """
    Score a DeckCandidate -> FitnessReport.

    apl_provider(cand) -> (apl, info) defaults to gen.apl_cache.get_apl_for_candidate.
    sim_runner(cand, n, fmt, packages, apl) -> SimulationResults defaults to the
    real goldfish path. Both are injectable for offline tests.
    """
    deck_id = deck_id or cand.name

    if apl_provider is None:
        from gen.apl_cache import get_apl_for_candidate
        apl, info = get_apl_for_candidate(cand, packages=packages, fmt=fmt)
    else:
        apl, info = apl_provider(cand)
    fidelity = info.get("fidelity", cand.metadata.get("fidelity", "high"))

    runner = sim_runner or _default_sim_runner
    res = runner(cand, n_goldfish, fmt, packages, apl)

    dist = res.kill_turn_distribution()
    field_wr, per_opp = field_winrate(dist)
    win_pct = res.win_rate() * 100
    speed = speed_score(dist)
    cons = consistency_score(res)
    fitness = compute_fitness(field_wr, win_pct, speed, cons)
    verdict = verdict_for(field_wr, fidelity)

    return FitnessReport(
        deck_id=deck_id,
        fitness=fitness,
        verdict=verdict,
        fidelity=fidelity,
        field_wr=field_wr,
        goldfish={
            "win_rate": round(win_pct, 1),
            "avg_kill_turn": res.avg_kill_turn(),
            "median_kill_turn": res.median_kill_turn(),
            "speed": speed,
            "consistency": cons,
            "kill_distribution": dist,
        },
        field=per_opp,
        apl_source=info.get("source", ""),
    )
