import pickle

import yfinance as yf
import pandas as pd
import ta as ta_lib
import matplotlib.pyplot as plt

FEATURES = [
    "rsi", "macd", "macd_hist", "sma_20", "sma_50",
    "bb_upper", "bb_lower", "change_1d", "change_5d", "vol_ratio"
]

BUY_PROB_THRESHOLD = 0.65
SELL_PROB_THRESHOLD = 0.35
INITIAL_CAPITAL = 100000.0
TRADE_FEE_RATE = 0.001  # 0.1% ต่อการซื้อ/ขาย 1 ครั้ง


def load_model():
    try:
        with open("model.pkl", "rb") as f:
            saved = pickle.load(f)
            return saved["model"], saved.get("features", FEATURES)
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์ model.pkl กรุณารัน train_model.py ก่อน")
        return None, FEATURES


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    volume = df["volume"]

    df["rsi"] = ta_lib.momentum.RSIIndicator(close, window=14).rsi()

    macd_obj = ta_lib.trend.MACD(close)
    df["macd"] = macd_obj.macd()
    df["macd_hist"] = macd_obj.macd_diff()

    df["sma_20"] = ta_lib.trend.SMAIndicator(close, window=20).sma_indicator()
    df["sma_50"] = ta_lib.trend.SMAIndicator(close, window=50).sma_indicator()

    bb = ta_lib.volatility.BollingerBands(close, window=20)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    df["change_1d"] = close.pct_change(1)
    df["change_5d"] = close.pct_change(5)
    df["vol_ratio"] = volume / volume.rolling(20).mean()

    return df


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min() * 100)


def run_backtest(ticker_symbol: str, period: str = "2y"):
    model, model_features = load_model()
    if model is None:
        return

    df = yf.download(ticker_symbol, period=period, interval="1d", progress=False)

    if df.empty:
        print(f"❌ ไม่พบข้อมูล {ticker_symbol}")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    df = build_features(df).dropna().copy()

    capital = INITIAL_CAPITAL
    position = 0.0
    entry_price = None
    trades = []
    equity_curve = []

    for i in range(len(df)):
        row = df.iloc[i]
        current_price = float(row["close"])

        feat_row = pd.DataFrame([{feat: float(row[feat]) for feat in FEATURES}])
        feat_row = feat_row[model_features]
        prob = float(model.predict_proba(feat_row)[0][1])

        # Equity ณ วันนั้น เพื่อคำนวณ drawdown
        equity = capital if position == 0 else position * current_price
        equity_curve.append({"date": df.index[i], "equity": equity})

        # BUY: ML มั่นใจว่าราคาขึ้น และยังไม่มี position
        if position == 0 and prob > BUY_PROB_THRESHOLD:
            buy_capital = capital * (1 - TRADE_FEE_RATE)
            position = buy_capital / current_price
            capital = 0.0
            entry_price = current_price
            trades.append({
                "date": df.index[i],
                "type": "BUY",
                "price": current_price,
                "prob": prob,
                "capital": buy_capital,
            })
            print(f"🛒 BUY  {df.index[i].date()} | Price: {current_price:,.2f} | ML: {prob:.1%}")

        # SELL: ML เริ่มไม่มั่นใจ หรือ RSI สูงมากและ MACD Hist อ่อน
        elif position > 0 and (
            prob < SELL_PROB_THRESHOLD
            or (row["rsi"] > 65 and row["macd_hist"] < 0)
        ):
            gross_capital = position * current_price
            capital = gross_capital * (1 - TRADE_FEE_RATE)
            trade_return = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0
            position = 0.0
            entry_price = None
            trades.append({
                "date": df.index[i],
                "type": "SELL",
                "price": current_price,
                "prob": prob,
                "capital": capital,
                "return_pct": trade_return,
            })
            print(
                f"💰 SELL {df.index[i].date()} | Price: {current_price:,.2f} | "
                f"ML: {prob:.1%} | Trade: {trade_return:+.2f}% | Capital: {capital:,.2f}"
            )

    final_value = capital if position == 0 else position * float(df["close"].iloc[-1])
    total_return = ((final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

    buy_hold_return = ((float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / float(df["close"].iloc[0])) * 100

    sell_trades = [t for t in trades if t["type"] == "SELL"]
    wins = [t for t in sell_trades if t.get("return_pct", 0) > 0]
    win_rate = (len(wins) / len(sell_trades) * 100) if sell_trades else 0

    equity_df = pd.DataFrame(equity_curve).set_index("date")
    mdd = max_drawdown(equity_df["equity"])

    print(f"\n--- Backtest Result: {ticker_symbol} ({period}) ---")
    print(f"Initial Capital : {INITIAL_CAPITAL:,.2f}")
    print(f"Final Capital   : {final_value:,.2f}")
    print(f"AI Return       : {total_return:+.2f}%")
    print(f"Buy & Hold      : {buy_hold_return:+.2f}%")
    print(f"Trades          : {len(sell_trades)} closed trades")
    print(f"Win Rate        : {win_rate:.2f}%")
    print(f"Max Drawdown    : {mdd:.2f}%")

    # วาด equity curve
    plt.figure(figsize=(10, 5))
    plt.plot(equity_df.index, equity_df["equity"], linewidth=2)
    plt.title(f"{ticker_symbol} AI Backtest Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"backtest_{ticker_symbol.replace('^', '').replace('=', '_')}.png")
    plt.close()
    print("📈 Saved equity curve image")


if __name__ == "__main__":
    run_backtest("^GSPC", period="2y")
