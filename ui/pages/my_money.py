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

st.set_page_config(page_title="Soul AI Portfolio", page_icon="💰", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #1f2a44 0, #0f172a 34%, #020617 100%);
        color: #e5e7eb;
    }
    .main .block-container {
        padding-top: 2rem;
        max-width: 1220px;
    }
    .hero-card {
        padding: 28px 30px;
        border-radius: 26px;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.22), rgba(168, 85, 247, 0.18));
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 24px 70px rgba(2, 6, 23, 0.34);
        margin-bottom: 22px;
    }
    .hero-title {
        font-size: 2.35rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 4px;
    }
    .hero-subtitle {
        color: #cbd5e1;
        font-size: 1rem;
        max-width: 760px;
    }
    .metric-card {
        padding: 20px;
        border-radius: 22px;
        background: rgba(15, 23, 42, 0.74);
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 12px 34px rgba(2, 6, 23, 0.22);
        min-height: 116px;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.03em;
    }
    .metric-delta-positive { color: #4ade80; font-weight: 700; }
    .metric-delta-negative { color: #fb7185; font-weight: 700; }
    .metric-delta-neutral { color: #cbd5e1; font-weight: 700; }
    .section-title {
        font-size: 1.25rem;
        font-weight: 800;
        margin: 18px 0 10px 0;
    }
    .highlight-card {
        padding: 18px 20px;
        border-radius: 20px;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        min-height: 130px;
    }
    .highlight-label {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 8px;
    }
    .highlight-main {
        font-size: 1.35rem;
        font-weight: 800;
    }
    .highlight-sub {
        color: #cbd5e1;
        margin-top: 4px;
    }
    .asset-card {
        padding: 22px;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.72));
        border: 1px solid rgba(148, 163, 184, 0.2);
        box-shadow: 0 16px 38px rgba(2, 6, 23, 0.23);
        margin-bottom: 16px;
    }
    .asset-symbol {
        font-size: 1.45rem;
        font-weight: 850;
        letter-spacing: -0.03em;
    }
    .asset-name {
        color: #94a3b8;
        font-size: 0.92rem;
    }
    .pill {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.16);
        border: 1px solid rgba(96, 165, 250, 0.24);
        color: #bfdbfe;
        font-size: 0.86rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .ai-comment {
        color: #e2e8f0;
        line-height: 1.65;
        margin-top: 12px;
        padding: 14px 16px;
        border-radius: 16px;
        background: rgba(2, 6, 23, 0.32);
        border: 1px solid rgba(148, 163, 184, 0.12);
    }
    div[data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.62);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 18px;
        padding: 14px 16px;
    }
    div[data-testid="stExpander"] {
        background: rgba(15, 23, 42, 0.62);
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.16);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">💰 Soul AI Portfolio</div>
        <div class="hero-subtitle">
            Dashboard สำหรับดูพอร์ตจริง วิเคราะห์ AI Score, RSI, Trend, Volatility และ Investor Memory ในที่เดียว
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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


def fmt_money(value: float) -> str:
    return f"{float(value or 0):,.2f}"


def fmt_pct(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):+.2f}%"


def metric_card(label: str, value: str, delta: str | None = None, positive: bool | None = None):
    if positive is True:
        delta_class = "metric-delta-positive"
    elif positive is False:
        delta_class = "metric-delta-negative"
    else:
        delta_class = "metric-delta-neutral"

    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


portfolio, summary = reload_data()
assets = summary.get("assets", [])

st.markdown('<div class="section-title">📊 Portfolio Overview</div>', unsafe_allow_html=True)
profit = float(summary.get("asset_profit_thb", 0) or 0)
profit_pct = float(summary.get("asset_profit_pct", 0) or 0)

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("เงินต้นหุ้น/ทอง", f"{fmt_money(summary['asset_total_thb'])} ฿")
with col2:
    metric_card("มูลค่าปัจจุบัน", f"{fmt_money(summary['asset_market_total_thb'])} ฿")
with col3:
    metric_card("กำไร/ขาดทุน", f"{profit:+,.2f} ฿", f"{profit_pct:+.2f}%", profit >= 0)
with col4:
    metric_card("Cash", f"{fmt_money(summary['cash_thb'])} ฿")

