"""Game-level matchup matrix for PT SOS 2026.

Builds match WR and game WR per archetype matchup using round-by-round
score data in data/pt_sos_2026.json. Game WR exposes how "tight" or
"blown out" a matchup actually is -- a deck might lose 33% of matches
but win 48% of games (close losses) vs lose 25% / win 30% (blowouts).

Usage:
  python scripts/ptsos_game_level_matrix.py [--archetype 'Izzet Prowess']
"""
import json
import sys
import argparse
from collections import defaultdict


def normalize(name):
    if not name:
        return ''
    name = name.lower().strip()
    if ',' in name:
        parts = name.split(',')
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ''
        return f'{first} {last}'.strip()
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archetype', help='Filter to matchups involving this archetype')
    ap.add_argument('--top', type=int, default=20, help='Show top N by match count')
    args = ap.parse_args()

    with open('data/pt_sos_2026.json') as f:
        d = json.load(f)

    # Build normalized player -> archetype lookup
    players = d.get('player_archetypes', {})
    norm_lookup = {}
    for k, v in players.items():
        a = v.get('archetype') if isinstance(v, dict) else v
        norm_lookup[normalize(k)] = a

    # Score format: 2-0, 2-1, 1-2, 0-2 (from p1 perspective)
    rounds = d.get('rounds', {})
    mu_scores = defaultdict(lambda: defaultdict(int))
    matched = 0
    total = 0
    for round_num, matches in rounds.items():
        for m in matches:
            total += 1
            a1 = norm_lookup.get(normalize(m.get('p1', '')))
            a2 = norm_lookup.get(normalize(m.get('p2', '')))
            if not a1 or not a2:
                continue
            matched += 1
            winner = m.get('winner')
            score = m.get('score', '')
            if winner == 'p1':
                mu_scores[(a1, a2)][score] += 1
            elif winner == 'p2':
                parts = score.split('-')
                if len(parts) == 2:
                    inv = f'{parts[1]}-{parts[0]}'
                    mu_scores[(a1, a2)][inv] += 1

    print(f'Matched: {matched}/{total} matches ({matched/total*100:.0f}%)')
    print()

    rows = list(mu_scores.items())
    if args.archetype:
        rows = [r for r in rows if args.archetype in r[0]]
    rows.sort(key=lambda x: -sum(x[1].values()))
    rows = rows[:args.top]

    print(f'{"Matchup":<48}  {"Total":<5} {"2-0":<5} {"2-1":<5} {"1-2":<5} {"0-2":<5}  {"Match%":<7} {"Game%":<7} {"Tightness":<10}')
    print('-' * 120)
    for (a1, a2), scores in rows:
        total_m = sum(scores.values())
        a1_wins = scores.get('2-0', 0) + scores.get('2-1', 0)
        a1_match_wr = a1_wins / total_m * 100 if total_m else 0
        a1_games = scores.get('2-0', 0)*2 + scores.get('2-1', 0)*2 + scores.get('1-2', 0)*1
        a2_games = scores.get('2-1', 0)*1 + scores.get('1-2', 0)*2 + scores.get('0-2', 0)*2
        total_games = a1_games + a2_games
        a1_game_wr = a1_games / total_games * 100 if total_games else 0
        # Tightness: |game_wr - 50| -- low means matchup is close at game level
        # If match% is far from 50 but game% is near 50 -> "close losses" (the deck does something right)
        tightness = abs(a1_game_wr - 50)
        gap = a1_match_wr - a1_game_wr
        tag = ''
        if abs(gap) > 10 and tightness < 15:
            if gap > 0:
                tag = 'SWINGY (wins decisive matches)'
            else:
                tag = 'CLOSE LOSER (does something right)'
        elif tightness > 25:
            tag = 'BLOWOUT'
        print(f'  {a1[:23]:<24} vs {a2[:23]:<24}  {total_m:<5} {scores.get("2-0",0):<5} {scores.get("2-1",0):<5} {scores.get("1-2",0):<5} {scores.get("0-2",0):<5}  {a1_match_wr:>5.1f}%  {a1_game_wr:>5.1f}%  {tag}')


if __name__ == '__main__':
    main()
