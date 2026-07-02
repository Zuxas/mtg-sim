# AUTO_GENERATED_APLS.md

**29 APLs flagged for rewrite.** Each has  on the class.
All produce unreliable sim results — simple attack-everything logic beats
decision-aware opponents. Exclude from gauntlets until rewritten.

## Priority: Standard Match APLs (affect gauntlet results)

| Class | File | Deck | Status |
|---|---|---|---|
|  |  | Simic Jackal | NEEDS REWRITE |
|  |  | Four Color Overlords | NEEDS REWRITE |
|  |  | Esper Pixie | NEEDS REWRITE |
|  |  | Izzet Spellementals | NEEDS REWRITE |
|  |  | Azorius Control | NEEDS REWRITE |
|  |  | Izzet Cauldron | NEEDS REWRITE |
|  |  | Grixis Discard | NEEDS REWRITE |
|  |  | Dimir Oculus | NEEDS REWRITE |

## Standard Goldfish APLs

| Class | File | Deck | Status |
|---|---|---|---|
|  |  | Simic Jackal | NEEDS REWRITE |
|  |  | Four Color Overlords | NEEDS REWRITE |
|  |  | Simic Rhythm | NEEDS REWRITE |
|  |  | Mono Green Landfall | NEEDS REWRITE |
|  |  | Dimir Excruciator | NEEDS REWRITE |
|  |  | Azorius Soldiers | NEEDS REWRITE |
|  |  | Azorius Toxic | NEEDS REWRITE |
|  |  | Boros Convoke | NEEDS REWRITE |
|  |  | Cutter Affinity | NEEDS REWRITE |
|  |  | Gruul Ouroboroid | NEEDS REWRITE |
|  |  | Izzet Lessons | NEEDS REWRITE |
|  |  | Jeskai Phelia | NEEDS REWRITE |
|  |  | Mono White Aggro | NEEDS REWRITE |
|  |  | Temur Analyst | NEEDS REWRITE |

## Modern / Legacy APLs (lower priority)

| Class | File | Deck | Status |
|---|---|---|---|
|  |  | Simic Rhythm | NEEDS REWRITE |
|  |  | Jeskai Control | NEEDS REWRITE |
|  |  | Izzet Lessons | NEEDS REWRITE |
|  |  | Belcher | NEEDS REWRITE |
|  |  | Neoform | NEEDS REWRITE |
| RubyStormMatchAPL | apl/ruby_storm_match.py | Ruby Storm | REWRITTEN + HAND-AUDITED 2026-07-02 (kill reachability via wishboard fix; see mismodeled_matchups 'ruby storm' — cell still INFLATED, clock too slow) |
|  |  | UW Blink | NEEDS REWRITE |
|  |  | UW Control | NEEDS REWRITE |

## How to detect in code

```python
from apl import MATCH_APL_REGISTRY
import importlib
def is_auto(key):
    entry = MATCH_APL_REGISTRY.get(key)
    if not entry: return False
    mod = importlib.import_module(entry[0])
    cls = getattr(mod, entry[1])
    return getattr(cls, "AUTO_GENERATED", False)
```