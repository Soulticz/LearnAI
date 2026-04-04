from pandas.io import pickle
from yfinance import ticker
import json
import os
import pickle
import pandas as pd
from datetime import datetime
from sklearn.metrics import accuracy_score
import yfinance as yf

LOG_FILE = "signal_log.json"
FEATURES = ["rsi_14", "macd_hist", "sma_20", "sma_50", "change_1d", "change_5d", "vol_ratio"]

def save_signal(ticker: str, action: str,
                price : float, features: dict):
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

    logs.append({
        "ticker": ticker,
        "action": action,
        "price": price,
        "features": features,
        "timestamp": datetime.now().isoformat(),
        "evauated": False,
        "correct": None,
    })

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2 ,ensure_ascii=False)
    print(f"[LOG] Saved signal: {action} {ticker}")

def evaluate_old_signals() -> list[dict]:
    if not os.path.exists(LOG_FILE):
        print("[EVAL] No log file found")
        return []

    with open(LOG_FILE, "r") as f:
        logs : json.load(f)
    new_training_data = []
    updated = False

    for log in logs:
        if log["evauated"]:
            continue

        signal_date = datetime.fromisoformat(log["timestamp"])
        days_passed = (datetime.now() - signal_date).days

        if days_passed < 5:
            continue
        try:
            t =yf.Ticker(log["ticker"])
            price_now = float(t.history(period="1d")["Close"].iloc[-1]
            )
            change_pct = (price_now - log["price"]) / log["price"] *100
            
            if log["action"].startswith("BUY 🟢"):
                correct = change_pct > 1.0
            elif log["action"].startswith("SELL 🔴"):
                correct = change_ptc < -1.0
            else:
                correct : True


            log["evauated"] = True
            log["correct"] = correct
            log["change_pct"]= round(change_pct, 2)
            updated = True
            

            log["evaluated"] = True
            log["correct"] = correct
            log["change_pct"] = round(change_pct, 2)
            updated = True

            print(f"{'✅' if correct else '❌'} {log['ticker']}" f"->{change_pct:+.1f}%")
            if not log["action"].startswith("🟡"):
                new_training_data.append({
                    "features": log["features"],
                    "label": 1 if correct else 0,
                })
        except Exception as e:
            print(f"ประเมิน { log['ticker']} ไม่ได้:{e}")

    if updated:
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    return new_training_date

def retrain_if_needed(new_data: list[dict]):
    if len(new_data) < 5:
        print("[TRAIN] Not enough data to retrain")
        return
    
    print(f"[TRAIN] Retraining model with {len(new_data)} new samples...")
    
    try:
        with open("training_data.pkl", "rb") as f:
            saved = pickle.load(f)
            model = saved["model"]
    
    except FileNotFoundError:
        print("[TRAIN] No model found, training new model")
        return

    new_df = pd.DataFrame([d["features"] for d in new_data])
    new_y = pd.Series([d["label"] for d in new_data])

    for col in FEATURES:
        if col not in new_df.columns:
            new_df[col] = 0.0
    new_df = new_df[FEATURES]
    
    model.set_params(warm_stat=True, n_estimators=model.n_estimators + 10)
    
    model.fit(new_df, new_y)

    y_pred = model.predict(new_df)
    acc = accuracy_score(new_y, y_pred)
    print(f"[TRAIN] New accuracy: {acc:.1%}")
    print(f"[TRAIN] Model saved")

    with open("model.pkl", "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)
    print(f"[TRAIN] Done")

   