import pickle

import yfinance as yf
import pandas as pd
import ta as ta_lib
import matplotlib.pyplot as plt

WATCHLIST = [
    "SNDK", "AAPL", "MSFT", "NVDA", "GOOGL", "META",
    "AMZN", "TSLA", "AMD", "INTC", "CRM",
    "ORCL", "ADBE", "QCOM", "TXN", "AVGO",
    # Finance
    "JPM", "BAC", "GS", "MS", "V", "MA",
    # Health
    "JNJ", "PFE", "MRNA", "UNH", "ABBV",
    # Energy
    "XOM", "CVX", "OXY",
    # Consumer
    "MCD", "SBUX", "NKE", "DIS", "NFLX",
    # ETF
    "SPY", "QQQ", "IWM",
    # Crypto-related
    "COIN", "MSTR", "MARA",
]

FEATURES = [
    "rsi", "macd", "macd_hist", "sma_20", "sma_50",
    "bb_upper", "bb_lower", "change_1d", "change_5d", "vol_ratio"
]

BUY_PROB_THRESHOLD = 0.55
SELL_PROB_THRESHOLD = 0.45
INITIAL_CAPITAL = 100000.0
TRADE_FEE_RATE = 0.001  # 0.1% ต่อการซื้อ/ขาย 1 ครั้ง
CORE_HOLD_RATIO = 0.50  # ถือยาว 50% + ให้ AI เทรด 50%


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


def safe_filename(ticker: str) -> str:
    return ticker.replace("^", "").replace("=", "_").replace("-", "_")


def simulate_ai_trading(df: pd.DataFrame, model, model_features, starting_capital: float, verbose: bool = False, ticker_symbol: str = ""):
    capital = starting_capital
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

        equity = capital if position == 0 else position * current_price
        equity_curve.append({"date": df.index[i], "equity": equity})

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
            if verbose:
                print(f"🛒 BUY  {ticker_symbol} {df.index[i].date()} | Price: {current_price:,.2f} | ML: {prob:.1%}")

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
            if verbose:
                print(
                    f"💰 SELL {ticker_symbol} {df.index[i].date()} | Price: {current_price:,.2f} | "
                    f"ML: {prob:.1%} | Trade: {trade_return:+.2f}% | Capital: {capital:,.2f}"
                )

    final_value = capital if position == 0 else position * float(df["close"].iloc[-1])
    sell_trades = [t for t in trades if t["type"] == "SELL"]
    wins = [t for t in sell_trades if t.get("return_pct", 0) > 0]
    win_rate = (len(wins) / len(sell_trades) * 100) if sell_trades else 0
    equity_df = pd.DataFrame(equity_curve).set_index("date")

    return {
        "final_value": final_value,
        "trades": sell_trades,
        "win_rate_pct": win_rate,
        "equity_df": equity_df,
        "max_drawdown_pct": max_drawdown(equity_df["equity"]),
    }


def prepare_data(ticker_symbol: str, period: str):
    df = yf.download(ticker_symbol, period=period, interval="1d", progress=False)

    if df.empty:
        print(f"❌ ไม่พบข้อมูล {ticker_symbol}")
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    df = build_features(df).dropna().copy()
    if df.empty:
        print(f"❌ ข้อมูลไม่พอหลังคำนวณ indicators: {ticker_symbol}")
        return None
    return df


