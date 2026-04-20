import json, glob, sys
sys.path.insert(0,'.')

files = sorted(glob.glob('data/parallel_results_*.json'))[-4:]
for f in files:
    with open(f) as fh: d = json.load(fh)
    deck = d.get('our_deck','?')
    fmt  = d.get('format','?')
    fw   = d.get('field_weighted_match', 0)
    t    = d.get('elapsed_s', 0)
    results = d.get('results', [])
    errors  = [r for r in results if r.get('error')]
    ok      = [r for r in results if not r.get('error')]

    print(f"\n{'='*70}")
    print(f"  {deck} ({fmt.upper()})  —  field-weighted match win%: {fw}%  [{t}s]")
    print(f"  {len(ok)} ok / {len(errors)} errors")
    print(f"{'='*70}")
    print(f"  {'Opponent':<30} {'Field%':>6}  {'G1':>6}  {'G2':>6}  {'Match':>7}  Src")
    print(f"  {'-'*65}")
    for r in sorted(results, key=lambda x: -x.get('field_pct',0)):
        opp   = r.get('opp','?')
        fp    = r.get('field_pct', 0)
        if r.get('error'):
            print(f"  {'ERR':<30} {fp:>5.1f}%  {r['error'][:35]}")
            continue
        g1    = r.get('g1', 0)
        g2    = r.get('g2', 0)
        match = r.get('match', 0)
        src   = r.get('g1_source', r.get('type','?'))[:3]
        print(f"  {opp:<30} {fp:>5.1f}%  {g1:>5.1f}%  {g2:>5.1f}%  {match:>6.1f}%  {src}")
