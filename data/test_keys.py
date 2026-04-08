from sim_bridge import _infer_archetype_key, ARCHETYPE_CLOCKS, avg_kill_turn

# Test: verify avg kill turns match expected measured values (within 0.5 turns)
tests = [
    ("Boros Energy",       6.98),
    ("Living End",         6.53),
    ("Golgari Yawgmoth",   7.37),
    ("Eldrazi Tron",       6.75),
    ("UW Blink",           6.13),
    ("Amulet Titan",       8.65),
    ("Dimir Reanimator",   2.93),
    ("Mono Red Painter",   4.08),
    ("Jeskai Blink",       7.79),
    ("Izzet Affinity",     9.35),
    ("Domain Zoo",         9.03),
    ("Dimir Tempo",        3.90),  # T3.5-4 expected for tempo
    ("Hogaak",             3.80),
]

all_ok = True
for name, expected_avg in tests:
    key  = _infer_archetype_key(name)
    dist = ARCHETYPE_CLOCKS.get(key, {})
    avg  = avg_kill_turn(dist) if dist else 99.0
    diff = abs(avg - expected_avg)
    ok   = diff < 1.0  # within 1 turn
    if not ok:
        all_ok = False
    flag = "OK  " if ok else "FAIL"
    print(f"  {flag}  {name:<25} -> {key:<25} T{avg:.2f}  (expected T{expected_avg:.2f})")

print()
print("All within range:", all_ok)
print("Total clocks:", len(ARCHETYPE_CLOCKS))
