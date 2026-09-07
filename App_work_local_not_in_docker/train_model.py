"""
train_model.py
Trains a tiny dummy "image classifier" so the lab is self-contained
(no real dataset needed). Run this locally before starting the app.
"""
import os

import numpy as np
from sklearn.linear_model import LogisticRegression
import joblib

os.makedirs("models", exist_ok=True)

# Fake training data: 64 "pixel-ish" features -> 2 classes (cat=0, dog=1)
rng = np.random.default_rng(42)
X = rng.random((200, 64))
y = (X.mean(axis=1) > 0.5).astype(int)

clf = LogisticRegression()
clf.fit(X, y)

joblib.dump(clf, "models/image_classifier.pkl")
print("Model trained and saved to models/image_classifier.pkl")
