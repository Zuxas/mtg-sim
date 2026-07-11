# Affinity sim-internal decomposition (bob-20260710-182604-17f1, G2/G3)

**Decision question:** on the recommended Low Curve build, is Affinity actually a liability?
**Opponent resolution (verified):** `affinity` == `izzetaffinity` -> `decks/izzet_affinity_modern.txt` /
`IzzetAffinityMatchAPL` (apl/__init__.py:120,361). Field config "Affinity" 9.0% is this deck. No label mismatch.

## Boros-vs-Affinity cells, metric-pinned (g1 = game-1 WR; match = bo3 match WR)

| our build | method | g1 | match | n | source |
|---|---|---|---|---|---|
| base `boros_energy` (memo's 42.7) | bo3 | 42.7 | 38.8 | 100k | cached |
| **`borosenergylowcurve` (RECOMMENDED)** | **bo3** | **48.0** | **46.7** | **3000** | **THIS RUN (seed 42, 60s)** |
| `borosenergy` (match-APL alias) | bo3 | 60.0 | 63.5 | 200 | cached |
| `fable` | bo3 | 41.0 | 33.5 | 200 | cached |
| `jitte` | bo3 | 52.0 | 49.0 | 200 | cached |
| `variant` | sim | 85.4 | 96.6 | 100k | cached (DIFFERENT method 'sim') |
| (build unspec.) | run_match MATCH | -- | 63.0 | 300 | docs/wpb4-documented-shifts:8 POST-WP-B4 (old ~76 was PRE-WP-B4/stale) |
| **live paper** | -- | **72.7** | -- | **23** | live anchor (== WP-F#2 paper 0.727/23; Wilson [52,87]; match col dropped as double-counted) |

## Decomposition of the 42.7 -> 72.7 gap  (fable-refute corrected)
- **BUILD** (base -> lowcurve, both bo3 _run_fair, same opp/seed/metric): **+5.3pp** (42.7 -> 48.0). SMALL.
  (Clean: base 100k cache written post-WP-B4, same engine as this run; n=3000 CI +/-1.8pp.)
- **METHOD** (bo3 _run_fair vs run_match): **~15-25pp** (lowcurve bo3 46.7 match / 48.0 g1 vs current-engine
  run_match MATCH 63.0). The larger term, but magnitude is SOFT (metric/build-mixed; run_match build
  unspecified in the shift doc). The old ~76 (=> ~28pp) was PRE-WP-B4 and is NOT used.
- The bo3 _run_fair path (~42-48) is the LOW OUTLIER; run_match (63) and live (72.7) both put Boros
  FAVORED (>50%) but differ ~10pp -- "both favor Boros", not "agree".

## Verdict  (fable-refute: NOT-REFUTED after this amendment; sim reproduced 48.0 bit-identical)
1. **Build effect is small (~5pp).** Switching to Low Curve does NOT resolve the memo's Affinity
   "liability" within the bo3 field-read (48.0 is still ~even).
2. **The larger term is METHOD (~15-25pp):** the bo3 `_run_fair` gauntlet path rates Boros lower vs
   Affinity than the run_match harness (63.0, current-engine) and live paper (72.7, n=23). Both non-bo3
   sources put Boros FAVORED (>50%). Magnitude is soft; direction is robust.
3. **So the memo's "Affinity = biggest liability" is probably a bo3-method artifact**, not a real
   matchup fact and not a build issue. The flag's asserted "truth ~44" is contradicted by live 72.7
   (Wilson [52,87] excludes 42.7/48.0) -> the bo3 cell is more likely DEFLATED than INFLATED.
4. **Disposition (constraint-respecting):** NO direction flip on n=23 (tiny). Update the flag NOTE with
   this decomposition; mark the cell's INFLATED-vs-truth direction CONTESTED/likely-inverted. Grow n +
   re-verify run_match before adopting. Memo headline SOFTENS: Affinity is the biggest UNCERTAINTY, not
   a confident liability; the limited real data leans Boros-FAVORED.

## Caveats
- run_match ~76 is documented (arc#3), not re-run here (user approved ONE serialized run). The
  method-effect magnitude is therefore suggestive; the BUILD-effect-is-small + bo3-disagrees-with-live
  conclusions are solid from this run + cache.
- Metric pinned to g1 for the build comparison (base 42.7 vs lowcurve 48.0). match tells the same story
  (38.8 vs 46.7).
- n=23 live paper = the SAME 23 matches as the WP-F#2 spec's paper cell (one data point, not two).
