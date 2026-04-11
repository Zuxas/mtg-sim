# BOROS ENERGY — CARD-BY-CARD APL AUDIT
# Every card analyzed from pilot + opponent perspective
# What APL currently does vs what it SHOULD do

## CRITICAL CORRECTIONS NEEDED

### 1. Phlage, Titan of Fire's Fury (Main x4) — FUNDAMENTALLY WRONG
**Oracle:** "When Phlage enters, sacrifice it unless it escaped."
         "Whenever Phlage enters or attacks, it deals 3 damage to any target and you gain 3 life."
         "Escape—{R}{R}{W}{W}, Exile five other cards from your graveyard."
**Current APL:** Treats Phlage as a normal 6/6 creature when hardcast.
**CORRECT behavior:**
  - HARDCAST {1}{R}{W}: ETB → 3 damage + 3 life → IMMEDIATELY SACRIFICED (goes to GY)
    → This is a removal spell that gains life, NOT a creature deployment
  - ESCAPE {R}{R}{W}{W} + exile 5 from GY: ETB → 3 damage + 3 life → STAYS as 6/6
    → This is the late-game finisher, requires 5+ cards in GY
  - Each ATTACK: deals 3 more damage + 3 more life (if escaped and on board)
**Pilot perspective:** Early game = burn spell. Late game = recurring 6/6 haste.
**Opponent perspective:** Kill it before it attacks. The ETB still fires even if countered.

### 2. Ocelot Pride (Main x4) — TIMING WRONG
**Oracle:** "At the beginning of your END STEP, if you gained life this turn,
           create a 1/1 white Cat creature token."
**Current APL:** May be treating this as "whenever you gain life" (multiple triggers)
**CORRECT behavior:**
  - ONCE per turn, at end step
  - Checks "did you gain ANY life this turn?" — yes/no binary
  - If yes: ONE Cat token per Ocelot
  - With 2 Ocelots: 2 Cat tokens per end step
  - Ascend (10+ permanents): copy ALL tokens that entered this turn
**Pilot:** Must gain life during your turn (combat with lifelink, Guide trigger)
**Opponent:** Remove Ocelot BEFORE end step to prevent tokens

### 3. Guide of Souls (Main x4) — ATTACK ABILITY MISSING
**Oracle:** "Whenever another creature you control enters, you gain 1 life and get {E}."
           "Whenever you attack, you may pay {E}{E}{E}. When you do, put two +1/+1 counters
            and a flying counter on target attacking creature."
**Current APL:** Models lifegain + energy, MISSING the attack ability.
**CORRECT behavior:**
  - Passive: Each creature entering → +1 life, +1 {E} per Guide on board
  - Attack: Pay 3{E} → any attacker gets +2/+2 and FLYING
    → This turns a ground creature into a flyer that can't be blocked
    → Example: Ragavan 2/1 → 4/3 flying Angel. Voice 1/3 → 3/5 flying.
**Pilot:** Save 3 energy for the pump. Makes any creature a lethal flyer.
**Opponent:** Must keep energy low (kill Guide) to prevent pump.

### 4. Voice of Victory (Main x3) — PARTIALLY CORRECT, MISSING SACRIFICE + SPELL LOCK
**Oracle:** "Mobilize 2 (Whenever this creature attacks, create two tapped and attacking
           1/1 red Warrior creature tokens. Sacrifice them at the beginning of the 
           next end step.)"
           "Your opponents can't cast spells during your turn."
**Current APL:** Models Mobilize tokens, MISSING:
  - Tokens are SACRIFICED at end step (not permanent)
  - "Opponents can't cast spells during your turn" = NO INSTANT-SPEED INTERACTION
**CORRECT behavior:**
  - Attack → 2 Warriors enter tapped and attacking → deal combat damage
  - Each Warrior entering triggers Guide (+1 life, +1E per Guide)
  - At YOUR end step: Warriors are sacrificed
    → Sacrifice to Bombardment BEFORE end step (1 dmg each)
    → Sacrifice triggers Ajani transform (Cats dying)
  - SPELL LOCK: Opponent can't Bolt/Discharge during YOUR turn
    → This means Voice must be removed on THEIR turn or during YOUR end step