def run_backtest(ticker_symbol: str, period: str = "2y", model=None, model_features=None, verbose: bool = True):
    if model is None or model_features is None:
        model, model_features = load_model()
    if model is None:
        return None

    df = prepare_data(ticker_symbol, period)
    if df is None:
        return None

    ai = simulate_ai_trading(df, model, model_features, INITIAL_CAPITAL, verbose=verbose, ticker_symbol=ticker_symbol)
    final_value = ai["final_value"]
    total_return = ((final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    buy_hold_return = ((float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / float(df["close"].iloc[0])) * 100

    result = {
        "ticker": ticker_symbol,
        "final_capital": final_value,
        "ai_return_pct": total_return,
        "buy_hold_pct": buy_hold_return,
        "closed_trades": len(ai["trades"]),
        "win_rate_pct": ai["win_rate_pct"],
        "max_drawdown_pct": ai["max_drawdown_pct"],
    }

    if verbose:
        print(f"\n--- Backtest Result: {ticker_symbol} ({period}) ---")
        print(f"Initial Capital : {INITIAL_CAPITAL:,.2f}")
        print(f"Final Capital   : {final_value:,.2f}")
        print(f"AI Return       : {total_return:+.2f}%")
        print(f"Buy & Hold      : {buy_hold_return:+.2f}%")
        print(f"Trades          : {len(ai['trades'])} closed trades")
        print(f"Win Rate        : {ai['win_rate_pct']:.2f}%")
        print(f"Max Drawdown    : {ai['max_drawdown_pct']:.2f}%")

        plt.figure(figsize=(10, 5))
        plt.plot(ai["equity_df"].index, ai["equity_df"]["equity"], linewidth=2)
        plt.title(f"{ticker_symbol} AI Backtest Equity Curve")
        plt.xlabel("Date")
        plt.ylabel("Equity")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"backtest_{safe_filename(ticker_symbol)}.png")
        plt.close()
        print("📈 Saved equity curve image")

    return result


def run_hybrid_backtest(ticker_symbol: str, period: str = "2y", model=None, model_features=None, verbose: bool = False):
    if model is None or model_features is None:
        model, model_features = load_model()
    if model is None:
        return None

    df = prepare_data(ticker_symbol, period)
    if df is None:
        return None

    core_capital = INITIAL_CAPITAL * CORE_HOLD_RATIO
    ai_capital = INITIAL_CAPITAL * (1 - CORE_HOLD_RATIO)

    first_price = float(df["close"].iloc[0])
    last_price = float(df["close"].iloc[-1])

    core_position = (core_capital * (1 - TRADE_FEE_RATE)) / first_price
    core_final = core_position * last_price

    ai = simulate_ai_trading(df, model, model_features, ai_capital, verbose=verbose, ticker_symbol=ticker_symbol)
    hybrid_final = core_final + ai["final_value"]
    hybrid_return = ((hybrid_final - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    buy_hold_return = ((last_price - first_price) / first_price) * 100

    hybrid_equity_df = ai["equity_df"].copy()
    core_equity = core_position * df.loc[hybrid_equity_df.index, "close"]
    hybrid_equity_df["equity"] = hybrid_equity_df["equity"] + core_equity

    return {
        "ticker": ticker_symbol,
        "hybrid_final_capital": hybrid_final,
        "hybrid_return_pct": hybrid_return,
        "buy_hold_pct": buy_hold_return,
        "closed_trades": len(ai["trades"]),
        "win_rate_pct": ai["win_rate_pct"],
        "hybrid_max_drawdown_pct": max_drawdown(hybrid_equity_df["equity"]),
    }


def run_backtest_all(period: str = "2y"):
    model, model_features = load_model()
    if model is None:
        return

    results = []
    for i, ticker in enumerate(WATCHLIST, start=1):
        print(f"\n[{i}/{len(WATCHLIST)}] Backtesting {ticker}...")
        try:
            ai_result = run_backtest(ticker, period=period, model=model, model_features=model_features, verbose=False)
            hybrid_result = run_hybrid_backtest(ticker, period=period, model=model, model_features=model_features, verbose=False)
            if ai_result and hybrid_result:
                result = {**ai_result, **hybrid_result}
                results.append(result)
                print(
                    f"✅ {ticker}: AI {result['ai_return_pct']:+.2f}% | "
                    f"Hybrid {result['hybrid_return_pct']:+.2f}% | "
                    f"B&H {result['buy_hold_pct']:+.2f}% | "
                    f"Trades {result['closed_trades']} | "
                    f"Win {result['win_rate_pct']:.1f}% | "
                    f"AI DD {result['max_drawdown_pct']:.2f}% | "
                    f"Hybrid DD {result['hybrid_max_drawdown_pct']:.2f}%"
                )
        except Exception as e:
            print(f"❌ {ticker}: {e}")

    if not results:
        print("❌ ไม่มีผล backtest")
        return

    summary = pd.DataFrame(results)
    summary["ai_alpha_vs_hold_pct"] = summary["ai_return_pct"] - summary["buy_hold_pct"]
    summary["hybrid_alpha_vs_hold_pct"] = summary["hybrid_return_pct"] - summary["buy_hold_pct"]
    summary = summary.sort_values("hybrid_return_pct", ascending=False)
    summary.to_csv("backtest_summary.csv", index=False, encoding="utf-8-sig")

    print("\n========== Backtest Summary ==========")
    print(summary.to_string(index=False, formatters={
        "final_capital": "{:,.2f}".format,
        "hybrid_final_capital": "{:,.2f}".format,
        "ai_return_pct": "{:+.2f}".format,
        "hybrid_return_pct": "{:+.2f}".format,
        "buy_hold_pct": "{:+.2f}".format,
        "win_rate_pct": "{:.2f}".format,
        "max_drawdown_pct": "{:.2f}".format,
        "hybrid_max_drawdown_pct": "{:.2f}".format,
        "ai_alpha_vs_hold_pct": "{:+.2f}".format,
        "hybrid_alpha_vs_hold_pct": "{:+.2f}".format,
    }))
    print("\n💾 Saved summary to backtest_summary.csv")


if __name__ == "__main__":
    run_backtest_all(period="2y")
