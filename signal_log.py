import json
import os
import pickle
import pandas as pd
from datetime import datetime
from sklearn.metrics import accuracy_score
import yfinance as yf

LOG_FILE = "signal_log.json"
FEATURES = ["rsi_14", "macd_hist", "sma_20", "sma_50", "change_1d", "change_5d", "vol_ratio"]

def save_signal(ticker: str, action: str, price: float, features: dict):
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            logs = []

    logs.append({
        "ticker": ticker,
        "action": action,
        "price": price,
        "features": features,
        "timestamp": datetime.now().isoformat(),
        "evaluated": False, # แก้คำผิดจาก evauated
        "correct": None,
    })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[LOG] Saved signal: {action} {ticker}")

def evaluate_old_signals() -> list[dict]:
    """ แก้ชื่อให้ตรงกับที่ stock_bot.py เรียกใช้ """
    if not os.path.exists(LOG_FILE):
        print("[EVAL] No log file found")
        return []

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f) # แก้จาก : เป็น =
    except:
        return []

    new_training_data = []
    updated = False

    for log in logs:
        # เช็กทั้งคำผิดเก่าและคำถูกใหม่เพื่อความชัวร์
        if log.get("evaluated") or log.get("evauated"):
            continue

        signal_date = datetime.fromisoformat(log["timestamp"])
        days_passed = (datetime.now() - signal_date).days

        # รอ 5 วันค่อยประเมินผล (นายจะปรับเป็น 1 วันก่อนเพื่อเทสก็ได้นะ)
        if days_passed < 5:
            continue

        try:
            t = yf.Ticker(log["ticker"])
            hist = t.history(period="1d")
            if hist.empty: continue
            
            price_now = float(hist["Close"].iloc[-1])
            change_pct = (price_now - log["price"]) / log["price"] * 100
            
            # เช็กจากคำภาษาไทยที่ส่งมาจาก stock_bot.py
            if "ซื้อ" in log["action"]:
                correct = change_pct > 1.0
            elif "ขาย" in log["action"]:
                correct = change_pct < -1.0
            else:
                correct = True

            log["evaluated"] = True
            log["correct"] = correct
            log["change_pct"] = round(change_pct, 2)
            updated = True

            print(f"{'✅' if correct else '❌'} {log['ticker']} -> {change_pct:+.1f}%")
            
            if "ถือ" not in log["action"]:
                new_training_data.append({
                    "features": log["features"],
                    "label": 1 if correct else 0,
                })
        except Exception as e:
            print(f"ประเมิน {log['ticker']} ไม่ได้: {e}")

    if updated:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    return new_training_data # แก้ชื่อตัวแปรจาก date เป็น data

def retrain_if_needed(new_data: list[dict]):
    if len(new_data) < 5:
        print("[TRAIN] Not enough data to retrain (Need 5 samples)")
        return
    
    print(f"[TRAIN] Retraining model with {len(new_data)} new samples...")
    
    try:
        # พยายามโหลดโมเดลเดิมมา Train ต่อ
        model_path = "model.pkl"
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                saved = pickle.load(f)
                model = saved["model"]
        else:
            print("[TRAIN] No model.pkl found to retrain")
            return

        new_df = pd.DataFrame([d["features"] for d in new_data])
        new_y = pd.Series([d["label"] for d in new_data])

        # อุดช่องโหว่เรื่อง Column หาย
        for col in FEATURES:
            if col not in new_df.columns:
                new_df[col] = 0.0
        new_df = new_df[FEATURES]
        
        # ฝึกฝนเพิ่ม (Incremental Learning)
        model.fit(new_df, new_y)

        y_pred = model.predict(new_df)
        acc = accuracy_score(new_y, y_pred)
        print(f"[TRAIN] New accuracy on fresh data: {acc:.1%}")

        with open(model_path, "wb") as f:
            pickle.dump({"model": model, "features": FEATURES}, f)
        print(f"[TRAIN] Model updated and saved")
        
    except Exception as e:
        print(f"[TRAIN] Error: {e}")