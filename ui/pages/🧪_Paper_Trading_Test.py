from pathlib import Path
import sys

import streamlit as st
import yfinance as yf
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from paper_trading import (
    load_portfolio,
    save_portfolio,
    paper_buy,
    paper_sell,
    format_portfolio_summary,
)

PORTFOLIO_FILE = ROOT / "paper_portfolio.json"
DEFAULT_TICKERS = ["META", "CRM", "QCOM", "COIN", "NVDA", "AAPL", "SPY", "QQQ"]

st.set_page_config(page_title="Paper Trading Test", page_icon="🧪", layout="wide")
st.title("🧪 Paper Trading Test")
st.caption("ใช้สำหรับทดสอบซื้อ/ขายจำลอง เพื่อดูว่า Paper Portfolio เปลี่ยนจริงไหม")


@st.cache_data(ttl=300)
def get_latest_price(ticker: str) -> float | None:
    data = yf.download(ticker, period="5d", interval="1d", progress=False)
    if data.empty:
        return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.columns = data.columns.str.lower()
    return float(data["close"].iloc[-1])


def show_portfolio():
    portfolio = load_portfolio(str(PORTFOLIO_FILE))
    st.code(format_portfolio_summary(portfolio))

    positions = portfolio.get("positions", {})
    if positions:
        rows = []
        for ticker, pos in positions.items():
            rows.append({
                "ticker": ticker,
                "shares": float(pos.get("shares", 0)),
                "avg_price": float(pos.get("avg_price", 0)),
                "last_price": float(pos.get("last_price", 0)),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    trades = portfolio.get("trades", [])
    if trades:
        st.subheader("Recent Trades")
        st.dataframe(pd.DataFrame(trades).tail(20), use_container_width=True)


st.subheader("🎮 Test Controls")
col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.selectbox("Ticker", DEFAULT_TICKERS)

with col2:
    price_mode = st.radio("Price", ["Latest from yfinance", "Manual"], horizontal=False)

with col3:
    manual_price = st.number_input("Manual price", min_value=0.01, value=100.0, step=1.0)

price = get_latest_price(ticker) if price_mode == "Latest from yfinance" else manual_price
if price is None:
    st.warning("ดึงราคาล่าสุดไม่สำเร็จ ใช้ Manual price แทนได้")
else:
    st.metric(f"{ticker} price", f"{price:,.2f}")

buy_col, sell_col, refresh_col = st.columns(3)

with buy_col:
    if st.button("🟢 Test BUY", use_container_width=True):
        portfolio = load_portfolio(str(PORTFOLIO_FILE))
        ok, msg = paper_buy(
            portfolio=portfolio,
            ticker=ticker,
            price=float(price or manual_price),
            reason="Manual UI test buy",
        )
        save_portfolio(portfolio, str(PORTFOLIO_FILE))
        if ok:
            st.success(msg)
        else:
            st.warning(msg)
        st.rerun()

with sell_col:
    if st.button("🔴 Test SELL", use_container_width=True):
        portfolio = load_portfolio(str(PORTFOLIO_FILE))
        ok, msg = paper_sell(
            portfolio=portfolio,
            ticker=ticker,
            price=float(price or manual_price),
            reason="Manual UI test sell",
        )
        save_portfolio(portfolio, str(PORTFOLIO_FILE))
        if ok:
            st.success(msg)
        else:
            st.warning(msg)
        st.rerun()

with refresh_col:
    if st.button("🔄 Refresh", use_container_width=True):
        get_latest_price.clear()
        st.rerun()

st.divider()
st.subheader("📒 Current Paper Portfolio")
show_portfolio()

st.info(
    "หน้านี้เป็นปุ่มทดสอบเท่านั้น ใช้เงินจำลองจาก paper_portfolio.json ไม่เกี่ยวกับเงินจริงค่ะ"
)
