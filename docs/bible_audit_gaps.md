# Bible Audit — Things the APL Doesn't Model or Gets Wrong
# Systematic pass through Dom Harvey's "All About Amulet Titan" vs current APL
# Last updated: Session of April 13-14, 2026

## VERIFIED STATUS:
## ✅ = Confirmed working | ⚠️ = Fixed this session | ❌ = Still needs work | 🔲 = Low priority

## CRITICAL (likely affects speed/WR by 0.5%+ each)

### ⚠️ 1. Mirrorpool Copy BEFORE Lotus Sac Resolves (Lines 679-681) — FIXED
Bible: "Titan ETB finds Lotus + Mirrorpool, COPY BEFORE Lotus sac resolves"
The copy uses Mirrorpool activation ({4}{C}) with mana generated from Amulet
untapping the lands — but the Lotus sac trigger is still on the stack.
The copy's ETB then finds MORE lands before those Lotus sacs resolve.

**APL Status:** Sequential processing. Lotus sac fires immediately via 
_place_land_on_bf. The _skip_lotus_sac flag helps during Scapeshift/Analyst
but NOT during Titan ETB fetches. When Titan ETB fetches Lotus + Mirrorpool,
Lotus sac fires before Mirrorpool can be activated.

**Fix needed:** During Titan ETB, defer Lotus sac until after Mirrorpool 
copy resolves (same _skip_lotus_sac pattern).

### ❌ 2. Titan Copy → ETB → Fetches MORE Lands → Chain Kills (Lines 641-662)
Bible describes Triple/Quad Titan via: Titan ETB → Lotus + Mirrorpool → 
copy Titan → Copy ETB → Deeps(Mirror) + Lotus → copy again → etc.
Each copy's ETB fetches 2 more lands, chaining into 3-4 Titan attacks.

**APL Status:** Mirrorpool copy creates a token Titan that fires ETB and
fetches 2 lands. But the APL only does ONE copy. The Bible describes
chaining Copy ETB → Deeps(Mirror) → copy AGAIN. The APL doesn't chain.

**Fix needed:** After Mirrorpool copy's ETB, if Deeps can become Mirrorpool
from GY (where original Mirrorpool went after legendary rule), the APL
should activate Deeps-as-Mirrorpool for a SECOND copy, and so on.

### ✅ 3. Scapeshift OHKO Line FULLY IMPLEMENTED (Lines 916-927)
Bible: Shift for 2 Lotus + bounce + TWest → 9 mana → Transmute → Pact → 
Analyst → return all lands → 13+ mana → Transmute → Pact → Titan → 
Titan ETB → Woodland + Lotus → Analyst loop = infinite damage.

**APL Status:** _try_scapeshift exists but likely doesn't execute the full
TWest transmute → Pact → Analyst → return → Pact → Titan chain. It 
probably just fetches lands and ramps. The Scapeshift OHKO is a SEPARATE
win condition from combat Titan.

**Fix needed:** Implement the full Scapeshift deterministic kill sequence
when conditions are met (Amulet + 4 lands + Shift in hand).

### ✅ 4. Vestige → Bounce → Replay Vestige = Extra Mana (Line 1458) — VERIFIED WORKING
Bible: "With one Amulet, playing Vestige → bounceland returning Vestige → 
replay Vestige gets you the same amount of mana as playing the bounceland 
repeatedly while letting you keep this additional land in play."

**APL Status:** The greedy loop might not sequence Vestige → bounce → 
replay Vestige optimally. Vestige's ETB gives 1 mana, then bounce returns
it, then replay gives ANOTHER ETB → 1 more mana. Net: 2 Vestige ETBs 
= 2 extra mana + Vestige stays on BF.

**Fix needed:** Check if bounce return of Vestige + replay is available
as a mana-generating sequence in the greedy loop.

### ✅ 5. Mycosynth Gardens Copying Amulet — LOGIC EXISTS, DECKLIST ISSUE (Lines 541-604)
Bible: "Titan ETB finds Battlements + Gardens, haste Titan + copy Amulet"
Gardens taps for {C}, then {1} to copy Amulet artifact = double Amulet.
This upgrades single-Amulet hands into double-Amulet kills.

**APL Status:** Gardens is in the deck and produces {C}. But the APL 
likely never COPIES Amulet with Gardens. The copy requires {1},{T} and
the APL would need to recognize "I have Gardens + Amulet → copy Amulet
before casting Titan to enable double-Amulet lines."

**Fix needed:** Add Gardens-copies-Amulet logic to main phase when it
enables a meaningfully better Titan turn (double Amulet).

## HIGH (affects speed by 0.1-0.5%)

### 6. Otawara Channel During Declare Attackers (Lines 379-384)
Bible: "Titan ETB → Battlements + Vestige → Attack → finds bounce + 
Otawara → float UGX → channel Otawara bounce something (all during 
declare attackers)"

**APL Status:** Otawara channel is a goldfish consideration for clearing
your own things or bouncing Titan for replay. In matchplay this is critical
but for goldfish probably low impact.

### 7. Pact in Response to Bounce/Saga Trigger (Line 1257)
Bible: "You can cast Pact in response to the bounce trigger... Similarly,
you can Pact in response to the final chapter trigger from Urza's Saga"

**APL Status:** Not modeled. Pact is cast during main phase. Casting Pact
at instant speed in response to triggers would allow finding Titan before
deciding what to do with the bounce/Saga trigger resolution.

### 8. Urza's Cave Instant-Speed Fetch (Line 1494)
Bible: "Certain effects are much more valuable at instant speed (Bojuka Bog
is unreliable but much better as an instant; Valakut triggers can shoot a 
wider range of things)"