**Pilot:** Voice + Bombardment = 2 free damage per turn from Mobilize tokens
**Opponent:** Remove Voice on YOUR turn before it attacks. Can't interact during their turn.

### 5. Goblin Bombardment (Main x3) — PARTIALLY CORRECT, NEEDS REACTIVE USE
**Oracle:** "Sacrifice a creature: This enchantment deals 1 damage to any target."
**Current APL:** End step sacrifice tokens for damage. MISSING:
  - REACTIVE sacrifice: In response to opponent removal, sacrifice target for 1 damage
    → Opponent tries to exile your Guide → sacrifice it to Bombardment for 1 damage first
  - NO mana cost, NO tap cost → can sacrifice unlimited creatures per activation
  - Can target creatures OR players (any target)
  - Voice Mobilize tokens → sacrifice before forced end-step sacrifice → free damage
  - Ocelot tokens → each sacrifice triggers Ajani transform if Cats die
**Pilot:** Think of this as "all creature deaths = 1 damage to face." Never let a creature die without getting Bombardment value.
**Opponent:** Must destroy Bombardment to stop the value engine. Enchantment removal is key.

### 6. Ajani, Nacatl Pariah (Main x4) — TRANSFORM NOT MODELED
**Oracle:** "When Ajani enters, create a 2/1 white Cat Warrior creature token."
           "Whenever one or more other Cats you control die, you may exile Ajani, 
            then return him to the battlefield transformed under his owner's control."
**Current APL:** Models ETB 2/1 token. MISSING transform.
**CORRECT behavior:**
  - ETB: 2/1 Cat token (triggers Guide: +1 life, +1E)
  - Transform: When ANY Cat dies (Ocelot tokens, Cat Warrior tokens, etc.)
    → Ajani transforms into Ajani, Resilient Leader (planeswalker)
    → BACK FACE: Loyalty 4, +2: Put +1/+1 counter on each creature
    → -1: Return Cat creature from GY to battlefield
    → The planeswalker continues generating value
  - Bombardment sacrifice + Cat death → Ajani transforms
**Pilot:** Deploy Ajani, let a Cat die (naturally or to Bombardment), flip into PW
**Opponent:** Exiling Ajani prevents the transform (no death trigger). Don't kill Cats if Ajani is on board.

### 7. Screaming Nemesis (Main x1) — ANTI-LIFEGAIN NOT MODELED
**Oracle:** "Haste. Whenever this creature is dealt damage, it deals that much damage 
           to any other target. If a player is dealt damage this way, they can't gain 
           life for the rest of the game."
**Current APL:** Models as 3/3 haste. MISSING damage reflection + lifegain prevention.
**CORRECT behavior:**
  - Any damage to Nemesis → reflects to any target
  - If player takes reflected damage → NO LIFEGAIN for rest of game (permanent!)
  - This means: opponent can't Bolt Nemesis or they lose lifegain forever
  - In combat: if blocked by a 2/2, Nemesis takes 2 → reflects 2 to opponent → no more lifegain
**Pilot:** Attack into blockers. The reflection is upside. Against lifegain decks, this is devastating.
**Opponent:** NEVER use damage-based removal on Nemesis. Use exile (Solitude, Prismatic Ending, Leyline Binding).

### 8. Seasoned Pyromancer (Main x2) — TOKEN GENERATION NOT MODELED
**Oracle:** "When enters, discard two cards, then draw two cards. For each nonland card
           discarded this way, create a 1/1 red Elemental creature token."
           "{3}{R}{R}, Exile from GY: Create two 1/1 red Elemental tokens."
**Current APL:** Generic creature deployment. MISSING:
  - ETB: Discard 2 + Draw 2 + create 0-2 Elemental tokens
    → Discarding Phlage = puts Phlage in GY for escape! (Key synergy)
    → Each Elemental triggers Guide (+1 life, +1E)
  - GY activation: {3}{R}{R} for 2 Elemental tokens (late game)
