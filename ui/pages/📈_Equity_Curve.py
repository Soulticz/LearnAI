from pathlib import Path
import json

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO_FILE = ROOT / "paper_portfolio.json"
INITIAL_CASH = 100000.0

st.set_page_config(page_title="Equity Curve", page_icon="📈", layout="wide")
st.title("📈 Equity Curve")
st.caption("ดูเส้นทางมูลค่าพอร์ตจาก Paper Trading")


def load_portfolio() -> dict | None:
    if not PORTFOLIO_FILE.exists():
        return None
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


portfolio = load_portfolio()

if portfolio is None:
    st.warning("ยังไม่พบ paper_portfolio.json ให้รัน python paper_trading.py ก่อน")
    st.stop()

cash = float(portfolio.get("cash", 0))
positions = portfolio.get("positions", {})
trades = portfolio.get("trades", [])

current_market_value = 0.0
for ticker, pos in positions.items():
    shares = float(pos.get("shares", 0))
    last_price = float(pos.get("last_price", pos.get("avg_price", 0)))
    current_market_value += shares * last_price

current_equity = cash + current_market_value
pnl_pct = ((current_equity - INITIAL_CASH) / INITIAL_CASH * 100) if INITIAL_CASH else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cash", f"{cash:,.2f}")
c2.metric("Market Value", f"{current_market_value:,.2f}")
c3.metric("Current Equity", f"{current_equity:,.2f}", f"{pnl_pct:+.2f}%")
c4.metric("Trades", len(trades))

st.divider()

if not trades:
    st.info("ยังไม่มี trade ให้สร้างกราฟ ลองไปหน้า 🧪 Paper Trading Test แล้วกด Test BUY/SELL ก่อน")
    st.stop()

trade_df = pd.DataFrame(trades)
trade_df["timestamp"] = pd.to_datetime(trade_df["timestamp"], errors="coerce")
trade_df["cash_after"] = pd.to_numeric(trade_df["cash_after"], errors="coerce")
trade_df["price"] = pd.to_numeric(trade_df["price"], errors="coerce")
trade_df["shares"] = pd.to_numeric(trade_df["shares"], errors="coerce")
trade_df = trade_df.sort_values("timestamp")

# เวอร์ชันเริ่มต้น: ใช้ cash_after เป็น equity timeline จาก trade log
# หมายเหตุ: ยังไม่ mark-to-market ทุกวัน แต่ช่วยให้เห็น flow เงินหลังซื้อขาย
trade_df["equity_cash_curve"] = trade_df["cash_after"]

st.subheader("📈 Cash-Based Equity Curve")
st.caption("กราฟนี้ใช้ cash_after จาก trade log ก่อน ยังไม่รวมมูลค่าหุ้นค้างในทุกจุดเวลา")

fig = px.line(
    trade_df,
    x="timestamp",
    y="equity_cash_curve",
    markers=True,
    title="Paper Trading Equity Curve",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🧾 Trade Timeline")
fig2 = px.scatter(
    trade_df,
    x="timestamp",
    y="price",
    color="action",
    size="shares",
    hover_data=["ticker", "shares", "cash_after", "reason"],
    title="BUY / SELL Timeline",
)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("📋 Trade Data")
st.dataframe(trade_df.sort_values("timestamp", ascending=False), use_container_width=True)

st.subheader("📦 Current Positions")
if positions:
    rows = []
    for ticker, pos in positions.items():
        shares = float(pos.get("shares", 0))
        avg_price = float(pos.get("avg_price", 0))
        last_price = float(pos.get("last_price", avg_price))
        stop_loss = float(pos.get("stop_loss", 0))
        take_profit_5 = avg_price * 1.05 if avg_price else 0
        take_profit_10 = avg_price * 1.10 if avg_price else 0
        market_value = shares * last_price
        pnl_pct_pos = ((last_price - avg_price) / avg_price * 100) if avg_price else 0
        rows.append({
            "ticker": ticker,
            "shares": shares,
            "avg_price": avg_price,
            "last_price": last_price,
            "stop_loss": stop_loss,
            "take_profit_5": take_profit_5,
            "take_profit_10": take_profit_10,
            "market_value": market_value,
            "pnl_pct": pnl_pct_pos,
        })
    pos_df = pd.DataFrame(rows)
    st.dataframe(pos_df, use_container_width=True)
else:
    st.info("ยังไม่มี position เปิดอยู่")
