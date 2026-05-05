from pathlib import Path
import json

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO_FILE = ROOT / "paper_portfolio.json"
INITIAL_CASH = 100000.0

st.set_page_config(page_title="Performance", page_icon="📊", layout="wide")
st.title("📊 Performance")
st.caption("สรุปผล Paper Trading: Win Rate, กำไร/ขาดทุน และประสิทธิภาพระบบ")


def load_portfolio() -> dict | None:
    if not PORTFOLIO_FILE.exists():
        return None
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_trade_df(portfolio: dict) -> pd.DataFrame:
    trades = portfolio.get("trades", [])
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["price", "shares", "cash_after"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["trade_value"] = df["price"] * df["shares"]
    return df.sort_values("timestamp")


def estimate_closed_trades(trade_df: pd.DataFrame) -> pd.DataFrame:
    """จับคู่ BUY/SELL แบบง่ายด้วย avg buy cost ต่อ ticker

    หมายเหตุ: เป็นเวอร์ชัน estimate สำหรับ paper trading เบื้องต้น
    """
    positions = {}
    closed_rows = []

    for _, trade in trade_df.iterrows():
        ticker = str(trade.get("ticker", "")).upper()
        action = str(trade.get("action", "")).upper()
        price = float(trade.get("price", 0) or 0)
        shares = float(trade.get("shares", 0) or 0)
        timestamp = trade.get("timestamp")
        reason = str(trade.get("reason", ""))

        if not ticker or shares <= 0 or price <= 0:
            continue

        if action == "BUY":
            pos = positions.get(ticker, {"shares": 0.0, "avg_price": 0.0})
            old_shares = float(pos["shares"])
            old_avg = float(pos["avg_price"])
            new_shares = old_shares + shares
            new_avg = ((old_shares * old_avg) + (shares * price)) / new_shares
            positions[ticker] = {"shares": new_shares, "avg_price": new_avg}

        elif action in ["SELL", "SELL_HALF"]:
            pos = positions.get(ticker)
            if not pos or pos["shares"] <= 0:
                continue

            sell_shares = min(shares, float(pos["shares"]))
            avg_price = float(pos["avg_price"])
            pnl = (price - avg_price) * sell_shares
            pnl_pct = ((price - avg_price) / avg_price * 100) if avg_price else 0

            closed_rows.append({
                "timestamp": timestamp,
                "ticker": ticker,
                "action": action,
                "avg_buy_price": avg_price,
                "sell_price": price,
                "shares": sell_shares,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "result": "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN",
                "reason": reason,
            })

            pos["shares"] = float(pos["shares"]) - sell_shares
            if pos["shares"] <= 0:
                del positions[ticker]
            else:
                positions[ticker] = pos

    return pd.DataFrame(closed_rows)


portfolio = load_portfolio()

if portfolio is None:
    st.warning("ยังไม่พบ paper_portfolio.json ให้รัน python paper_trading.py ก่อน")
    st.stop()

trade_df = build_trade_df(portfolio)

cash = float(portfolio.get("cash", 0))
positions = portfolio.get("positions", {})
market_value = 0.0
for ticker, pos in positions.items():
    shares = float(pos.get("shares", 0))
    last_price = float(pos.get("last_price", pos.get("avg_price", 0)))
    market_value += shares * last_price

current_equity = cash + market_value
total_return = ((current_equity - INITIAL_CASH) / INITIAL_CASH * 100) if INITIAL_CASH else 0

closed_df = estimate_closed_trades(trade_df) if not trade_df.empty else pd.DataFrame()

wins = int((closed_df["result"] == "WIN").sum()) if not closed_df.empty else 0
losses = int((closed_df["result"] == "LOSS").sum()) if not closed_df.empty else 0
breakevens = int((closed_df["result"] == "BREAKEVEN").sum()) if not closed_df.empty else 0
closed_count = len(closed_df)
win_rate = (wins / closed_count * 100) if closed_count else 0
realized_pnl = float(closed_df["pnl"].sum()) if not closed_df.empty else 0
avg_pnl = float(closed_df["pnl"].mean()) if not closed_df.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Equity", f"{current_equity:,.2f}", f"{total_return:+.2f}%")
c2.metric("Win Rate", f"{win_rate:.2f}%")
c3.metric("Realized P/L", f"{realized_pnl:,.2f}")
c4.metric("Closed Trades", closed_count)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Wins", wins)
c6.metric("Losses", losses)
c7.metric("Breakeven", breakevens)
c8.metric("Avg P/L", f"{avg_pnl:,.2f}")

st.divider()

if trade_df.empty:
    st.info("ยังไม่มี trade ให้ประเมิน performance")
    st.stop()

if closed_df.empty:
    st.info("ยังไม่มีรายการขาย เลยยังคำนวณ Win Rate ไม่ได้ ลอง SELL หรือให้ Take Profit/Stop Loss ทำงานก่อน")
else:
    st.subheader("🏆 Win / Loss Summary")
    result_counts = closed_df["result"].value_counts().reset_index()
    result_counts.columns = ["result", "count"]
    st.plotly_chart(px.pie(result_counts, values="count", names="result", title="Win / Loss Ratio"), use_container_width=True)

    st.subheader("📈 Realized P/L Timeline")
    closed_df["cumulative_pnl"] = closed_df["pnl"].cumsum()
    st.plotly_chart(
        px.line(closed_df, x="timestamp", y="cumulative_pnl", markers=True, title="Cumulative Realized P/L"),
        use_container_width=True,
    )

    st.subheader("📊 P/L by Ticker")
    by_ticker = closed_df.groupby("ticker").agg(
        closed_trades=("ticker", "count"),
        total_pnl=("pnl", "sum"),
        avg_pnl_pct=("pnl_pct", "mean"),
    ).reset_index()
    st.dataframe(by_ticker, use_container_width=True)
    st.plotly_chart(px.bar(by_ticker, x="ticker", y="total_pnl", title="Realized P/L by Ticker"), use_container_width=True)

    st.subheader("🧾 Closed Trade Details")
    st.dataframe(closed_df.sort_values("timestamp", ascending=False), use_container_width=True)

st.subheader("📋 Raw Trade Log")
st.dataframe(trade_df.sort_values("timestamp", ascending=False), use_container_width=True)

st.caption("หมายเหตุ: Win Rate หน้านี้เป็น estimate จาก trade log โดยจับคู่ราคา BUY เฉลี่ยต่อ ticker")
