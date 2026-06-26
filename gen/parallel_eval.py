"""
gen/parallel_eval.py -- Fan-out evaluation of candidates.

The expensive part of evaluation is the goldfish sim; APL generation must stay
serialized (shared on-disk cache, file contention). So the throughput model is:
  1. resolve+cache every candidate's APL serially (cheap after the first of a
     package set; see gen/apl_cache.py reuse tiers), then
  2. run the goldfish sims across a process pool.

For offline tests and small runs an injected `eval_fn` is mapped serially. True
multiprocessing requires a module-level (picklable) eval_fn; closures fall back
to serial automatically.
"""

import os
from concurrent.futures import ProcessPoolExecutor


def _is_picklable_callable(fn):
    return getattr(fn, "__module__", None) is not None and hasattr(fn, "__qualname__") \
        and "<locals>" not in getattr(fn, "__qualname__", "<locals>")


def evaluate_population(cands, eval_fn, max_workers=None):
    """
    Evaluate candidates with eval_fn(cand) -> report.

    Runs serially when max_workers in (None,0,1) or eval_fn is a closure;
    otherwise distributes across a ProcessPoolExecutor. Returns a list of
    reports aligned with `cands` (None for any that error).
    """
    if not cands:
        return []
    workers = max_workers or 1
    if workers <= 1 or not _is_picklable_callable(eval_fn):
        out = []
        for c in cands:
            try:
                out.append(eval_fn(c))
            except Exception as e:
                print(f"[parallel_eval] {getattr(c, 'name', '?')} failed: {e}")
                out.append(None)
        return out

    workers = min(workers, os.cpu_count() or 1, len(cands))
    results = [None] * len(cands)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(eval_fn, c): i for i, c in enumerate(cands)}
        for fut, i in futs.items():
            try:
                results[i] = fut.result()
            except Exception as e:
                print(f"[parallel_eval] candidate {i} failed: {e}")
    return results
