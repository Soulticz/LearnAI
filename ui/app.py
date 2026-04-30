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

MODE_COLORS = {
    "HYBRID": "#16a34a",
    "HOLD": "#2563eb",
    "WATCH": "#ca8a04",
    "AVOID": "#dc2626",
    "UNKNOWN": "#6b7280",
}

st.markdown(
    """
    <style>
    .sq-card {
        padding: 18px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
        min-height: 132px;
    }
    .sq-mode {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 8px;
    }
    .sq-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .sq-subtle {
        color: rgba(255,255,255,0.70);
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
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


def mode_badge(mode: str) -> str:
    color = MODE_COLORS.get(str(mode).upper(), MODE_COLORS["UNKNOWN"])
    return f"<span class='sq-mode' style='background:{color}'>{mode}</span>"


def render_pick_card(row: pd.Series):
    mode = str(row.get("mode", "UNKNOWN"))
    ticker = str(row.get("ticker", "-"))
    reason = str(row.get("reason", ""))
    hybrid_return = float(row.get("hybrid_return_pct", 0))
    buy_hold = float(row.get("buy_hold_pct", 0))
    alpha = float(row.get("hybrid_alpha_vs_hold_pct", 0))
    st.markdown(
        f"""
        <div class="sq-card">
            {mode_badge(mode)}
            <div class="sq-title">{ticker}</div>
            <div class="sq-subtle">Hybrid: <b>{hybrid_return:+.2f}%</b> • B&H: <b>{buy_hold:+.2f}%</b></div>
            <div class="sq-subtle">Alpha: <b>{alpha:+.2f}%</b></div>
            <div class="sq-subtle" style="margin-top:8px;">{reason[:160]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

# Top Action Panel
st.subheader("⚡ Top Action Panel")
if strategy_df is None:
    st.warning("ยังไม่พบ strategy_modes.csv ให้รัน python strategy_selector.py ก่อน")
else:
    hybrid_top = strategy_df[strategy_df["mode"] == "HYBRID"].sort_values("hybrid_alpha_vs_hold_pct", ascending=False).head(3)
    hold_top = strategy_df[strategy_df["mode"] == "HOLD"].sort_values("buy_hold_pct", ascending=False).head(3)
    watch_top = strategy_df[strategy_df["mode"] == "WATCH"].sort_values("hybrid_alpha_vs_hold_pct", ascending=False).head(3)
    avoid_top = strategy_df[strategy_df["mode"] == "AVOID"].sort_values("hybrid_max_drawdown_pct", ascending=True).head(3)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("### 🟢 Best HYBRID")
        if hybrid_top.empty:
            st.caption("ยังไม่มี")
        else:
            render_pick_card(hybrid_top.iloc[0])
    with c2:
        st.markdown("### 🔵 Best HOLD")
        if hold_top.empty:
            st.caption("ยังไม่มี")
        else:
            render_pick_card(hold_top.iloc[0])
    with c3:
        st.markdown("### 🟡 WATCH")
        if watch_top.empty:
            st.caption("ยังไม่มี")
        else:
            render_pick_card(watch_top.iloc[0])
    with c4:
        st.markdown("### 🔴 AVOID")
        if avoid_top.empty:
            st.caption("ยังไม่มี")
        else:
            render_pick_card(avoid_top.iloc[0])

    with st.expander("ดู Top Picks ทั้งหมด"):
        col1, col2, col3, col4 = st.columns(4)
        for col, title, data in [
            (col1, "🟢 HYBRID", hybrid_top),
            (col2, "🔵 HOLD", hold_top),
            (col3, "🟡 WATCH", watch_top),
            (col4, "🔴 AVOID", avoid_top),
        ]:
            with col:
                st.markdown(f"#### {title}")
                if data.empty:
                    st.caption("ไม่มีข้อมูล")
                else:
                    st.dataframe(data[["ticker", "mode", "hybrid_return_pct", "buy_hold_pct", "hybrid_alpha_vs_hold_pct"]], use_container_width=True)

st.divider()

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
            fig = px.bar(
                mode_counts,
                x="mode",
                y="count",
                title="Strategy Mode Count",
                color="mode",
                color_discrete_map=MODE_COLORS,
            )
            st.plotly_chart(fig, use_container_width=True)

        mode_filter = st.multiselect(
            "Filter mode",
            options=sorted(strategy_df["mode"].unique()),
            default=sorted(strategy_df["mode"].unique()),
        )
        filtered = strategy_df[strategy_df["mode"].isin(mode_filter)].copy()
        st.dataframe(
            filtered.style.apply(
                lambda row: [f"background-color: {MODE_COLORS.get(row['mode'], '#6b7280')}33"] * len(row),
                axis=1,
            ),
            use_container_width=True,
        )

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
            st.markdown(f"{mode_badge(strategy_row['mode'])}", unsafe_allow_html=True)
            st.info(f"{strategy_row['reason']}")

        compare_df = pd.DataFrame({
            "strategy": ["AI", "Hybrid", "Buy & Hold"],
            "return_pct": [row["ai_return_pct"], row["hybrid_return_pct"], row["buy_hold_pct"]],
        })
        fig = px.bar(compare_df, x="strategy", y="return_pct", title=f"{ticker} Return Comparison")
        st.plotly_chart(fig, use_container_width=True)