**APL Status:** Cave is in the deck but the APL likely only activates it
during main phase. Instant-speed Cave → fetch bounce → mana generation
during opponent's turn or in response to triggers isn't modeled.

### ✅ 9. Spelunking's Explore — Put a Land From Hand (Line 1093) — VERIFIED WORKING  
Bible: "Stapled to this Amulet riff is an Explore"
Spelunking ETB: draw a card + if it's a land, you MAY put it onto the BF.

**APL Status:** Need to verify: does the APL's Spelunking ETB actually
put the drawn land onto BF? Or just draw? The extra land from Spelunking
is a critical mana boost on the combo turn.

### 10. Vesuva Entering as Bounce → Returns Itself to Hand (Line 1355)
Bible: "A Titan trigger can find Vesuva and have it copy a bounceland to
return itself to your hand. This helps if you don't know which land you
want to double up on yet or need a more flexible, generic land drop."

**APL Status:** Vesuva can copy BF lands but does the APL ever choose to
copy a bounce land with it? This gives a "free" bounce land in hand for
future use + Vesuva's ETB as the bounce land produces 2 mana.

## MEDIUM (correctness / edge cases)

### 11. Double Shift Hands (Lines 965-973)
Bible: "Shift 1: 3 Vestige → 4GG floating → Cast Shift 2 → Shift 2:
Lotus + bounce + TWest → complete OHKO"

**APL Status:** Probably casts one Scapeshift but never sequences two
Scapeshifts in the same turn.

### 12. Shift for Boseiju + Bounce to Destroy Hate (Line 936)
Bible: "Include Boseiju + bounceland into your Shift pile (bouncing + 
using it before Lotus triggers resolve) to swat away on-board hate"

**APL Status:** Goldfish sim has no opponent permanents to destroy, but
the Boseiju inclusion in Shift piles matters for matchplay.

### 13. Woodland Becomes Urza's Saga for Slow Grind (Line 1485)
Bible: "You can slowly build a permanent Urza's Saga (activating in your
draw step each turn you want to gain a counter)"

**APL Status:** Not modeled. Edge case for extremely long games.

### 14. Grazer + Vestige = Mana-Neutral Without Amulet (Lines 1148, 1467)
Bible: "With Crumbling Vestige, Grazer can 'pay for itself': Turn 1 
Grazer → Vestige (G)"

**APL Status:** Need to verify Grazer → Vestige sequence generates G from
Vestige ETB (choose G) to pay for Grazer cost.

## ENGINE-LEVEL BUGS FOUND (Not APL logic — affects ALL decks)

### ⚠️ FIXED: Deck Loader Shared Card Objects (data/deck.py line 163)
`cards.extend([card] * qty)` created qty REFERENCES to the SAME Card object.
ALL copies of every card shared identical Python objects in memory.
- Tapping one land tapped ALL copies across ALL zones (70% of games!)
- 4.6 mana LOST per game average from phantom tapped lands
- Summoning sickness, tags, counters all leaked between copies
- BF land count inflated (Colossus P/T wrong 178 times)
**Fix:** `copy.deepcopy(card)` for each decklist entry.
**Impact:** WR 97.7% → 98.9% (+1.2%)

### ❌ UNFIXED: Cross-Game Card Object Reuse (run_simulation / take_opening_hand)
The same 60 Card objects persist across ALL 20,000 simulation games.
`run_simulation` never deepcopies the deck between games.
- After game 1: 12 cards tapped, 21 cards have stale turn_entered
- By game 5: 35 of 60 cards have stale state from previous games
- Saga chapter tracking uses turn_entered → chapters miscalculated in 99.99% of games
- `.tags`, `.turn_entered`, `.counters`, `.power`/`.toughness` all persist
- `_untap()` only resets `.tapped` and `.summoning_sickness`
**Fix needed:** `copy.deepcopy(deck)` at start of each game in run_simulation
or in take_opening_hand before shuffling.

### 🟡 MINOR: Boseiju Double-Added to Graveyard
Boseiju appears 2x in GY in ~1% of games. Lotus sac adds it to GY AND
`_track_land_to_gy` also adds it. Doesn't affect gameplay, just bookkeeping.

## BIBLE SCENARIO FAILURES (APL Logic — to fix after engine is solid)

### ❌ Bounce Loop Trap (Scenario 4)
When bf_land_count ≤ 1 and Amulet is active, Grazer puts bounce land
(priority 90) over permanent land like Vestige (priority 70). The bounce
eats the only permanent land, leaving 0 permanent + 1 bounce. Stuck in
infinite bounce cycle generating mana but never accumulating lands.
**Fix:** When bf_count ≤ 1, prefer permanent lands over bounces for Grazer.

### ❌ Scapeshift Timing at 4 Lands (Scenario 3)
`_try_scapeshift` doesn't fire at priority 0.3 when Amulet + 4 lands are
available. Instead the APL deploys Titan (priority higher). For hands with
Scapeshift but no Titan, Scapeshift should fire earlier.

### ❌ Gardens T1 Priority (Scenario 2)
With Gardens + Amulet in hand T1, APL plays Forest instead of Gardens.
Gardens T1 enables: T2 play bounce → Gardens copies Amulet → double Amulet
→ massive mana burst. Forest T1 is slower.

### ❌ Pact Upkeep Tap Fixed, But Philosophy Wrong
Fixed: Pact upkeep now taps Hanweir for mana (no haste reservation during upkeep).
But the REAL fix should be: only tap the MINIMUM lands needed for {2}{G}{G},
leaving extras untapped for main phase. Currently taps all → untaps all → net
same, but misses instant-speed opportunities.