**Pilot:** Discard lands/Phlage. Keep spells. Generate tokens that feed Bombardment.
**Opponent:** The card filtering makes Boros's draws more consistent.

### 9. Ragavan, Nimble Pilferer (Main x4) — COMBAT TRIGGER NOT MODELED
**Oracle:** "Whenever Ragavan deals combat damage to a player, create a Treasure token
           and exile top card of that player's library. Until EOT, you may cast that card."
           "Dash {1}{R}: gains haste, returns to hand at next end step."
**Current APL:** Generic creature. MISSING:
  - Combat damage → Treasure token (artifact, extra mana next turn)
  - Combat damage → exile opponent's card (card advantage)
  - Dash mode: haste for {1}{R}, returns to hand (dodges sorcery-speed removal)
**Pilot:** T1 Ragavan on the play is the best opening. Each hit = +1 mana +1 card.
**Opponent:** MUST kill Ragavan before it connects. Lava Dart kills it for 0 mana.

### 10. Static Prison (Main x2) — ENERGY MAINTENANCE NOT MODELED
**Oracle:** "ETB: Exile target nonland permanent. You get {E}{E}."
           "At beginning of your first main phase, sacrifice unless you pay {E}."
**Current APL:** Models exile + energy gain. MISSING:
  - Must pay 1 energy EACH TURN to maintain the prison
  - If energy runs out → permanent comes back
  - Energy is shared with Guide of Souls generation and Galvanic Discharge
**Pilot:** Prison is temporary — budget energy for it or let it fall off strategically.
**Opponent:** If Boros runs low on energy, the exiled permanent returns.

### 11. Galvanic Discharge (Main x4) — MOSTLY CORRECT
**Oracle:** "Choose target creature or planeswalker. You get {E}{E}{E}, then you may pay
           any amount of {E}. Galvanic Discharge deals that much damage to that permanent."
**Current APL:** Mostly correct — gets 3E, spends energy for damage.
**VERIFY:** Does NOT hit players (creature or planeswalker ONLY).
**Key:** With 6 energy: kills Murktide Regent (8/8 with enough energy).
         Energy stacks across turns — Guide generates energy each creature entering.

### 12. Thraben Charm (Main x2) — SCALING DAMAGE NOT MODELED
**Oracle:** "Choose one —
           • Deals damage equal to 2× number of creatures you control to target creature.
           • Destroy target enchantment.
           • Exile graveyards."
**Current APL:** May model as generic removal. MISSING:
  - Mode 1 scales with board: 4 creatures = 8 damage to a creature
  - With tokens from Voice/Ocelot/Ajani, this kills ANYTHING
  - Mode 2: Destroy enchantment (hits opponent's Blood Moon, Urza's Saga, etc.)
**Pilot:** In a board stall with 6+ creatures, Thraben Charm kills Emrakul.
**Opponent:** Keep Boros's creature count low or Charm kills your biggest threat.

## REMOVAL/INTERACTION SUMMARY (Pilot Perspective)
- Lightning Bolt: 3 to any target (face or creature)
- Galvanic Discharge: 3+ to creature/PW only (scales with energy)
- Static Prison: Exile nonland permanent (temporary, costs {E}/turn)
- Thraben Charm: 2× creatures damage to creature (scales with board)
- Phlage hardcast: 3 damage to any target + 3 life (then sacrifice Phlage)
- Goblin Bombardment: 1 damage per creature sacrificed (unlimited activations)

## ENERGY ECONOMY
Sources:
  - Guide of Souls: +1{E} per creature entering (each Guide)
  - Galvanic Discharge: +3{E} on cast
  - Static Prison: +2{E} on cast
Costs:
  - Galvanic Discharge: spend {E} for damage (1{E}=1 dmg)
  - Static Prison: pay 1{E} per turn or lose the prison
  - Guide of Souls: pay 3{E} for +2/+2 flying on attacker
  - Wrath of the Skies (SB): get X{E}, then spend to set wrath threshold

