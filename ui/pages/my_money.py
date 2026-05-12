import json

import pandas as pd
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

from money_tracker import ensure_portfolio_file, summarize_money, PORTFOLIO_FILE
from money_ai import ask_money_ai
from buy_advisor import build_buy_advice, format_buy_advice
from decision_tracker import log_ai_decision
from gold_portfolio import summarize_gold_portfolio

st.set_page_config(page_title="My Money", page_icon="💰", layout="wide")
st.title("💰 My Money Dashboard")
st.caption("Portfolio, Gold, AI Advisor, Buy Advisor")

with st.sidebar:
    st.subheader("Refresh")
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_minutes = st.selectbox("Interval", [5, 10, 15, 30, 60], index=2)
    if auto_refresh and st_autorefresh is not None:
        st_autorefresh(interval=refresh_minutes * 60 * 1000, key="my_money_auto_refresh")
    if st.button("Refresh now"):
        st.rerun()


def save_personal_portfolio(portfolio: dict):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


portfolio = ensure_portfolio_file()
summary = summarize_money(portfolio)
gold_summary = summarize_gold_portfolio(summary)
assets = summary.get("assets", [])

st.subheader("Portfolio Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", f"{summary.get('total_thb', 0):,.2f} THB")
c2.metric("Cash", f"{summary.get('cash_thb', 0):,.2f} THB")
c3.metric("Asset Value", f"{summary.get('asset_market_total_thb', 0):,.2f} THB")
c4.metric("P/L", f"{summary.get('asset_profit_thb', 0):+,.2f} THB", f"{summary.get('asset_profit_pct', 0):+.2f}%")

st.subheader("Gold Portfolio")
g1, g2, g3, g4 = st.columns(4)
g1.metric("Gold items", gold_summary.get("gold_count", 0))
g2.metric("Gold value", f"{gold_summary.get('gold_value_thb', 0):,.2f} THB")
g3.metric("Gold P/L", f"{gold_summary.get('gold_profit_thb', 0):+,.2f} THB", f"{gold_summary.get('gold_profit_pct', 0):+.2f}%")
g4.metric("Gold weight", f"{gold_summary.get('gold_weight_pct', 0):.2f}%")

for note in gold_summary.get("risk_notes", []):
    st.warning(note)

if gold_summary.get("gold_assets"):
    st.dataframe(pd.DataFrame(gold_summary["gold_assets"]), use_container_width=True)
else:
    st.info("No gold assets yet. Add GC=F, GLD, YLG-GOLD, or set type = gold.")

st.divider()

