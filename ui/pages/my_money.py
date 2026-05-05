import streamlit as st
from money_tracker import ensure_portfolio_file, summarize_money
from money_ai import ask_money_ai

st.set_page_config(page_title="My Money", page_icon="💰", layout="wide")

st.title("💰 My Money Dashboard")
st.caption("ดูพอร์ต + วิเคราะห์ด้วย AI")

portfolio = ensure_portfolio_file()
summary = summarize_money(portfolio)

st.subheader("📊 Portfolio Overview")

col1, col2, col3 = st.columns(3)
col1.metric("Total", f"{summary['total_thb']:,.2f}")
col2.metric("Funds", f"{summary['fund_total_thb']:,.2f}")
col3.metric("Assets", f"{summary['asset_total_thb']:,.2f}")

st.subheader("📊 Assets")
for asset in summary["assets"]:
    pnl = asset.get("pnl_pct")
    pnl_text = "N/A" if pnl is None else f"{pnl:+.2f}%"
    st.write(f"{asset['ticker']} → {pnl_text} | {asset['action']}")

st.subheader("⚠️ Risk Notes")
for note in summary["risk_notes"]:
    st.warning(note)

st.subheader("🤖 AI Advisor")
if st.button("วิเคราะห์พอร์ต"):
    result = ask_money_ai()
    st.success(result)
