"""Find effects that happen twice: once in the engine's card handler and
again by hand in a match APL.

Many match APLs were written before the engine had handlers. They call
gs.cast_spell(card) and then do the card's effect themselves (draw a card,
make a token, gain life). The handlers now do it too.

For every top-level cast_spell in a set of seeded mirror games this records
what changed INSIDE the call (the engine) and what the APL changed by hand
between that call and its next cast. A row is printed when both did the same
kind of thing for the same card at least 3 times.

It reports suspects, not proof: a second, real trigger can look the same.
"n/n casts" (every single cast) is the strong signal. Confirm by reading the
APL at the cast, then delete the hand-written copy.

Usage:  python scripts/audit_double_effects.py                 # every APL with a deck file
        python scripts/audit_double_effects.py borosenergy jeskaiblink
"""
import collections
import contextlib
import glob
import importlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apl import MATCH_APL_REGISTRY as R
from data.deck import load_deck_from_file as L
from engine import match_engine as ME
from engine.game_state import GameState as G

state={'cur':None,'depth':0}
found=collections.Counter(); casts=collections.Counter()
def snap(gs): return dict(life=gs.life,dmg=gs.damage_dealt,bf=len(gs.zones.battlefield),lib=len(gs.zones.library),energy=getattr(gs,'energy',0))
def diff(a,b):
    d=set()
    if b['bf']-a['bf']>1: d.add('token/extra permanent')
    if b['lib']<a['lib']: d.add('draw')
    if b['life']>a['life']: d.add('life gain')
    if b['dmg']>a['dmg']: d.add('damage')
    if b['energy']>a['energy']: d.add('energy')
    return d
orig=G.cast_spell
def cast(self,card,*a,**k):
    close(self)
    before=snap(self); state['depth']+=1
    try: ok=orig(self,card,*a,**k)
    finally: state['depth']-=1
    if ok and state['depth']==0:
        after=snap(self); state['cur']=(self,card.name,diff(before,after),after)
        casts[(state['apl'],card.name)]+=1
    return ok
def close(gs):
    cur=state['cur']
    if cur and cur[0] is gs:
        _,name,eng,after=cur; now=snap(gs)
        a=dict(after); a['bf']-=1          # diff() ignores the first new permanent
        manual=diff(a,now)
        for kind in eng & manual: found[(state['apl'],name,kind)]+=1
    state['cur']=None
G.cast_spell=cast
def cls(k):
    m,c=R[k]; return getattr(importlib.import_module(m),c)
# deck per registry key: best-effort filename match
decks={os.path.basename(f)[:-4].replace('_',''):f for f in glob.glob('decks/*.txt')}
keys = sys.argv[1:]
if not keys:
    seen = set()
    for k in R:
        if R[k] not in seen and any(d.startswith(k) for d in decks):
            seen.add(R[k]); keys.append(k)
for k in keys:
    f=next((v for d,v in decks.items() if d.startswith(k)),None)
    if not f: print("no deck for",k); continue
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            deck=L(f)[0]; A=cls(k); state['apl']=k
            class S(A):
                def main_phase_match(self,gs,opp):
                    r=super().main_phase_match(gs,opp); close(gs); return r
            for seed in range(60):
                state['cur']=None
                ME.run_match(S(),deck,S(),deck,seed=seed,on_play=seed%2==0)
    except Exception as e: print(k,"ERR",type(e).__name__,str(e)[:80])
for (apl,name,kind),n in sorted(found.items(), key=lambda x:(x[0][0],-x[1])):
    if n>=3: print(f"{apl:28s} {name:32s} {kind:22s} {n}/{casts[(apl, name)]} casts")
