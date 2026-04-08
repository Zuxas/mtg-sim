"""Step 2: Run RL training loop - 3 iterations of epsilon-greedy exploration."""
import sys
sys.path.insert(0, r'E:\vscode ai project\mtg-sim')
from ml.rl_trainer import rl_training_loop

rl_training_loop(
    n_iterations=3,
    games_per_iter=3000,
    epsilon_start=0.25,
    epsilon_end=0.10,
    model_path='data/win_prob_model_v3.pkl',
    data_path='data/win_prob_training_v3.json',
    seed=100,
)
