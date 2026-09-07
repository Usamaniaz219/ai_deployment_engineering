"""
app.py
A tiny "AI" image-classification API, built with FastAPI.
- Loads a pre-trained scikit-learn model with joblib
- Uses OpenCV to decode/resize incoming images
- Uses an APP_SECRET_KEY from the environment for request signing
"""
import os

import cv2
import numpy as np
import joblib
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables (if present)

APP_SECRET_KEY = os.environ["APP_SECRET_KEY"]  # raises KeyError if not set

app = FastAPI()

MODEL_PATH = "models/image_classifier.pkl"
print(f"[startup] loading model from {MODEL_PATH}")
model = joblib.load(MODEL_PATH)
print("[startup] model loaded successfully")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(request: Request):
    body = await request.body()
    file_bytes = np.frombuffer(body, dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="could not decode image")

    img = cv2.resize(img, (8, 8))
    features = img.flatten().astype("float32") / 255.0
    features = features[:64].reshape(1, -1)

    pred = model.predict(features)[0]
    label = "dog" if pred == 1 else "cat"
    return {"prediction": label}


if __name__ == "__main__":
    print("[startup] starting FastAPI app on 127.0.0.1:5000")
    uvicorn.run(app, host="127.0.0.1", port=5000)
