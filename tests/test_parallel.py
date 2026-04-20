import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multiprocessing as mp

def main():
    from parallel_sim import _worker

    tasks = [
        {"our_deck":"Legacy Humans","opp_name":"Dimir Reanimator",
         "field_pct":22.4,"n":300,"seed":42,"format_name":"legacy","use_combo":True},
        {"our_deck":"Legacy Humans","opp_name":"Eldrazi Stompy",
         "field_pct":6.4,"n":300,"seed":43,"format_name":"legacy","use_combo":False},
        {"our_deck":"Legacy Humans","opp_name":"Dimir Tempo",
         "field_pct":10.5,"n":300,"seed":44,"format_name":"legacy","use_combo":False},
    ]

    print("Sequential test...")
    for t in tasks:
        r = _worker(t)
        if r.get("error"):
            print(f"  {r['opp']}: ERROR — {r['error']}")
        else:
            print(f"  {r['opp']}: G1={r['g1']:.1f}%  Match={r['match']:.1f}%  ({r['type']})")

    print("\nPool test (2 cores)...")
    with mp.Pool(processes=2) as pool:
        results = pool.map(_worker, tasks[:2])
    for r in results:
        if r.get("error"):
            print(f"  {r['opp']}: ERROR — {r['error']}")
        else:
            print(f"  {r['opp']}: G1={r['g1']:.1f}%  Match={r['match']:.1f}%  (parallel OK)")

    print("Done.")

if __name__ == "__main__":
    mp.freeze_support()
    main()
