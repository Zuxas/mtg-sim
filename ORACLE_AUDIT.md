# ORACLE TEXT AUDIT — APL Accuracy Issues
## Generated 2026-04-10

## CRITICAL ISSUES (Impact: matchup-altering)

### BOROS ENERGY APL
1. **Voice of Victory x3 — NOT MODELED**
   - Oracle: "Mobilize 2 (Whenever this creature attacks, create two tapped and attacking 1/1 red Warrior tokens)"
   - Impact: HUGE — 3 copies × 2 tokens per attack = 6 extra damage per combat
   - Fix: Add token generation on attack, feed into Goblin Bombardment + Guide of Souls triggers

2. **Goblin Bombardment — NOT MODELED**
   - Oracle: "Sacrifice a creature: This enchantment deals 1 damage to any target"
   - Impact: CRITICAL — converts all tokens (Voice, Ocelot, Ajani) into face damage
   - Fix: End-of-combat sacrifice tokens for direct damage

3. **Phlage Escape — NOT MODELED**
   - Oracle: "Escape—{1}{R}{W}, Exile five other cards from your graveyard"
   - Impact: HIGH — recurring 6/6 haste from GY, key late-game threat
   - Fix: Check GY size ≥5, escape Phlage for {1}{R}{W}

4. **Guide of Souls Energy — PARTIALLY MODELED**
   - Oracle: "Whenever another creature you control enters, you gain 1 life and get {E}"
   - Impact: MEDIUM — energy generation fuels Galvanic Discharge
   - Currently: Lifegain modeled, energy generation NOT tracked

5. **Ocelot Pride Tokens — PARTIALLY MODELED**
   - Oracle: "Whenever you gain life, create a 1/1 white Cat creature token"
   - Impact: HIGH — cascades with Guide of Souls (creature enters → gain life → Ocelot token → creature enters → gain life → ...)
   - This is the Boros value engine

### IZZET PROWESS APL
6. **DRC Delirium — NOT MODELED**
   - Oracle: "As long as 4+ card types in GY, DRC gets +2/+2, has flying, attacks each combat"
   - Impact: HIGH — DRC as 3/3 flyer is the primary threat in many games
   - Fix: Track card types in GY, upgrade DRC power/toughness

7. **Violent Urge — CARD DRAW NOT MODELED**
   - Oracle: "Target creature gets +1/+0 and gains first strike until end of turn. Draw a card."
   - Impact: MEDIUM — it's a cantrip that draws a card, adds to burst fuel
   - Fix: Add gs.zones.draw(1) when Violent Urge is cast

8. **Cori-Steel Flurry Token — PARTIALLY MODELED**
   - Oracle: "Flurry — second spell each turn → create 1/1 Monk → auto-attach Cutter"
   - The Monk gets +1/+1 trample haste from the equipment
   - Currently: Flurry trigger exists but token quality may be wrong

### JESKAI BLINK APL
9. **Phelia Blink Trigger — NOT MODELED**
   - Oracle: "Flash. Whenever Phelia attacks, exile another target nonland permanent. Return at end step"
   - Impact: HIGH — removes blockers + re-triggers ETB (Solitude, Phlage)
   - Fix: On attack, exile opponent's best creature temporarily

10. **Consign to Memory Replicate — NOT MODELED**
    - Oracle: "Replicate {1} — copy for each replicate paid"
    - Impact: LOW — usually just cast for 1 counter, replicate is expensive

### GORYOS VENGEANCE APL
11. **Goryo's Exile at End Step — NOT MODELED**
    - Oracle: "Return legendary creature... gains haste. Exile it at beginning of next end step"
    - Impact: HIGH — reanimated creature only lasts ONE turn, then exiled
    - Fix: Track that Goryo'd creature is exiled after one combat
    - This means Atraxa only gets ONE attack (draw 7 + deal 7)

12. **Psychic Frog Power Growth — NOT MODELED**
    - Oracle: "Discard a card: Psychic Frog gets +1/+1 until end of turn"
    - Impact: MEDIUM — Frog is not just a discard outlet, it's a scalable threat
    - Fix: Model discard → pump, track power growth

### ELDRAZI TRON APL
13. **Karn Wishboard — NOT MODELED**
    - Oracle: "-2: Choose an artifact card you own from outside the game, reveal it, put into hand"
    - Impact: HIGH — tutors Chalice, Bridge, Cage from sideboard
    - Fix: Add SB artifact lookup on Karn activation

## MEDIUM ISSUES

### ALL APLs
14. **Fetchland Life Loss — NOT MODELED**
    - All fetchlands pay 1 life on activation
    - Impact: MEDIUM — Boros/Prowess/Jeskai each pay 3-5 life from fetches
    - This is why Boros starts games at 16-17 life, not 20

15. **Shockland Life Loss — NOT MODELED**
    - Sacred Foundry, Steam Vents etc. pay 2 life if entering untapped
    - Impact: MEDIUM — another 2-4 life loss per game

## LOW ISSUES
- Seasoned Pyromancer discard/draw + token creation
- Static Prison exile timing
- Ajani flip trigger (transform at 3+ creatures)