## THE VALUE ENGINE (How Boros Actually Wins)
1. Guide of Souls on board → every creature entering = +1 life +1{E}
2. Deploy creatures (Ragavan, Ajani, Voice) → Guide triggers
3. Ajani ETB: 2/1 Cat token → Guide triggers (+1 life, +1{E})
4. Ocelot on board: at end step, if gained life → 1/1 Cat token
5. Cat token entering → Guide triggers AGAIN (+1 life, +1{E})
6. Voice attacks → 2 Warrior tokens → Guide triggers ×2
7. Bombardment: sacrifice expendable tokens for face damage
8. Warrior tokens sacrifice at end step → sacrifice to Bombardment FIRST
9. Cat dies → Ajani transforms into planeswalker
10. Energy generated → fuel Galvanic Discharge for big removal or Guide pump for flying

## LAND NOTES
- 10 fetchlands: Each pays 1 life → Boros starts at ~17 life with 3 fetches
- 3 Sacred Foundry: Pay 2 life if untapped → further life loss
- 3 Arena of Glory: Exert for {R}{R} + haste on creature
- 1 Dalkovan Encampment: {2}{W},{T} → creates 2 Warrior tokens when attacking (like Voice)
- NET LIFE LOSS from lands: typically 4-6 life (3 fetches + 1-2 shocklands)
  → Boros effectively starts at 14-16 life, NOT 20

## APL CHANGES NEEDED (Priority Order)

### P0 — Game-Breaking (Matchup results are wrong without these)

1. **Phlage hardcast = sacrifice** (currently stays as 6/6)
   - Hardcast {1}{R}{W}: ETB trigger fires (3 dmg + 3 life), then SACRIFICE
   - Only stays if ESCAPED: {R}{R}{W}{W} + exile 5 cards from GY
   - APL needs: track Phlage in GY, check GY size ≥6 for escape, model escape cost correctly
   - This changes Boros from "deploy 6/6 for 3 mana" to "burn spell that fuels late game"

2. **Ocelot token timing: end step, not on-trigger**
   - Current: may trigger multiple times per lifegain
   - Correct: ONE check at end step, ONE Cat per Ocelot
   - With 2 Ocelots: 2 Cats (not unlimited)

3. **Fetchland + shockland life loss** 
   - Boros pays 4-6 life from mana base
   - Effective starting life: 14-16, not 20
   - This makes the Prowess burst easier to lethal

### P1 — Significant (Affects accuracy by 5%+)

4. **Guide of Souls attack pump ({E}{E}{E} → +2/+2 flying)**
   - Converts any attacker into a flyer
   - This is how Boros pushes through board stalls
   - Changes combat math significantly

5. **Voice of Victory spell lock ("opponents can't cast spells during your turn")**
   - Opponent can't use instant-speed removal during Boros's turn
   - Changes when opponent can interact
   - Currently not modeled

6. **Ajani transform → planeswalker**
   - When Cat dies → Ajani becomes PW with +2 (pump all creatures)
   - Common sequence: Ajani ETB → Cat token → Bombardment sacrifice Cat → Ajani transforms
   - Ongoing value engine

7. **Ragavan combat triggers (Treasure + exile card)**
   - Each Ragavan hit = +1 mana next turn + card advantage
   - This accelerates Boros's mana development

### P2 — Minor (Affects accuracy by 1-3%)

8. **Screaming Nemesis reflection + anti-lifegain**
9. **Seasoned Pyromancer discard → draw + tokens**
10. **Thraben Charm scaling damage (2× creatures)**
11. **Mobilize tokens sacrificed to Bombardment BEFORE end step sacrifice**
12. **Static Prison energy maintenance cost**
13. **Arena of Glory exert for haste**
14. **Dalkovan Encampment token generation**


## CRITICAL INTERACTION LINES (Pilot Knowledge)

