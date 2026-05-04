from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
STRATEGY_FILE = ROOT / "strategy_modes.csv"

st.set_page_config(page_title="Daily Decision", page_icon="🎯", layout="wide")

st.title("🎯 Daily Decision")
st.caption("วันนี้ควรเทรดไหม ? ให้ระบบช่วยตัดสินใจ")

if not STRATEGY_FILE.exists():
    st.warning("ไม่พบไฟล์ strategy_modes.csv")
    st.stop()

df = pd.read_csv(STRATEGY_FILE)

st.write(df.head())
st.write(df.columns)

st.subheader(" Today Setup")

hybrid_df = df[df["mode"] == "HYBRID"].copy()
hold_df = df[df["mode"] == "HOLD"].copy()
watch_df = df[df["mode"] == "WATCH"].copy()
avoid_df = df[df["mode"] == "AVOID"].copy()

st.write("## HYBRID:", len(hybrid_df))
st.write("## HOLD:", len(hold_df))
st.write("## WATCH:", len(watch_df))
st.write("## AVOID:", len(avoid_df))
# ===== เลือกตัวที่ดีที่สุด =====
if not hybrid_df.empty:
    top = hybrid_df.sort_values("hybrid_alpha_vs_hold_pct", ascending=False).iloc[0]
    st.subheader("TOP PICKS:")
    st.success(f"({top['ticker']}) 🟢 เข้าซื้อ")

    st.write(f"Alpha: {top['hybrid_alpha_vs_hold_pct']:.2f}%")
    st.write(f"hybrid return: {top['hybrid_return_pct']:.2f}%")
    st.write(f"Reason: {top['reason']}")

    # ===== Action Logic =====
    alpha = top['hybrid_alpha_vs_hold_pct']
    if alpha > 20:
        action = "🔥 เข้าได้ 2 ไม้"
        risk = "🟢 ต่ำ"
    elif alpha > 5:
        action = "⚡ เข้าได้ 1 ไม้"
        risk = "🟡 กลาง"
    else:
        action = "🚫 รอจังหวะก่อน"
        risk = "🔴 สูงมาก"

    st.markdown("## MY ACTION")
    st.write("Action:",action)
    st.write("Risk:",risk)

else:
    st.write("ยังไม่มีหุ้น")