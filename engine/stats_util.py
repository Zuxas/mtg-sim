"""engine/stats_util.py -- Wilson score confidence bands for reported win rates.

Reporting-layer ONLY: these helpers make every printed/serialized win rate
carry an honest 95% band so sim noise is not over-read as a real edge
(a 68% FWR at N=200 is really 68% +/- ~6.5pp). They must NOT feed back
into decision logic (promotion gates, fitness, APL choices).

Pattern follows mtg-meta-analyzer/analysis/wilson.py, per
harness/knowledge/tech/ext-eval-ml-calibration-2026-06-26.md section 1C
("FWR confidence bands").
"""
from __future__ import annotations

import math

# Two-sided z at 95% confidence
Z_95 = 1.959963984540054


def wilson_bounds(wins: float, total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Returns (lower, upper) on [0.0, 1.0]. For total<=0 returns (0.0, 1.0)
    -- maximally uninformative band, the right answer when we have no data.
    ``wins`` may be fractional (pseudo-wins from a weighted rate).
    """
    if total <= 0:
        return (0.0, 1.0)
    n = float(total)
    p = min(max(wins / n, 0.0), 1.0)
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2.0 * n)) / denom
    half = (z * math.sqrt((p * (1.0 - p) / n) + (z * z) / (4.0 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def wilson_bounds_pct(win_pct: float, total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson bounds for a win rate already expressed as a 0-100 percentage.

    For aggregated rates (e.g. field-weighted FWR) where only the point pct
    and an effective sample size are known at print/serialize time.
    Returns (lo_pct, hi_pct) on [0.0, 100.0].
    """
    lo, hi = wilson_bounds(win_pct / 100.0 * max(total, 0), total, z=z)
    return (lo * 100.0, hi * 100.0)


def fmt_pct_band(win_pct: float, total: int, z: float = Z_95) -> str:
    """Render a win rate with its 95% band: '54.3% [44.3–63.4]'.

    Display helper -- append-safe after existing '<pct>%' output so log
    parsers keyed on the point value (e.g. arl_loop.FWR_RE) still match.
    """
    lo, hi = wilson_bounds_pct(win_pct, total, z=z)
    return f"{win_pct:.1f}% [{lo:.1f}–{hi:.1f}]"