### LINE 1: Ajani Defensive Transform (removal protection)
**Situation:** Opponent targets Ajani with removal (Bolt, Fatal Push, Prismatic Ending, etc.)
**Response:** Sacrifice a Cat token to Goblin Bombardment (or kill Cat with Galvanic Discharge)
**Result:**
  1. Cat dies → Ajani transform trigger: "exile Ajani, return transformed"
  2. Ajani is EXILED (leaves the battlefield as part of transform)
  3. Opponent's removal spell has NO LEGAL TARGET → FIZZLES (does nothing)
  4. Ajani returns as planeswalker (Ajani, Resilient Leader)
  5. Net result: opponent wasted a removal spell, you got a planeswalker + 1 Bombardment damage
**APL requirement:** When opponent targets Ajani with removal AND we have a Cat + Bombardment,
  the APL must sacrifice the Cat in response to protect Ajani. This is NOT optional — 
  any competitive pilot does this 100% of the time.
**Also works with:** Galvanic Discharge targeting your own Cat (costs energy but same result)

### LINE 2: Bombardment Sacrifice in Response to Removal
**Situation:** Opponent targets ANY creature with removal
**Response:** Sacrifice that creature to Goblin Bombardment before removal resolves
**Result:** 
  1. Creature is sacrificed → Bombardment deals 1 damage
  2. Removal spell has no target → FIZZLES
  3. Net: opponent wasted a card, you got 1 damage
**APL requirement:** Never let a creature die to removal when Bombardment is on board.
  Always sacrifice in response for value.

### LINE 3: Voice of Victory Spell Lock + Mobilize
**Situation:** Voice of Victory is on board during your turn
**Rule:** "Your opponents can't cast spells during your turn"
**Result:**
  - Opponent CANNOT use instant-speed removal during your combat
  - Opponent CANNOT cast combat tricks
  - Opponent CANNOT counter your spells (during your turn)
  - Voice's Mobilize tokens are SAFE from instant-speed removal
  - Opponent must interact ONLY during THEIR turn or your end step
**APL requirement:** When Voice is on board, opponent's respond_to_spell should return None
  during Boros's turn. Voice fundamentally changes the interaction dynamic.

### LINE 4: Phlage Hardcast as Removal + GY Setup
**Situation:** Opponent has a 3-toughness creature you need to kill
**Play:** Hardcast Phlage for {1}{R}{W}
**Result:**
  1. ETB: 3 damage to the creature (kills it) + 3 life for you
  2. Phlage is sacrificed (since not escaped)
  3. Phlage goes to GY → available for future escape
  4. If Seasoned Pyromancer discards Phlage → same GY setup without spending mana
**APL requirement:** Phlage hardcast is a REMOVAL SPELL, not a creature deployment.
  Use it to kill 3-toughness creatures while fueling the GY for later escape.

### LINE 5: Guide of Souls Energy → Flying Pump
**Situation:** Board stall, opponent has ground blockers
**Play:** Attack, pay {E}{E}{E} from Guide of Souls
**Result:**
  1. Target attacking creature gets +2/+2 and FLYING
  2. Creature is now an Angel in addition to other types
  3. Flying bypasses ground blockers → guaranteed damage
  4. +2/+2 makes the creature harder to block even if opponent has flyers
**APL requirement:** When energy ≥ 3 and attacking into a board stall,
  pump the biggest attacker with Guide's ability for evasion damage.

### LINE 6: Screaming Nemesis Anti-Removal
**Situation:** Opponent wants to remove Screaming Nemesis
**Key:** ANY damage to Nemesis reflects to any target. If reflected to a player,
  that player CAN'T GAIN LIFE for the rest of the game.
**Result:**
  - Opponent Bolts Nemesis → Nemesis reflects 3 to opponent → opponent can't gain life
  - Opponent blocks with a 2/2 → Nemesis reflects 2 to opponent → can't gain life
  - Opponent MUST use exile-based removal (Solitude, Prismatic Ending, Leyline Binding)
