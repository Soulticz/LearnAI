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

st.set_page_config(page_title="My Money", page_icon="💰", layout="wide")

st.title("💰 My Money Dashboard")
st.caption("ดูพอร์ต + เพิ่ม/แก้ไขหุ้น ทอง กองทุน + AI + Buy Advisor")

# ===== Auto refresh =====
with st.sidebar:
    st.subheader("⏱ Refresh")
    auto_refresh = st.toggle("Auto refresh", value=True)
    refresh_minutes = st.selectbox("รอบเช็ก", [5, 10, 15, 30, 60], index=2)

    if auto_refresh:
        if st_autorefresh is not None:
            st_autorefresh(interval=refresh_minutes * 60 * 1000, key="my_money_auto_refresh")
            st.caption(f"รีเฟรชทุก {refresh_minutes} นาที")
        else:
            st.warning("ยังไม่ได้ติดตั้ง streamlit-autorefresh")
            st.code("pip install streamlit-autorefresh")

    if st.button("🔄 Refresh ตอนนี้"):
        st.rerun()


def save_personal_portfolio(portfolio: dict):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


def reload_data():
    portfolio = ensure_portfolio_file()
    summary = summarize_money(portfolio)
    return portfolio, summary


def ai_color(score: int) -> str:
    if score >= 75:
        return "🟢"
    if score >= 55:
        return "🔵"
    if score >= 40:
        return "🟡"
    return "🔴"


portfolio, summary = reload_data()

