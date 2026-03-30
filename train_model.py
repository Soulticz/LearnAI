import yfinance as yf
import pandas as pd 
import ta as ta_lib
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

TICKER = ["^GSPC","GC=F","BTC-USD","NVDA"]

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    close  = df["close"]
    volume = df["volume"]

    df["rsi"] = ta_lib.momentum.RSIIndicator(close,window=14).rsi()

    macd_obj        = ta_lib.trend.MACD(close)
    df["macd"]      = macd_obj.macd()
    df["macd_hist"]   = macd_obj.macd_diff()
    
    df["sma_20"] = ta_lib.trend.SMAIndicator(close,window=20).sma_indicator()
    df["sma_50"] = ta_lib.trend.SMAIndicator(close,window=50).sma_indicator()

    bb = ta_lib.volatility.BollingerBands(close, window=20)
    df["bb_upper"] =  bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    df["change_1d"] = close.pct_change(1)
    df["change_5d"] = close.pct_change(5)
    df["vol_ratio"] = volume / volume.rolling(20).mean()

    # Label - ราคา 5 วันข้างหน้าขึ้น 1% ไหม
    df["label"] = (close.shift(-5)> close *1.01).astype(int)

    return df

FEATURES = ["rsi","macd","macd_hist","sma_20","sma_50","bb_upper","bb_lower","change_1d","change_5d","vol_ratio"]

def train():
     all_data = []

     for ticker in TICKER:
        print(f"ดึงข้อมูล {ticker}...")
        df = yf.download(ticker, period="5y", progress=False)
        if isinstance(df.columns,pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()
        df.columns = df.columns.str.lower()
        df = build_features(df)
        df["ticker"] = ticker  # บอก model ว่าข้อมูลมาจากหุ้นไหน
        all_data.append(df)

         # รวมข้อมูลทุกตัวเข้าด้วยกัน
     combined_df = pd.concat(all_data).dropna()

     x = combined_df[FEATURES]
     y = combined_df["label"]
          # แบ่ง train/test ตามเวลา ห้าม shuffle!
     split   = int(len(x) * 0.8)
     x_train = x.iloc[:split]
     x_test  = x.iloc[split:]
     y_train = y.iloc[:split]
     y_test  = y.iloc[split:]

     print(f"Train : {len(x_train)} วัน | Test: {len(x_test)} วัน")

     model = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=20,random_state=42,)
     model.fit(x_train,y_train)
 # ประเมินผล
     y_pred = model.predict(x_test)
     print("\n--- Model Performance ---")
     print(classification_report(y_test,y_pred, target_names=["ไม่ขึ้น" ," ขึ้น > 1%"]))
      # Feature importance

     print("--- Feature Importance ---")
     pairs = zip(FEATURES, model.feature_importances_)
     for feat, imp in sorted(pairs, key=lambda x: -x[1]):
        bar = "█" * int(imp * 50)
        print(f"{feat:12} {bar} {imp:.3f}")

        # Save model
     with open("model.pkl", "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)
     print("\n✅ Saved model to model.pkl")
if __name__ == "__main__":
    train()
