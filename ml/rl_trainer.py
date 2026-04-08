"""
ml/rl_trainer.py — Reinforcement learning via epsilon-greedy self-play

Trains the win probability model by having the agent explore non-obvious
action orderings and learn from outcomes.

Algorithm: epsilon-greedy Q-learning
  - epsilon% of the time: pick a random action (explore)
  - (1-epsilon)% of the time: pick highest P(win) action (exploit)
  - After each game: record (state, action, outcome)
  - Retrain model on accumulated experience

After enough iterations the model discovers orderings the static
priority list never tried — e.g. Guide before Champion into Reanimator.

Usage:
    python ml/rl_trainer.py --iterations 5 --games-per-iter 5000
    python ml/rl_trainer.py --iterations 20 --games-per-iter 10000 --epsilon 0.25
"""

import sys, os, json, random, pickle, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np


def run_exploration_game(apl_class, main_deck, arch, opp_dist,
                          evaluator, epsilon, rng):
    """
    Run one game with epsilon-greedy exploration.
    Returns (snapshots, won) where snapshots is a list of
    (pre_action_snap, card_played, post_action_snap) tuples.
    """
    from engine.game_events import reset_event_bus
    reset_event_bus()

    apl = apl_class()
    apl.set_opponent(arch)

    # Monkey-patch pick_best to do epsilon-greedy
    original_pick_best = evaluator.pick_best

    experience = []   # (snap_before, card_chosen, snap_after) per action

    def epsilon_greedy_pick(gs, candidates):
        if not candidates:
            return None
        snap_before = gs.snapshot() if hasattr(gs, 'snapshot') else {}
        if rng.random() < epsilon:
            chosen = rng.choice(candidates)   # explore
        else:
            chosen = original_pick_best(gs, candidates)  # exploit
        experience.append((snap_before, getattr(chosen, 'name', ''), chosen))
        return chosen

    evaluator.pick_best = epsilon_greedy_pick
    apl._evaluator = evaluator

    result = apl.run_game(main_deck, on_play=True, verbose=False)

    evaluator.pick_best = original_pick_best  # restore

    # Sample opponent kill turn
    opp_turns   = sorted(opp_dist.keys())
    opp_weights = [opp_dist[t] for t in opp_turns]
    opp_total   = sum(opp_weights)
    r = rng.random() * opp_total
    cumul, opp_kill = 0, opp_turns[-1]
    for t, w in zip(opp_turns, opp_weights):
        cumul += w
        if r <= cumul:
            opp_kill = t
            break

    won = 1 if result.kill_turn > 0 and result.kill_turn <= opp_kill else 0
    return experience, won, result.turn_snapshots


