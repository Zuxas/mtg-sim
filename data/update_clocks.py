"""Update sim_bridge.py ARCHETYPE_CLOCKS with measured kill distributions."""
import json, re

with open("data/measured_clocks.json") as f:
    measured = json.load(f)

lines = []
for name, data in sorted(measured.items()):
    key = name.lower().replace("-","").replace(" ","").replace("'","")
    dist = {int(k): v for k, v in data["dist"].items() if v > 0.5}
    lines.append(f'    "{key}": {dist},  # T{data["avg"]:.2f} avg (measured)')

print("Paste these into ARCHETYPE_CLOCKS in sim_bridge.py:\n")
for l in lines:
    print(l)
