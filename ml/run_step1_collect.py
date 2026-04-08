"""Step 1: Collect v3 training data with richer features."""
import sys, json
sys.path.insert(0, r'E:\vscode ai project\mtg-sim')
from ml.win_prob_model import collect_training_data, train_model, save_model

print('=== Collecting v3 training data (20k games, richer features) ===')
X, y = collect_training_data(n_games=20000, save_path='data/win_prob_training_v3.json')

print('\n=== Training GBM on v3 data ===')
m = train_model(X, y, model_type='gbm')
if m:
    save_model(m, 'data/win_prob_model_v3.pkl')
    print('DONE: data/win_prob_model_v3.pkl')