def collect_rl_experience(n_games=5000, epsilon=0.20, archetypes=None, seed=42):
    """
    Collect experience with exploration. Returns (X, y) training pairs.
    """
    from data.deck import load_deck_from_file
    from apl.humans import HumansAPL
    from ml.win_prob_model import (load_model, ARCHETYPE_ENCODING,
                                    SNAPSHOT_KEYS, snapshot_to_features)
    from engine.action_evaluator import ActionEvaluator
    from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn

    main_deck, _ = load_deck_from_file("decks/humans_legacy.txt")
    model = load_model()
    rng   = random.Random(seed)

    if archetypes is None:
        archetypes = [k for k in ARCHETYPE_ENCODING if k != "unknown"]

    games_each = max(1, n_games // len(archetypes))
    X, y = [], []

    print(f"RL exploration: {n_games} games, epsilon={epsilon:.0%}, "
          f"{len(archetypes)} archetypes")

    for arch in archetypes:
        opp_key  = _infer_archetype_key(arch)
        opp_dist = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"])
        opp_avg  = avg_kill_turn(opp_dist)
        arch_enc = ARCHETYPE_ENCODING.get(arch, 15)

        if model:
            evaluator = ActionEvaluator(model, arch)
        else:
            evaluator = None

        wins = 0
        for _ in range(games_each):
            if evaluator:
                exp, won, snaps = run_exploration_game(
                    HumansAPL, main_deck, arch, opp_dist,
                    evaluator, epsilon, rng
                )
            else:
                from engine.runner import run_simulation
                apl = HumansAPL()
                sim = run_simulation(apl, main_deck, n=1,
                                     on_play=True, seed=rng.randint(0, 99999),
                                     save_logs=True)
                snaps = sim.game_logs[0].turn_snapshots if sim.game_logs else []
                won = 1 if sim.won_games > 0 else 0

            wins += won
            for snap in snaps:
                feat = snapshot_to_features(snap, arch_enc, opp_avg)
                X.append(feat)
                y.append(won)

        wr = wins / games_each * 100
        print(f"  {arch:<30} {games_each}g  win%={wr:.1f}%  "
              f"samples={len(X):,}")

    print(f"\nTotal RL samples: {len(X):,}  (win rate: {sum(y)/len(y)*100:.1f}%)")
    return X, y


def rl_training_loop(
    n_iterations:    int   = 5,
    games_per_iter:  int   = 5000,
    epsilon_start:   float = 0.25,
    epsilon_end:     float = 0.05,
    model_path:      str   = "data/win_prob_model_v2.pkl",
    data_path:       str   = "data/win_prob_training_v2.json",
    seed:            int   = 42,
):
    """
    Full RL training loop:
      1. Collect games with epsilon-greedy exploration
      2. Combine with existing training data
      3. Retrain model
      4. Repeat with decaying epsilon

    After N iterations the model has seen diverse action orderings
    and can guide the APL better than the static priority list.
    """
    from ml.win_prob_model import train_model, save_model, load_model

    # Load existing training data
    if os.path.exists(data_path):
        with open(data_path) as f:
            existing = json.load(f)
        X_base = existing["X"]
        y_base = existing["y"]
        print(f"Loaded {len(X_base):,} existing samples")
    else:
        X_base, y_base = [], []
        print("No existing data — starting fresh")

    model = load_model(model_path)

    for iteration in range(n_iterations):
        # Decay epsilon: start aggressive, end conservative
        t = iteration / max(1, n_iterations - 1)
        epsilon = epsilon_start + t * (epsilon_end - epsilon_start)

        print(f"\n{'='*60}")
        print(f"RL Iteration {iteration+1}/{n_iterations}  "
              f"epsilon={epsilon:.0%}")
        print(f"{'='*60}")

        # Collect new experience
        X_new, y_new = collect_rl_experience(
            n_games=games_per_iter,
            epsilon=epsilon,
            seed=seed + iteration,
        )

        # Combine: new experience + sample from existing (avoid bias)
        if X_base:
            # Sample existing data proportionally
            sample_size = min(len(X_base), len(X_new) * 3)
            indices = random.sample(range(len(X_base)), sample_size)
            X_combined = [X_base[i] for i in indices] + X_new
            y_combined = [y_base[i] for i in indices] + y_new
        else:
            X_combined = X_new
            y_combined = y_new

        print(f"\nTraining on {len(X_combined):,} samples "
              f"({len(X_new):,} new + {len(X_combined)-len(X_new):,} existing)...")
        model = train_model(X_combined, y_combined, model_type="gbm")

        if model:
            save_model(model, model_path)
            X_base.extend(X_new)
            y_base.extend(y_new)
            # Save updated dataset
            with open(data_path, 'w') as f:
                json.dump({"X": X_base, "y": y_base,
                           "feature_dim": len(X_base[0]) if X_base else 0}, f)
            print(f"Dataset grown to {len(X_base):,} total samples")

    print(f"\nRL training complete. Model saved to {model_path}")
    return model


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations",     type=int,   default=5)
    ap.add_argument("--games-per-iter", type=int,   default=5000)
    ap.add_argument("--epsilon-start",  type=float, default=0.25)
    ap.add_argument("--epsilon-end",    type=float, default=0.05)
    ap.add_argument("--seed",           type=int,   default=42)
    args = ap.parse_args()

    rl_training_loop(
        n_iterations=args.iterations,
        games_per_iter=args.games_per_iter,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        seed=args.seed,
    )
