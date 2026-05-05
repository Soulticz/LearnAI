from pathlib import Path
import json
import sys

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from money_tracker import ensure_portfolio_file, summarize_money
from buy_advisor import build_buy_advice
from money_ai import ask_money_ai

BACKTEST_FILE = ROOT / "backtest_summary.csv"
STRATEGY_FILE = ROOT / "strategy_modes.csv"
PORTFOLIO_FILE = ROOT / "paper_portfolio.json"

st.set_page_config(page_title="SoulQuant Home", page_icon="💰", layout="wide")

st.markdown(
    """
    <style>
    .hero {
        padding: 28px;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(34,197,94,.18), rgba(59,130,246,.12));
        border: 1px solid rgba(255,255,255,.12);
        margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-size: 2.4rem; }
    .hero p { margin-top: 8px; color: rgba(255,255,255,.72); font-size: 1.05rem; }
    .card {
        padding: 18px;
        border-radius: 18px;
        background: rgba(255,255,255,.045);
        border: 1px solid rgba(255,255,255,.11);
        min-height: 128px;
    }
    .card-title { font-size: .9rem; color: rgba(255,255,255,.62); margin-bottom: 8px; }
    .big-number { font-size: 1.9rem; font-weight: 800; }
    .subtle { color: rgba(255,255,255,.64); font-size: .9rem; }
    .pill { display:inline-block; padding:5px 12px; border-radius:999px; font-weight:700; }
    .green { background: rgba(34,197,94,.2); color:#86efac; }
    .yellow { background: rgba(234,179,8,.2); color:#fde68a; }
    .red { background: rgba(239,68,68,.2); color:#fca5a5; }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def risk_badge(high_risk_count: int, buy_score: int) -> tuple[str, str]:
    if high_risk_count > 0 or buy_score < 40:
        return "🔴 High Risk", "red"
    if buy_score < 70:
        return "🟡 Medium", "yellow"
    return "🟢 Healthy", "green"


strategy_df = load_csv(STRATEGY_FILE)
backtest_df = load_csv(BACKTEST_FILE)
paper_portfolio = load_json(PORTFOLIO_FILE)

personal_portfolio = ensure_portfolio_file()
money_summary = summarize_money(personal_portfolio)
buy_advice = build_buy_advice(money_summary)

risk_label, risk_class = risk_badge(
    int(money_summary.get("high_risk_count", 0)),
    int(buy_advice.get("score", 0)),
)

st.markdown(
    """
    <div class="hero">
        <h1>💰 SoulQuant Control Center</h1>
        <p>Personal investment dashboard • Portfolio checker • Buy readiness • AI advisor</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🧭 Navigation")
    st.caption("ใช้ sidebar ด้านซ้ายเพื่อไปหน้าเฉพาะทาง")
    st.info("แนะนำใช้งานหลัก: My Money → Daily Decision → Performance")
    st.divider()
    st.header("📦 Data Status")
    st.write("Personal Portfolio:", "✅")
    st.write("Strategy Modes:", "✅" if strategy_df is not None else "❌")
    st.write("Backtest:", "✅" if backtest_df is not None else "❌")
    st.write("Paper Portfolio:", "✅" if paper_portfolio is not None else "❌")
    if st.button("🔄 Refresh Home"):
        st.rerun()

# ===== Top KPI =====
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Total Personal Money</div>
            <div class="big-number">{money_summary['total_thb']:,.0f} ฿</div>
            <div class="subtle">Funds + Assets + Cash</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Buy Readiness</div>
            <div class="big-number">{buy_advice['score']}/100</div>
            <div class="subtle">{buy_advice['action']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Risk Status</div>
            <div class="big-number"><span class="pill {risk_class}">{risk_label}</span></div>
            <div class="subtle">Risk notes: {len(money_summary.get('risk_notes', []))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c4:
    assets_count = len(money_summary.get("assets", []))
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Assets Tracked</div>
            <div class="big-number">{assets_count}</div>
            <div class="subtle">Dime / Gold / ETF</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

left, right = st.columns([1.15, 1])

with left:
    st.subheader("🎯 Today Action")
    score = int(buy_advice.get("score", 0))
    if score >= 70:
        st.success(f"{buy_advice['verdict']} — ซื้อได้แค่ไม้เล็ก")
    elif score >= 40:
        st.warning(f"{buy_advice['verdict']} — ยังไม่ต้องรีบ")
    else:
        st.error(f"{buy_advice['verdict']} — ห้ามซื้อเพิ่มตอนนี้")

    st.markdown("**เหตุผลหลัก**")
    for reason in buy_advice.get("reasons", [])[:5]:
        st.write(f"• {reason}")

    candidates = buy_advice.get("candidates", [])
    if candidates:
        st.markdown("**ตัวที่น่าดูจาก Strategy**")
        st.dataframe(pd.DataFrame(candidates), use_container_width=True)
    else:
        st.caption("ยังไม่มีตัวที่ผ่านเงื่อนไขชัดเจน")

with right:
    st.subheader("⚠️ Risk Notes")
    for note in money_summary.get("risk_notes", [])[:5]:
        st.warning(note)

    st.subheader("🤖 Quick AI Advisor")
    question = st.text_input("ถาม AI", value="วันนี้ควรซื้อเพิ่มไหม ดูจากพอร์ตเรา")
    if st.button("วิเคราะห์ทันที"):
        with st.spinner("AI กำลังวิเคราะห์..."):
            st.info(ask_money_ai(question))

st.divider()

# ===== Portfolio composition =====
st.subheader("📊 Personal Portfolio")
fund_total = float(money_summary.get("fund_total_thb", 0))
asset_total = float(money_summary.get("asset_total_thb", 0))
cash = float(money_summary.get("cash_thb", 0))
composition_df = pd.DataFrame([
    {"type": "Funds", "amount": fund_total},
    {"type": "Assets", "amount": asset_total},
    {"type": "Cash", "amount": cash},
])
composition_df = composition_df[composition_df["amount"] > 0]

col_a, col_b = st.columns([1, 1])
with col_a:
    if not composition_df.empty:
        st.plotly_chart(px.pie(composition_df, values="amount", names="type", title="Money Allocation"), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลเงิน")
with col_b:
    assets = money_summary.get("assets", [])
    if assets:
        asset_df = pd.DataFrame(assets)
        cols = [c for c in ["ticker", "amount_thb", "current_price", "pnl_pct", "status", "action"] if c in asset_df.columns]
        st.dataframe(asset_df[cols], use_container_width=True)
    else:
        st.info("ยังไม่ได้กรอกหุ้น/ทองในหน้า My Money")

st.divider()

# ===== Strategy snapshot =====
st.subheader("🧭 Strategy Snapshot")
if strategy_df is not None and "mode" in strategy_df.columns:
    mode_counts = strategy_df["mode"].value_counts().reset_index()
    mode_counts.columns = ["mode", "count"]
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.dataframe(mode_counts, use_container_width=True)
    with col_s2:
        st.plotly_chart(px.bar(mode_counts, x="mode", y="count", title="Strategy Mode Count"), use_container_width=True)
else:
    st.warning("ยังไม่พบ strategy_modes.csv ให้รัน python strategy_selector.py ก่อน")

st.caption("หมายเหตุ: หน้า Home นี้เน้นสรุปเพื่อช่วยตัดสินใจ ส่วนรายละเอียดให้เข้า My Money, Daily Decision, Performance, Equity Curve จาก sidebar")