st.subheader("Add / Update item")
with st.form("add_item_form"):
    item_type = st.selectbox("Type", ["Asset", "Fund", "Cash"])

    if item_type == "Asset":
        a1, a2 = st.columns(2)
        with a1:
            ticker = st.text_input("Ticker", value="")
            name = st.text_input("Name", value="")
            asset_type = st.selectbox("Asset type", ["auto", "stock", "gold", "crypto", "etf"])
            qty = st.number_input("Quantity", min_value=0.0, value=0.0, step=0.000001, format="%.6f")
        with a2:
            amount_thb = st.number_input("Cost amount THB", min_value=0.0, value=0.0, step=100.0)
            avg_price = st.number_input("Average price", min_value=0.0, value=0.0, step=0.01)
            current_price_manual = st.number_input("Manual current price", min_value=0.0, value=0.0, step=0.01)

        submitted = st.form_submit_button("Save asset")
        if submitted:
            if not ticker.strip():
                st.error("Please enter ticker")
            else:
                new_asset = {
                    "ticker": ticker.upper().strip(),
                    "name": name.strip() or ticker.upper().strip(),
                    "amount_thb": float(amount_thb),
                    "qty": float(qty),
                    "avg_price": float(avg_price),
                }
                if asset_type != "auto":
                    new_asset["type"] = asset_type
                if current_price_manual > 0:
                    new_asset["current_price_manual"] = float(current_price_manual)

                asset_list = portfolio.setdefault("assets", [])
                for idx, old_asset in enumerate(asset_list):
                    if str(old_asset.get("ticker", "")).upper() == new_asset["ticker"]:
                        asset_list[idx] = new_asset
                        break
                else:
                    asset_list.append(new_asset)

                save_personal_portfolio(portfolio)
                st.success("Saved")
                st.rerun()

    elif item_type == "Fund":
        fund_name = st.text_input("Fund name", value="TSP5")
        fund_amount = st.number_input("Amount THB", min_value=0.0, value=2000.0, step=100.0)
        fund_note = st.text_input("Note", value="Hold long term")
        submitted = st.form_submit_button("Save fund")
        if submitted:
            new_fund = {"name": fund_name.strip() or "Fund", "amount_thb": float(fund_amount), "note": fund_note.strip()}
            funds = portfolio.setdefault("funds", [])
            for idx, old_fund in enumerate(funds):
                if str(old_fund.get("name", "")).upper() == new_fund["name"].upper():
                    funds[idx] = new_fund
                    break
            else:
                funds.append(new_fund)
            save_personal_portfolio(portfolio)
            st.success("Saved")
            st.rerun()

    else:
        cash = st.number_input("Cash THB", min_value=0.0, value=float(portfolio.get("cash_thb", 0)), step=100.0)
        submitted = st.form_submit_button("Save cash")
        if submitted:
            portfolio["cash_thb"] = float(cash)
            save_personal_portfolio(portfolio)
            st.success("Saved")
            st.rerun()

st.divider()

st.subheader("Funds")
funds = portfolio.get("funds", [])
if funds:
    st.dataframe(pd.DataFrame(funds), use_container_width=True)
else:
    st.info("No funds")

st.subheader("Assets")
if assets:
    st.dataframe(pd.DataFrame(assets), use_container_width=True)
else:
    st.info("No assets")

st.subheader("Delete item")
d1, d2 = st.columns(2)
with d1:
    asset_options = [a.get("ticker", "") for a in portfolio.get("assets", [])]
    if asset_options:
        delete_asset = st.selectbox("Delete asset", asset_options)
        if st.button("Delete selected asset"):
            portfolio["assets"] = [a for a in portfolio.get("assets", []) if a.get("ticker") != delete_asset]
            save_personal_portfolio(portfolio)
            st.rerun()
with d2:
    fund_options = [f.get("name", "") for f in portfolio.get("funds", [])]
    if fund_options:
        delete_fund = st.selectbox("Delete fund", fund_options)
        if st.button("Delete selected fund"):
            portfolio["funds"] = [f for f in portfolio.get("funds", []) if f.get("name") != delete_fund]
            save_personal_portfolio(portfolio)
            st.rerun()

st.divider()

st.subheader("Risk Notes")
for note in summary.get("risk_notes", []):
    st.warning(note)

st.subheader("Buy Advisor")
if st.button("Evaluate buy readiness"):
    advice = build_buy_advice(summary)
    st.info(format_buy_advice(advice))

st.subheader("AI Advisor")
question = st.text_input("Question", value="ช่วยวิเคราะห์พอร์ตของเราหน่อย")
if st.button("Analyze portfolio"):
    result = ask_money_ai(question)
    st.success(result)
    advice = build_buy_advice(summary)
    log_ai_decision(
        source="my_money",
        question=question,
        answer=result,
        buy_score=int(advice.get("score", 0)),
        action=str(advice.get("action", "UNKNOWN")),
        total_thb=float(summary.get("total_thb", 0)),
    )
    st.caption("Logged to ai_decision_log.json")

with st.expander("Raw JSON"):
    raw = st.text_area("personal_portfolio.json", json.dumps(portfolio, ensure_ascii=False, indent=2), height=320)
    if st.button("Save raw JSON"):
        try:
            new_data = json.loads(raw)
            save_personal_portfolio(new_data)
            st.success("Saved")
            st.rerun()
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
