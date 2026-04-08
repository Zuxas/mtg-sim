"""
ml/win_prob_model.py — Train a win probability model from sim game data

Replaces the goldfish race heuristic with a learned model.
Data: run 10k+ games → (features, outcome) pairs → train GBM or NN

Features per game:
  - avg_kill_turn (our kill speed)
  - opponent archetype encoding
  - (extended: board state features per turn once game_log is wired in)

This is supervised learning on sim-generated data.
No human labeling needed — the sim generates perfect ground truth.
"""

import json, os, pickle
import numpy as np


ARCHETYPE_ENCODING = {
    "dimir reanimator": 0, "lotus combo": 1, "dimir tempo": 2,
    "cephalid breakfast": 3, "eldrazi stompy": 4, "sneak and show": 5,
    "mono red painter": 6, "doomsday": 7, "izzet delver": 8,
    "death and taxes": 9, "bant nadu": 10, "four-color": 11,
    "jeskai control": 12, "mono red aggro": 13, "mono red prison": 14,
    "unknown": 15,
}
N_ARCHETYPES = len(ARCHETYPE_ENCODING)


def collect_training_data(n_games=10000, seed=42,
                          save_path="data/win_prob_training.json"):
    from data.deck import load_deck_from_file
    from apl.humans import HumansAPL
    from engine.runner import run_simulation
    from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn
    import random

    main_deck, _ = load_deck_from_file("decks/humans_legacy.txt")
    archetypes   = list(ARCHETYPE_ENCODING.keys())[:-1]  # skip unknown
    games_each   = max(1, n_games // len(archetypes))
    X, y = [], []
    rng  = random.Random(seed)

    print(f"Collecting {n_games} games across {len(archetypes)} archetypes...")
    for arch in archetypes:
        apl = HumansAPL()
        try:
            apl.set_opponent(arch, on_play=True)
        except Exception:
            pass

        sim      = run_simulation(apl, main_deck, n=games_each, on_play=True, seed=seed)
        arch_enc = ARCHETYPE_ENCODING.get(arch, 15)

        # Get opponent kill distribution
        opp_key  = _infer_archetype_key(arch)
        opp_dist = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"])
        opp_turns = sorted(opp_dist.keys())
        opp_weights = [opp_dist[t] for t in opp_turns]
        opp_total = sum(opp_weights)

        wins = 0
        for our_kill in sim.kill_turns:
            # Sample opponent kill turn from their distribution
            r = rng.random() * opp_total
            cumul = 0
            opp_kill = opp_turns[-1]
            for t, w in zip(opp_turns, opp_weights):
                cumul += w
                if r <= cumul:
                    opp_kill = t
                    break

            # We win if we kill before them (on play = we go first)
            won = 1 if our_kill <= opp_kill else 0
            wins += won
            X.append([our_kill, opp_kill, arch_enc])
            y.append(won)

        wr = wins / len(sim.kill_turns) * 100
        print(f"  {arch:<30} {games_each}g  win%={wr:.1f}%")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w') as f:
        json.dump({"X": X, "y": y}, f)
    print(f"\nSaved {len(X)} samples to {save_path}")
    return X, y


def train_model(X, y, model_type="gbm"):
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score
    except ImportError:
        print("Install: pip install scikit-learn --break-system-packages")
        return None

    Xa = np.array(X, dtype=float)
    ya = np.array(y, dtype=int)
    Xtr, Xte, ytr, yte = train_test_split(Xa, ya, test_size=0.2, random_state=42)

    if model_type == "gbm":
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(n_estimators=200, max_depth=4,
                                           learning_rate=0.1, random_state=42)
    else:
        from sklearn.neural_network import MLPClassifier
        model = MLPClassifier(hidden_layer_sizes=(64, 32, 16),
                              activation='relu', max_iter=500, random_state=42)

    model.fit(Xtr, ytr)
    yp = model.predict(Xte)
    yprob = model.predict_proba(Xte)[:, 1]

    print(f"\nModel ({model_type}):  accuracy={accuracy_score(yte,yp):.3f}  "
          f"AUC={roc_auc_score(yte,yprob):.3f}  "
          f"train={len(Xtr):,}  test={len(Xte):,}")
    return model


def save_model(model, path="data/win_prob_model.pkl"):
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Saved to {path}")


def load_model(path="data/win_prob_model.pkl"):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return pickle.load(f)


def predict_win_prob(our_kill_dist, opp_archetype, model=None):
    """Predict win% — uses ML model if available, falls back to race."""
    if model is None:
        model = load_model()
    if model is None:
        from sim_bridge import race_win_pct, ARCHETYPE_CLOCKS, _infer_archetype_key
        key = _infer_archetype_key(opp_archetype)
        return race_win_pct(our_kill_dist,
                            ARCHETYPE_CLOCKS.get(key, ARCHETYPE_CLOCKS["unknown"]),
                            n=20000)
    from sim_bridge import avg_kill_turn, ARCHETYPE_CLOCKS, _infer_archetype_key
    our_avg  = avg_kill_turn(our_kill_dist)
    opp_key  = _infer_archetype_key(opp_archetype)
    opp_dist = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"])
    opp_avg  = avg_kill_turn(opp_dist)
    enc      = ARCHETYPE_ENCODING.get(opp_archetype.lower(), 15)
    feat     = np.array([[our_avg, opp_avg, enc]])
    prob     = model.predict_proba(feat)[0][1]
    return round(prob * 100, 1)


if __name__ == "__main__":
    import argparse, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--train",   action="store_true")
    ap.add_argument("--games",   type=int, default=10000)
    ap.add_argument("--model",   default="gbm")
    args = ap.parse_args()

    if args.collect:
        collect_training_data(n_games=args.games)
    elif args.train:
        if not os.path.exists("data/win_prob_training.json"):
            print("Run --collect first"); exit(1)
        with open("data/win_prob_training.json") as f:
            data = json.load(f)
        m = train_model(data["X"], data["y"], args.model)
        if m:
            save_model(m)
