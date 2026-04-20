# JESKAI BLINK — APL AUDIT NOTES (PRELIMINARY)
# Source: <your-playbook-dir>\modern\jeskai-blink-playbook.html

## CURRENT APL STATUS: 286 lines, basic deployment + removal only

## CRITICAL MISSING MECHANICS:

### 1. Phelia Attack Blink Loop (P0 — defines the deck)
Oracle: "Whenever Phelia attacks, exile target nonland permanent you control.
Return it at the beginning of the next end step."
**Impact:** FREE ETB trigger every attack. Blinks Solitude (re-exile), Phlage (3 dmg + 3 life),
Quantum Riddler, Casey Jones. This is the PRIMARY value engine.
**Current APL:** Phelia attacks as a vanilla 2/2. No blink logic.

### 2. Solitude Pitch/Evoke (P0 — free removal)
Oracle: "Evoke — exile a white card from your hand. ETB: exile target creature."
When evoked: pay 0 mana, exile a white card from hand → exile target creature → Solitude dies.
Ephemerate on evoked Solitude: Solitude re-enters → exile ANOTHER creature → Solitude stays.
**Current APL:** Solitude is in REMOVAL set but only used as generic removal.

### 3. Ephemerate Rebound (P1 — doubles all blink value)
Oracle: "Exile target creature you control, then return it. Rebound."
Rebound: cast again for free at beginning of next upkeep.
**Impact:** 1 mana = 2 blink triggers across 2 turns.
**Current APL:** Ephemerate only targets Solitude, no Rebound.

### 4. Phlage Escape from GY (P1 — recurring threat)
Oracle: "Escape {R}{R}{W}{W}, exile 5 others from GY"
Same as Boros APL. Escaped Phlage STAYS as 6/6.
**Current APL:** Only hardcast Phlage, no escape from GY.

### 5. Consign to Memory — Counter Triggered Abilities (P2)
Oracle: "{U}, counter target triggered ability. Replicate {1}."
Counters: Archon ETB, Snapcaster ETB, Summoner's Pact trigger.
**Current APL:** Listed in REMOVAL set but no counter logic.

### 6. Quantum Riddler + Casey Jones — Oracle text needed
Need Scryfall verification for exact abilities.

## NEXT SESSION: Full rewrite following playbook engines as APL architecture.
