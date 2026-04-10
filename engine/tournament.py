"""
engine/tournament.py — Swiss tournament simulator

Simulates an actual RC-style Swiss event using Bo3 matchup data.
Answers: "What's my expected record with deck X at the RC?"

Uses metagame shares to populate the field, then runs Swiss pairings
where players with the same record get paired each round.
"""
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Player:
    deck: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    opponent_ids: list = field(default_factory=list)  # store id() not objects
    
    @property
    def points(self): return self.wins * 3 + self.draws
    @property
    def record(self): return f"{self.wins}-{self.losses}"


@dataclass 
class TournamentResult:
    deck: str
    avg_wins: float
    avg_losses: float
    top8_pct: float
    x0_pct: float  # undefeated
    x1_pct: float  # 1 loss
    x2_pct: float  # 2 loss (bubble)
    n_events: int


def build_field(field_shares: dict, n_players: int, rng: random.Random) -> list[Player]:
    """Build a tournament field based on metagame shares."""
    players = []
    # Distribute decks by share
    for deck, share in sorted(field_shares.items(), key=lambda x: -x[1]):
        count = max(1, round(share * n_players))
        for _ in range(count):
            if len(players) < n_players:
                players.append(Player(deck=deck))
    # Fill remaining slots with random decks weighted by share
    decks = list(field_shares.keys())
    weights = [field_shares[d] for d in decks]
    while len(players) < n_players:
        deck = rng.choices(decks, weights=weights, k=1)[0]
        players.append(Player(deck=deck))
    rng.shuffle(players)
    return players[:n_players]


def swiss_pair(players: list[Player], rng: random.Random) -> list[tuple[Player, Player]]:
    """Pair players with same record (Swiss-style). Leftover gets bye."""
    # Group by points
    groups = {}
    for p in players:
        groups.setdefault(p.points, []).append(p)
    
    pairs = []
    floaters = []
    
    for pts in sorted(groups.keys(), reverse=True):
        pool = floaters + groups[pts]
        rng.shuffle(pool)
        floaters = []
        
        while len(pool) >= 2:
            p1 = pool.pop(0)
            # Find opponent not previously played
            found = False
            for i, p2 in enumerate(pool):
                if id(p2) not in p1.opponent_ids:
                    pool.pop(i)
                    pairs.append((p1, p2))
                    found = True
                    break
            if not found and pool:
                p2 = pool.pop(0)
                pairs.append((p1, p2))
        
        if pool:
            floaters.extend(pool)
    
    # Bye for leftover
    for p in floaters:
        p.wins += 1  # bye = free win
    
    return pairs


def resolve_match(p1: Player, p2: Player, matrix: dict, rng: random.Random):
    """Resolve a match using the Bo3 matchup matrix."""
    wr = matrix.get((p1.deck, p2.deck), 50.0)
    if rng.random() * 100 < wr:
        p1.wins += 1; p2.losses += 1
    else:
        p2.wins += 1; p1.losses += 1
    p1.opponent_ids.append(id(p2))
    p2.opponent_ids.append(id(p1))


def run_tournament(field_shares: dict, matrix: dict, 
                   n_players: int = 200, n_rounds: int = 8,
                   seed: int = 42) -> list[Player]:
    """Run one Swiss tournament. Returns final standings."""
    rng = random.Random(seed)
    players = build_field(field_shares, n_players, rng)
    
    for rd in range(n_rounds):
        pairs = swiss_pair(players, rng)
        for p1, p2 in pairs:
            resolve_match(p1, p2, matrix, rng)
    
    players.sort(key=lambda p: (-p.points, -p.wins))
    return players


def simulate_rc(field_shares: dict, matrix: dict,
                n_events: int = 1000, n_players: int = 200,
                n_rounds: int = 8, seed: int = 42) -> list[TournamentResult]:
    """Simulate many RCs and compute expected records per deck."""
    rng = random.Random(seed)
    
    # Track per-deck results
    deck_results = {}  # deck -> list of (wins, losses)
    
    for event in range(n_events):
        standings = run_tournament(field_shares, matrix, n_players, n_rounds,
                                   seed=rng.randint(0, 999_999))
        for p in standings:
            deck_results.setdefault(p.deck, []).append((p.wins, p.losses))
    
    # Compute stats
    results = []
    for deck in sorted(field_shares.keys(), key=lambda d: -field_shares[d]):
        records = deck_results.get(deck, [])
        if not records: continue
        n = len(records)
        avg_w = sum(w for w, _ in records) / n
        avg_l = sum(l for _, l in records) / n
        x0 = sum(1 for w, l in records if l == 0) / n * 100
        x1 = sum(1 for w, l in records if l <= 1) / n * 100
        x2 = sum(1 for w, l in records if l <= 2) / n * 100
        # Top 8 = top 4% of field (8/200)
        top8 = sum(1 for w, l in records if w >= n_rounds - 1) / n * 100
        results.append(TournamentResult(
            deck=deck, avg_wins=round(avg_w, 1), avg_losses=round(avg_l, 1),
            top8_pct=round(top8, 1), x0_pct=round(x0, 1),
            x1_pct=round(x1, 1), x2_pct=round(x2, 1), n_events=n
        ))
    
    results.sort(key=lambda r: -r.top8_pct)
    return results


def print_rc_report(results: list[TournamentResult]):
    print(f"\n{'='*75}")
    print(f"  RC TOURNAMENT SIMULATION — Expected Records")
    print(f"{'='*75}")
    print(f"  {'Deck':<25} {'Avg Record':>10} {'Top8%':>6} {'X-0':>5} {'X-1':>5} {'X-2':>5}  {'N':>5}")
    print(f"  {'-'*25} {'-'*10} {'-'*6} {'-'*5} {'-'*5} {'-'*5}  {'-'*5}")
    for r in results:
        rec = f"{r.avg_wins:.1f}-{r.avg_losses:.1f}"
        print(f"  {r.deck:<25} {rec:>10} {r.top8_pct:>5.1f}% {r.x0_pct:>4.1f}% {r.x1_pct:>4.1f}% {r.x2_pct:>4.1f}%  {r.n_events:>5}")
