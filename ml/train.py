import sys, json
sys.path.insert(0, '.')
from ml.win_prob_model import train_model, save_model

with open('data/win_prob_training_v2.json') as f:
    d = json.load(f)

print(f"Samples: {len(d['X']):,}  Features: {len(d['X'][0])}")
m = train_model(d['X'], d['y'], model_type='gbm')
if m:
    save_model(m)
