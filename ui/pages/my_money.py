import json
from pathlib import Path

import pandas as pd
import streamlit as st

from money_tracker import ensure_portfolio_file, summarize_money, PORTFOLIO_FILE
from money_ai import ask_money_ai
from buy_advisor import build_buy_advice, format_buy_advice

st.set_page_config(page_title="My Money", page_icon="💰", layout="wide")


st.title("💰 My Money Dashboard")
st.caption("ดูพอร์ต + เพิ่ม/แก้ไขหุ้น ทอง กองทุน และวิเคราะห์ด้วย AI")


def save_personal_portfolio(portfolio: dict):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


def reload_data():
    portfolio = ensure_portfolio_file()
    summary = summarize_money(portfolio)
    return portfolio, summary


portfolio, summary = reload_data()

st.subheader("💡 Buy Advisor")
if st.button("ประเมินซิ้อ"):
    advice = build_buy_advice(summary)
    st.info(format_buy_advice(advice))

st.subheader("📊 Portfolio Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total", f"{summary['total_thb']:,.2f}")
col2.metric("Cash", f"{summary['cash_thb']:,.2f}")
col3.metric("Funds", f"{summary['fund_total_thb']:,.2f}")
col4.metric("Assets", f"{summary['asset_total_thb']:,.2f}")

st.divider()

# =========================
# Add / update portfolio
# =========================
st.subheader("➕ เพิ่มรายการลงทุน")

with st.form("add_asset_form"):
    item_type = st.selectbox("ประเภท", ["หุ้น/ทอง/ETF (Dime)", "กองทุน", "เงินสด"])

    if item_type == "หุ้น/ทอง/ETF (Dime)":
        c1, c2 = st.columns(2)
        with c1:
            ticker = st.text_input("Ticker เช่น AAPL, SNDK, GLD, GC=F", value="")
            name = st.text_input("ชื่อเรียก เช่น Apple, Gold", value="")
        with c2:
            amount_thb = st.number_input("เงินที่ลงไว้ (บาท)", min_value=0.0, value=0.0, step=100.0)
            avg_price = st.number_input("ราคาซื้อเฉลี่ย", min_value=0.0, value=0.0, step=1.0)

        submitted = st.form_submit_button("บันทึกหุ้น/ทอง")
        if submitted:
            if not ticker.strip():
                st.error("กรุณากรอก ticker ก่อน")
            else:
                new_asset = {
                    "ticker": ticker.upper().strip(),
                    "name": name.strip() or ticker.upper().strip(),
                    "amount_thb": float(amount_thb),
                    "avg_price": float(avg_price),
                }
                portfolio.setdefault("assets", []).append(new_asset)
                save_personal_portfolio(portfolio)
                st.success(f"บันทึก {new_asset['ticker']} แล้ว")
                st.rerun()

    elif item_type == "กองทุน":
        c1, c2 = st.columns(2)
        with c1:
            fund_name = st.text_input("ชื่อกองทุน เช่น TSP5", value="TSP5")
            fund_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, value=2000.0, step=100.0)
        with c2:
            fund_note = st.text_input("หมายเหตุ", value="กองทุนรวม ถือยาว ไม่ต้องดูรายวัน")

        submitted = st.form_submit_button("บันทึกกองทุน")
        if submitted:
            new_fund = {
                "name": fund_name.strip() or "Fund",
                "amount_thb": float(fund_amount),
                "note": fund_note.strip(),
            }
            portfolio.setdefault("funds", []).append(new_fund)
            save_personal_portfolio(portfolio)
            st.success(f"บันทึกกองทุน {new_fund['name']} แล้ว")
            st.rerun()

    else:
        cash = st.number_input("เงินสด (บาท)", min_value=0.0, value=float(portfolio.get("cash_thb", 0)), step=100.0)
        submitted = st.form_submit_button("อัปเดตเงินสด")
        if submitted:
            portfolio["cash_thb"] = float(cash)
            save_personal_portfolio(portfolio)
            st.success("อัปเดตเงินสดแล้ว")
            st.rerun()

st.divider()

# =========================
# Current data
# =========================
st.subheader("🐢 Funds")
funds = portfolio.get("funds", [])
if funds:
    fund_df = pd.DataFrame(funds)
    st.dataframe(fund_df, use_container_width=True)
else:
    st.info("ยังไม่มีกองทุน")

st.subheader("📊 Assets")
assets = summary.get("assets", [])
if assets:
    asset_df = pd.DataFrame(assets)
    st.dataframe(asset_df, use_container_width=True)
else:
    st.info("ยังไม่ได้กรอกหุ้น/ทอง")

st.subheader("🗑️ ลบรายการ")
col_a, col_b = st.columns(2)
with col_a:
    asset_options = [a.get("ticker", "") for a in portfolio.get("assets", [])]
    if asset_options:
        delete_asset = st.selectbox("ลบหุ้น/ทอง", asset_options)
        if st.button("ลบหุ้น/ทองที่เลือก"):
            portfolio["assets"] = [a for a in portfolio.get("assets", []) if a.get("ticker") != delete_asset]
            save_personal_portfolio(portfolio)
            st.success(f"ลบ {delete_asset} แล้ว")
            st.rerun()
    else:
        st.caption("ไม่มีหุ้น/ทองให้ลบ")

with col_b:
    fund_options = [f.get("name", "") for f in portfolio.get("funds", [])]
    if fund_options:
        delete_fund = st.selectbox("ลบกองทุน", fund_options)
        if st.button("ลบกองทุนที่เลือก"):
            portfolio["funds"] = [f for f in portfolio.get("funds", []) if f.get("name") != delete_fund]
            save_personal_portfolio(portfolio)
            st.success(f"ลบ {delete_fund} แล้ว")
            st.rerun()
    else:
        st.caption("ไม่มีกองทุนให้ลบ")

st.divider()

st.subheader("⚠️ Risk Notes")
for note in summary["risk_notes"]:
    st.warning(note)

st.subheader("🤖 AI Advisor")
question = st.text_input("ถาม AI เกี่ยวกับพอร์ต", value="ช่วยวิเคราะห์พอร์ตของเราหน่อย")
if st.button("วิเคราะห์พอร์ต"):
    result = ask_money_ai(question)
    st.success(result)

with st.expander("ดู/แก้ raw JSON"):
    raw = st.text_area("personal_portfolio.json", json.dumps(portfolio, ensure_ascii=False, indent=2), height=320)
    if st.button("บันทึก raw JSON"):
        try:
            new_data = json.loads(raw)
            save_personal_portfolio(new_data)
            st.success("บันทึก raw JSON แล้ว")
            st.rerun()
        except json.JSONDecodeError as e:
            st.error(f"JSON ไม่ถูกต้อง: {e}")