st.subheader("📊 Portfolio Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("เงินต้นรวม", f"{summary['asset_total_thb']:,.2f}")
col2.metric("มูลค่าปัจจุบัน", f"{summary['asset_market_total_thb']:,.2f}")
col3.metric("กำไร/ขาดทุน", f"{summary['asset_profit_thb']:+,.2f}", f"{summary['asset_profit_pct']:+.2f}%")
col4.metric("Cash", f"{summary['cash_thb']:,.2f}")

assets = summary.get("assets", [])

if assets:
    best_profit = max(assets, key=lambda x: x.get("pnl_pct", -9999) if x.get("pnl_pct") is not None else -9999)
    best_ai = max(assets, key=lambda x: x.get("ai_score", 0))
    worst_asset = min(assets, key=lambda x: x.get("pnl_pct", 9999) if x.get("pnl_pct") is not None else 9999)

    st.subheader("🔥 Highlights")
    h1, h2, h3 = st.columns(3)

    with h1:
        st.success(
            f"🏆 Best Performer\n\n{best_profit.get('ticker')}\n{best_profit.get('pnl_pct', 0):+.2f}%"
        )

    with h2:
        st.info(
            f"🤖 Highest AI Score\n\n{best_ai.get('ticker')}\n{best_ai.get('ai_score', 0)}/100"
        )

    with h3:
        st.error(
            f"⚠️ Highest Risk\n\n{worst_asset.get('ticker')}\n{worst_asset.get('pnl_pct', 0):+.2f}%"
        )

st.divider()

# =========================
# Add / update portfolio
# =========================
st.subheader("➕ เพิ่ม/อัปเดตรายการลงทุน")

with st.form("add_asset_form"):
    item_type = st.selectbox("ประเภท", ["หุ้น/ทอง/ETF (Dime)", "กองทุน", "เงินสด"])

    if item_type == "หุ้น/ทอง/ETF (Dime)":
        c1, c2 = st.columns(2)
        with c1:
            ticker = st.text_input("Ticker เช่น AAPL, SNDK, GC=F", value="")
            name = st.text_input("ชื่อเรียก เช่น Apple, YLG GOLD 99.99", value="")
            qty = st.number_input(
                "จำนวนที่ถือ เช่น หุ้น / oz",
                min_value=0.0,
                value=0.0,
                step=0.000001,
                format="%.6f",
            )

        with c2:
            amount_thb = st.number_input("เงินที่ลงไว้ (บาท)", min_value=0.0, value=0.0, step=100.0)
            avg_price = st.number_input("ราคาซื้อเฉลี่ย", min_value=0.0, value=0.0, step=0.01)
            current_price_manual = st.number_input(
                "ราคาปัจจุบันแบบกรอกเอง",
                min_value=0.0,
                value=0.0,
                step=0.01,
            )

        submitted = st.form_submit_button("บันทึกหุ้น/ทอง")
        if submitted:
            if not ticker.strip():
                st.error("กรุณากรอก ticker ก่อน")
            else:
                new_asset = {
                    "ticker": ticker.upper().strip(),
                    "name": name.strip() or ticker.upper().strip(),
                    "amount_thb": float(amount_thb),
                    "qty": float(qty),
                    "avg_price": float(avg_price),
                }

                if current_price_manual > 0:
                    new_asset["current_price_manual"] = float(current_price_manual)

                assets_portfolio = portfolio.setdefault("assets", [])
                updated = False
                for idx, asset in enumerate(assets_portfolio):
                    if str(asset.get("ticker", "")).upper() == new_asset["ticker"]:
                        assets_portfolio[idx] = new_asset
                        updated = True
                        break

                if not updated:
                    assets_portfolio.append(new_asset)

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
            funds = portfolio.setdefault("funds", [])
            updated = False
            for idx, fund in enumerate(funds):
                if str(fund.get("name", "")).upper() == new_fund["name"].upper():
                    funds[idx] = new_fund
                    updated = True
                    break
            if not updated:
                funds.append(new_fund)
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
    st.dataframe(pd.DataFrame(funds), use_container_width=True)
else:
    st.info("ยังไม่มีกองทุน")

st.subheader("📊 AI Assets")

if assets:
    for asset in assets:
        ticker = asset.get("ticker", "N/A")
        name = asset.get("name", ticker)
        ai_score = int(asset.get("ai_score", 0))
        pnl_pct = asset.get("pnl_pct")
        trend = asset.get("trend", "N/A")
        commentary = asset.get("ai_commentary", "")
        current_price = asset.get("current_price")
        avg_price = asset.get("avg_price")
        rsi = asset.get("rsi")
        volatility = asset.get("volatility_pct")

        pnl_text = "N/A" if pnl_pct is None else f"{pnl_pct:+.2f}%"
        current_text = "N/A" if current_price is None else f"{current_price:,.2f}"

        with st.container(border=True):
            top1, top2, top3 = st.columns([2, 1, 1])

            with top1:
                st.markdown(f"### {ticker}")
                st.caption(name)

            with top2:
                st.metric("P/L", pnl_text)

            with top3:
                st.metric("AI Score", f"{ai_score}/100")
                st.caption(f"{ai_color(ai_score)} {trend}")

            st.write(commentary)

            with st.expander(f"ดูรายละเอียด {ticker}"):
                d1, d2, d3 = st.columns(3)

                with d1:
                    st.write(f"💰 เงินต้น: {asset.get('amount_thb', 0):,.2f} บาท")
                    st.write(f"📈 ราคาปัจจุบัน: {current_text}")
                    st.write(f"📊 Avg Price: {avg_price:,.2f}")

                with d2:
                    st.write(f"⚡ RSI: {rsi}")
                    st.write(f"📉 Volatility: {volatility}%")
                    st.write(f"📈 Trend: {trend}")

                with d3:
                    st.write(f"🤖 Status: {asset.get('status')} ")
                    st.write(f"🎯 Action: {asset.get('action')} ")
                    st.write(f"💵 มูลค่าปัจจุบัน: {asset.get('estimated_value_thb', 0):,.2f} บาท")
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

st.subheader("🎯 Buy Advisor")
if st.button("ประเมินการซื้อ"):
    advice = build_buy_advice(summary)
    st.info(format_buy_advice(advice))

st.subheader("🤖 AI Advisor")
question = st.text_input("ถาม AI เกี่ยวกับพอร์ต", value="ช่วยวิเคราะห์พอร์ตของเราหน่อย")
if st.button("วิเคราะห์พอร์ต"):
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
    st.caption("✅ บันทึกคำตอบ AI ลง ai_decision_log.json แล้ว")

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
