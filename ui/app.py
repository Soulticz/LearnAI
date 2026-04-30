from pathlib import Path
import json

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
BACKTEST_FILE = ROOT / "backtest_summary.csv"
STRATEGY_FILE = ROOT / "strategy_modes.csv"
PORTFOLIO_FILE = ROOT / "paper_portfolio.json"

st.set_page_config(
    page_title="SoulQuant Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 SoulQuant Dashboard")
st.caption("AI Stock Analyst • Backtest • Strategy Selector • Paper Portfolio")


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_portfolio(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


backtest_df = load_csv(BACKTEST_FILE)
strategy_df = load_csv(STRATEGY_FILE)
portfolio = load_portfolio(PORTFOLIO_FILE)

with st.sidebar:
    st.header("⚙️ Data Status")
    st.write("Backtest:", "✅" if backtest_df is not None else "❌")
    st.write("Strategy:", "✅" if strategy_df is not None else "❌")
    st.write("Paper Portfolio:", "✅" if portfolio is not None else "❌")
    st.divider()
    st.caption("ถ้าไฟล์ไม่ขึ้น ให้รัน:")
    st.code("python backtest.py\npython strategy_selector.py\npython paper_trading.py", language="powershell")


tab1, tab2, tab3, tab4 = st.tabs([
    "📒 Portfolio",
    "🧭 Strategy Modes",
    "📊 Backtest",
    "🔎 Stock Detail",
])

with tab1:
    st.subheader("📒 Paper Portfolio")
    if portfolio is None:
        st.warning("ยังไม่พบ paper_portfolio.json ให้รัน python paper_trading.py ก่อน")
    else:
        cash = float(portfolio.get("cash", 0))
        positions = portfolio.get("positions", {})
        total_value = cash
        rows = []

        for ticker, pos in positions.items():
            shares = float(pos.get("shares", 0))
            avg_price = float(pos.get("avg_price", 0))
            last_price = float(pos.get("last_price", avg_price))
            market_value = shares * last_price
            pnl_pct = ((last_price - avg_price) / avg_price * 100) if avg_price else 0
            total_value += market_value
            rows.append({
                "ticker": ticker,
                "shares": shares,
                "avg_price": avg_price,
                "last_price": last_price,
                "market_value": market_value,
                "pnl_pct": pnl_pct,
            })

        c1, c2, c3 = st.columns(3)
        c1.metric("Cash", f"{cash:,.2f}")
        c2.metric("Positions", len(positions))
        c3.metric("Total Value", f"{total_value:,.2f}", f"{((total_value - 100000) / 100000) * 100:+.2f}%")

        if rows:
            pos_df = pd.DataFrame(rows)
            st.dataframe(pos_df, use_container_width=True)
            fig = px.pie(pos_df, values="market_value", names="ticker", title="Portfolio Allocation")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ยังไม่มี position ใน paper portfolio")

        trades = portfolio.get("trades", [])
        if trades:
            st.subheader("Trade History")
            st.dataframe(pd.DataFrame(trades).tail(20), use_container_width=True)

with tab2:
    st.subheader("🧭 Strategy Modes")
    if strategy_df is None:
        st.warning("ยังไม่พบ strategy_modes.csv ให้รัน python strategy_selector.py ก่อน")
    else:
        mode_counts = strategy_df["mode"].value_counts().reset_index()
        mode_counts.columns = ["mode", "count"]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.dataframe(mode_counts, use_container_width=True)
        with c2:
            fig = px.bar(mode_counts, x="mode", y="count", title="Strategy Mode Count")
            st.plotly_chart(fig, use_container_width=True)

        mode_filter = st.multiselect(
            "Filter mode",
            options=sorted(strategy_df["mode"].unique()),
            default=sorted(strategy_df["mode"].unique()),
        )
        filtered = strategy_df[strategy_df["mode"].isin(mode_filter)]
        st.dataframe(filtered, use_container_width=True)

with tab3:
    st.subheader("📊 Backtest Summary")
    if backtest_df is None:
        st.warning("ยังไม่พบ backtest_summary.csv ให้รัน python backtest.py ก่อน")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg AI Return", f"{backtest_df['ai_return_pct'].mean():+.2f}%")
        c2.metric("Avg Hybrid Return", f"{backtest_df['hybrid_return_pct'].mean():+.2f}%")
        c3.metric("Avg Buy & Hold", f"{backtest_df['buy_hold_pct'].mean():+.2f}%")

        chart_df = backtest_df.sort_values("hybrid_return_pct", ascending=False).head(15)
        fig = px.bar(
            chart_df,
            x="ticker",
            y=["ai_return_pct", "hybrid_return_pct", "buy_hold_pct"],
            barmode="group",
            title="Top 15 Return Comparison",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(backtest_df, use_container_width=True)

with tab4:
    st.subheader("🔎 Stock Detail")
    if backtest_df is None:
        st.warning("ยังไม่พบ backtest_summary.csv")
    else:
        ticker = st.selectbox("เลือกหุ้น", backtest_df["ticker"].tolist())
        row = backtest_df[backtest_df["ticker"] == ticker].iloc[0]

        strategy_row = None
        if strategy_df is not None and ticker in strategy_df["ticker"].values:
            strategy_row = strategy_df[strategy_df["ticker"] == ticker].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AI Return", f"{row['ai_return_pct']:+.2f}%")
        c2.metric("Hybrid Return", f"{row['hybrid_return_pct']:+.2f}%")
        c3.metric("Buy & Hold", f"{row['buy_hold_pct']:+.2f}%")
        c4.metric("Hybrid DD", f"{row['hybrid_max_drawdown_pct']:.2f}%")

        if strategy_row is not None:
            st.info(f"Strategy: {strategy_row['mode']} — {strategy_row['reason']}")

        compare_df = pd.DataFrame({
            "strategy": ["AI", "Hybrid", "Buy & Hold"],
            "return_pct": [row["ai_return_pct"], row["hybrid_return_pct"], row["buy_hold_pct"]],
        })
        fig = px.bar(compare_df, x="strategy", y="return_pct", title=f"{ticker} Return Comparison")
        st.plotly_chart(fig, use_container_width=True)