if assets:
    best_profit = max(assets, key=lambda x: x.get("pnl_pct", -9999) if x.get("pnl_pct") is not None else -9999)
    best_ai = max(assets, key=lambda x: x.get("ai_score", 0))
    worst_asset = min(assets, key=lambda x: x.get("pnl_pct", 9999) if x.get("pnl_pct") is not None else 9999)

    st.markdown('<div class="section-title">🔥 Highlights</div>', unsafe_allow_html=True)
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(
            f"""
            <div class="highlight-card">
                <div class="highlight-label">🏆 Best Performer</div>
                <div class="highlight-main">{best_profit.get('ticker')}</div>
                <div class="highlight-sub">{fmt_pct(best_profit.get('pnl_pct'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            f"""
            <div class="highlight-card">
                <div class="highlight-label">🤖 Highest AI Score</div>
                <div class="highlight-main">{best_ai.get('ticker')}</div>
                <div class="highlight-sub">{best_ai.get('ai_score', 0)}/100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            f"""
            <div class="highlight-card">
                <div class="highlight-label">⚠️ Highest Risk</div>
                <div class="highlight-main">{worst_asset.get('ticker')}</div>
                <div class="highlight-sub">{fmt_pct(worst_asset.get('pnl_pct'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# =========================
# Add / update portfolio
# =========================
st.markdown('<div class="section-title">➕ เพิ่ม/อัปเดตรายการลงทุน</div>', unsafe_allow_html=True)

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
st.markdown('<div class="section-title">🐢 Funds</div>', unsafe_allow_html=True)
funds = portfolio.get("funds", [])
if funds:
    st.dataframe(pd.DataFrame(funds), use_container_width=True)
else:
    st.info("ยังไม่มีกองทุน")

st.markdown('<div class="section-title">📊 AI Assets</div>', unsafe_allow_html=True)

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
        estimated_value = asset.get("estimated_value_thb", 0)
        profit_thb = float(asset.get("profit_thb", 0) or 0)

        pnl_text = fmt_pct(pnl_pct)
        current_text = "N/A" if current_price is None else f"{current_price:,.2f}"
        profit_class = "metric-delta-positive" if profit_thb >= 0 else "metric-delta-negative"

        st.markdown(
            f"""
            <div class="asset-card">
                <div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:flex-start;">
                    <div>
                        <div class="asset-symbol">{ai_color(ai_score)} {ticker}</div>
                        <div class="asset-name">{name}</div>
                        <div style="margin-top:10px;">
                            <span class="pill">AI {ai_score}/100</span>
                            <span class="pill">Trend: {trend}</span>
                            <span class="pill">P/L {pnl_text}</span>
                        </div>
                    </div>
                    <div style="text-align:right; min-width:190px;">
                        <div class="metric-label">มูลค่าปัจจุบัน</div>
                        <div class="metric-value">{float(estimated_value or 0):,.2f} ฿</div>
                        <div class="{profit_class}">{profit_thb:+,.2f} ฿</div>
                    </div>
                </div>
                <div class="ai-comment">💡 {commentary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"ดูรายละเอียด {ticker}"):
            d1, d2, d3 = st.columns(3)

            with d1:
                st.write(f"💰 เงินต้น: {asset.get('amount_thb', 0):,.2f} บาท")
                st.write(f"📈 ราคาปัจจุบัน: {current_text}")
                st.write(f"📊 Avg Price: {float(avg_price or 0):,.2f}")

            with d2:
                st.write(f"⚡ RSI: {rsi}")
                st.write(f"📉 Volatility: {volatility}%")
                st.write(f"📈 Trend: {trend}")

            with d3:
                st.write(f"🤖 Status: {asset.get('status')} ")
                st.write(f"🎯 Action: {asset.get('action')} ")
                st.write(f"💵 มูลค่าปัจจุบัน: {float(estimated_value or 0):,.2f} บาท")
else:
    st.info("ยังไม่ได้กรอกหุ้น/ทอง")

st.markdown('<div class="section-title">🗑️ ลบรายการ</div>', unsafe_allow_html=True)
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

st.markdown('<div class="section-title">⚠️ Risk Notes</div>', unsafe_allow_html=True)
for note in summary["risk_notes"]:
    st.warning(note)

st.markdown('<div class="section-title">🎯 Buy Advisor</div>', unsafe_allow_html=True)
if st.button("ประเมินการซื้อ"):
    advice = build_buy_advice(summary)
    st.info(format_buy_advice(advice))

st.markdown('<div class="section-title">🤖 AI Advisor</div>', unsafe_allow_html=True)
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
