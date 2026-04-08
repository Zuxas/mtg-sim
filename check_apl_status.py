import os, sys
sys.path.insert(0,'.')
from sim_bridge import _infer_archetype_key

apl_files = [f for f in os.listdir('apl') if f.endswith('.py')
             and f not in ['__init__.py','base_apl.py','mulligan.py',
                           'generic_apl.py','auto_apl.py','playbook_parser.py']]
print("Hand-tuned APLs:", apl_files)
print()

legacy = [
    ("Dimir Reanimator",22.4),("Lotus Combo",10.5),("Dimir Tempo",10.5),
    ("Cephalid Breakfast",7.5),("Eldrazi Stompy",6.4),("Sneak And Show",5.4),
    ("Mono Red Painter",5.0),("Doomsday",4.9),("Izzet Delver",4.7),
    ("Death And Taxes",4.6),("Bant Nadu",4.3),("Four-Color",3.7),
    ("Jeskai Control",3.6),("Mono Red Aggro",3.4),("Mono Red Prison",3.2),
]

APL_MAP = {
    "humans":"hand-tuned","elves":"hand-tuned","delver":"hand-tuned",
    "lands":"hand-tuned","painter":"hand-tuned","stoneforge":"hand-tuned",
    "hogaak":"hand-tuned","izzet delver":"hand-tuned",
}
GENERIC_OK   = {"aggro","midrange","ramp","four-color","tempo","control"}
NEEDS_CUSTOM = {"dimir reanimator","reanimator","lotus combo","cephalid breakfast",
                "sneak and show","mono red painter","doomsday","bant nadu","combo"}

print(f"{'Archetype':<28} {'Field%':>6}  {'Status':<28}  Strategy")
print("-"*80)
for arch, pct in legacy:
    key = _infer_archetype_key(arch)
    if key in APL_MAP:
        status = "hand-tuned APL"
        strat  = "READY - real data now"
    elif key in NEEDS_CUSTOM or arch.lower().replace(" ","") in {k.replace(" ","") for k in NEEDS_CUSTOM}:
        status = "MISSING - needs APL"
        strat  = "AutoAPL or custom"
    elif key in GENERIC_OK:
        status = "GenericAPL (~80%)"
        strat  = "usable, not perfect"
    else:
        status = "GenericAPL (~70%)"
        strat  = "partial"
    print(f"{arch:<28} {pct:>5.1f}%  {status:<28}  {strat}")
