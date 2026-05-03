from pathlib import Path
import json
import sys

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

PORTFOLIO_FILE = ROOT / "paper_portfolio.json"

st.set_page_config(page_title="Trade Log", page_icon="📜", layout="wide")
st.title("📜 Trade Log")
st.caption("ประวัติการซื้อขายจำลองจาก Paper Trading")


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
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["price", "shares", "cash_after"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


portfolio = load_portfolio()

if portfolio is None:
    st.warning("ยังไม่พบ paper_portfolio.json ให้รัน python paper_trading.py ก่อน")
    st.stop()

trade_df = build_trade_df(portfolio)

cash = float(portfolio.get("cash", 0))
positions = portfolio.get("positions", {})

c1, c2, c3 = st.columns(3)
c1.metric("Cash", f"{cash:,.2f}")
c2.metric("Open Positions", len(positions))
c3.metric("Total Trades", len(trade_df))

st.divider()

if trade_df.empty:
    st.info("ยังไม่มี trade ค่ะ ลองไปหน้า 🧪 Paper Trading Test แล้วกด Test BUY ดูก่อน")
    st.stop()

# Filters
left, right = st.columns([1, 2])
with left:
    tickers = sorted(trade_df["ticker"].dropna().unique().tolist()) if "ticker" in trade_df.columns else []
    selected_tickers = st.multiselect("Filter ticker", tickers, default=tickers)
with right:
    actions = sorted(trade_df["action"].dropna().unique().tolist()) if "action" in trade_df.columns else []
    selected_actions = st.multiselect("Filter action", actions, default=actions)

filtered = trade_df.copy()
if selected_tickers:
    filtered = filtered[filtered["ticker"].isin(selected_tickers)]
if selected_actions:
    filtered = filtered[filtered["action"].isin(selected_actions)]

# Summary by ticker/action
st.subheader("📊 Trade Summary")
summary = (
    filtered.groupby(["ticker", "action"], dropna=False)
    .agg(
        trades=("action", "count"),
        total_shares=("shares", "sum"),
        avg_price=("price", "mean"),
    )
    .reset_index()
)
st.dataframe(summary, use_container_width=True)

if not filtered.empty and "timestamp" in filtered.columns:
    fig = px.scatter(
        filtered,
        x="timestamp",
        y="price",
        color="action",
        size="shares",
        hover_data=["ticker", "shares", "cash_after", "reason"],
        title="Trade Timeline",
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🧾 Trade History")
st.dataframe(filtered.sort_values("timestamp", ascending=False), use_container_width=True)

st.subheader("📦 Current Positions")
if positions:
    rows = []
    for ticker, pos in positions.items():
        shares = float(pos.get("shares", 0))
        avg_price = float(pos.get("avg_price", 0))
        last_price = float(pos.get("last_price", avg_price))
        market_value = shares * last_price
        pnl_pct = ((last_price - avg_price) / avg_price * 100) if avg_price else 0
        rows.append({
            "ticker": ticker,
            "shares": shares,
            "avg_price": avg_price,
            "last_price": last_price,
            "market_value": market_value,
            "pnl_pct": pnl_pct,
        })
    pos_df = pd.DataFrame(rows)
    st.dataframe(pos_df, use_container_width=True)
    st.plotly_chart(px.bar(pos_df, x="ticker", y="pnl_pct", title="Open Position P/L %"), use_container_width=True)
else:
    st.info("ยังไม่มี position เปิดอยู่")
