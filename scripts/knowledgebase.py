import os
import glob
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor

BASE_DIR = '/Users/sudiptogoldfish/code files/7059B A_AI Lab/Chatbot/train service data/'
MODEL_PATH = os.path.join(BASE_DIR, 'delay_model.pkl')

class DelayModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
        else:
            self.train()

    def train(self):
        X, y = [], []
        files = glob.glob(os.path.join(BASE_DIR, '*.xlsx'))
        for f in files:
            try:
                df = pd.read_excel(f, engine='openpyxl')
                df['p'] = pd.to_datetime(df['planned_arrival_time'], format='%H:%M:%S', errors='coerce')
                df['a'] = pd.to_datetime(df['actual_arrival_time'], format='%H:%M:%S', errors='coerce')
                df['delay'] = (df['a'] - df['p']).dt.total_seconds() / 60.0
                df = df.dropna(subset=['delay', 'rid'])
                for _, g in df.groupby('rid'):
                    if len(g) < 2: continue
                    g = g.sort_values('p')
                    final_delay = g.iloc[-1]['delay']
                    for i in range(len(g) - 1):
                        X.append([g.iloc[i]['delay'], len(g) - i - 1, i])
                        y.append(final_delay)
            except Exception: continue
        if X: self.model.fit(np.array(X), np.array(y))
        else: self.model.fit([[0, 0, 0], [10, 2, 1], [20, 3, 2]], [0, 8, 15])
        try:
            with open(MODEL_PATH, 'wb') as f: pickle.dump(self.model, f)
        except Exception: pass

    def predict(self, d, stops=3, pos=1):
        pred = self.model.predict([[d, stops, pos]])
        return max(0, int(round(pred[0])))

predictor = DelayModel()