**APL requirement:** From OPPONENT perspective: never use damage-based removal on Nemesis.
  From PILOT perspective: attack Nemesis into blockers for upside.

### LINE 7: Ocelot Pride Lifelink First Strike
**Situation:** Ocelot Pride attacks
**Key:** Ocelot has FIRST STRIKE and LIFELINK
**Result:**
  1. Ocelot deals 1 first strike damage → gains 1 life
  2. Life gained → Ocelot end step trigger active (create Cat token)
  3. If blocked by a 1/1: Ocelot kills it in first strike, takes no damage
  4. If blocked by a 2/2: Ocelot deals 1 first strike, dies in regular combat
     → But Guide already triggered the lifegain → end step Cat still happens
**APL requirement:** Ocelot is always safe to attack into X/1 creatures.
  The lifelink from combat guarantees the end step token.


## CODE-LEVEL AUDIT (Cross-referenced with APL source)

### Issue A: Phlage Escape — Summoning Sickness Wrong (line ~290)
```python
phlage.summoning_sickness = False  # WRONG — escape doesn't give haste
```
Escaped Phlage has summoning sickness. Can't attack turn it enters.
ETB still fires (3 dmg + 3 life). But NO attack that turn.
**Fix:** `phlage.summoning_sickness = True`

### Issue B: Ocelot Token Timing — Wrong Phase (line ~370)
`_simulate_end_step()` is called at end of `main_phase_match` (step 8).
But Ocelot triggers at END STEP — AFTER combat, not before.
Currently: tokens created → then attack. Should be: attack → then tokens at end step.
**Fix:** Move `_simulate_end_step` to `end_step_actions` method.

### Issue C: Voice Mobilize — Damage Double-Counted (line ~406)
```python
gs.damage_dealt += new_tokens  # BAD — bypasses combat, may double-count
```
Mobilize tokens are "tapped and attacking" — they should go through combat,
not add damage directly. If they're also counted in the combat step as
part of the attackers list, damage is counted twice.
**Fix:** Don't add damage_dealt here. Instead track tokens for end_step
Bombardment sacrifice (since tokens get sacrificed at end step anyway).

### Issue D: Ocelot Cascade in Voice Section — Oracle Wrong (line ~416)
```python
if ocelots > 0 and life_gained > 0:
    cat_tokens = ocelots * min(life_gained, 3)  # WRONG
```
Ocelot creates ONE Cat per Ocelot at end step — NOT one per lifegain event.
This creates way too many tokens.
**Fix:** Remove cascade from Voice section. Ocelot tokens only in end_step_actions.

### Issue E: respond_to_spell — No Defensive Lines (line ~487)
Current implementation only checks for Bolt on opponent creatures.
Missing:
- Sacrifice to Bombardment in response to removal targeting our creature
- Ajani defensive transform (sac Cat → Ajani exiles → fizzles removal)
- Static Prison on opponent's newly deployed threat
**Fix:** Complete rewrite of respond_to_spell with defensive interaction tree.

### Issue F: Guide Attack Pump — Completely Missing
No code for: "Whenever you attack, pay {E}{E}{E} → +2/+2 and flying counter"
This is how Boros breaks through board stalls.
**Fix:** Add to declare_attackers — check energy ≥ 3, pump best attacker.

### Issue G: Fetchland/Shockland Life — Not Modeled
Both players start at 20. Boros typically pays 4-6 life from mana base.
Real starting life: ~14-16.
**Fix:** Add to _play_land_if_able — pay 1 life for fetches, 2 for shocklands.

### Issue H: Static Prison Maintenance — Not Tracked
Static Prison costs 1{E} per turn. If energy runs dry, prison breaks.
The exiled creature returns. Currently modeled as permanent exile.
**Fix:** Track Static Prisons on board, pay energy each turn in main phase.

### Issue I: Ragavan Treasure — Not Tracked
Each Ragavan combat hit creates a Treasure (extra mana next turn).
Currently no Treasure generation.
**Fix:** In end_step_actions, count Ragavans that attacked → create Treasures.
