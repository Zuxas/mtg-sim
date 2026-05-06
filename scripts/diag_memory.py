"""Measure per-game RAM growth of run_match.

Runs N games of one matchup sequentially in this process. Reports RSS
after each batch of 5 games so we can see whether memory grows linearly
(true leak) or plateaus (Python allocator stickiness, harmless).
"""
import sys, os, time, gc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def rss_mb():
    """Return current process RSS in MB."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback: use resource on Unix, ctypes on Windows
        if sys.platform == "win32":
            import ctypes, ctypes.wintypes
            class PMC(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.wintypes.DWORD),
                    ("PageFaultCount", ctypes.wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            counters = PMC()
            counters.cb = ctypes.sizeof(PMC)
            ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(counters), counters.cb
            )
            return counters.WorkingSetSize / (1024 * 1024)
        return 0


def main():
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    apl_a = get_match_apl('azoriushighnoon')
    apl_b = get_match_apl('izzetspellementals')
    deck_a, _ = load_deck_from_file('decks/azorius_high_noon_standard.txt')
    deck_b, _ = load_deck_from_file('decks/izzet_spellementals_standard.txt')

    base = rss_mb()
    print(f"[init] RSS={base:.0f} MB (after CardDB + decks loaded)", flush=True)

    t0 = time.time()
    for batch in range(6):
        for s in range(batch * 5, (batch + 1) * 5):
            run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
        rss = rss_mb()
        delta = rss - base
        elapsed = time.time() - t0
        print(f"  after game {(batch+1)*5:>2}  RSS={rss:6.0f} MB  "
              f"delta=+{delta:5.0f} MB  elapsed={elapsed:5.1f}s", flush=True)

    # Force GC and re-measure
    gc.collect()
    rss = rss_mb()
    print(f"[after gc.collect()] RSS={rss:.0f} MB  delta=+{rss-base:.0f} MB", flush=True)


if __name__ == "__main__":
    main()
