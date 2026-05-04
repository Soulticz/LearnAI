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
df["mode"] = df["mode"].astype(str).str.upper().str.strip()

st.subheader("📊 Today Setup")

hybrid_df = df[df["mode"] == "HYBRID"].copy()
hold_df = df[df["mode"] == "HOLD"].copy()
watch_df = df[df["mode"] == "WATCH"].copy()
avoid_df = df[df["mode"] == "AVOID"].copy()

c1, c2, c3, c4 = st.columns(4)
c1.metric("HYBRID", len(hybrid_df))
c2.metric("HOLD", len(hold_df))
c3.metric("WATCH", len(watch_df))
c4.metric("AVOID", len(avoid_df))

st.divider()

# ===== เลือกหุ้นที่ปลอดภัยพอ =====
# เงื่อนไขสำคัญ:
# 1) Hybrid return ต้องเป็นบวก
# 2) Drawdown ต้องไม่หนักเกิน -25%
safe_df = hybrid_df[
    (hybrid_df["hybrid_return_pct"] > 0) &
    (hybrid_df["hybrid_max_drawdown_pct"] > -25)
].copy()

if not safe_df.empty:
    top = safe_df.sort_values(
        "hybrid_alpha_vs_hold_pct",
        ascending=False
    ).iloc[0]

    st.subheader("🎯 TOP PICK")
    st.success(f"วันนี้น่าสนใจ: {top['ticker']} 🟢")

    col1, col2, col3 = st.columns(3)
    col1.metric("Alpha", f"{top['hybrid_alpha_vs_hold_pct']:.2f}%")
    col2.metric("Hybrid Return", f"{top['hybrid_return_pct']:.2f}%")
    col3.metric("Drawdown", f"{top['hybrid_max_drawdown_pct']:.2f}%")

    st.info(f"Reason: {top['reason']}")

    alpha = float(top["hybrid_alpha_vs_hold_pct"])

    if alpha > 20:
        action = "🔥 เข้าได้ 2 ไม้"
        risk = "🟢 ต่ำ"
    elif alpha > 5:
        action = "⚡ เข้าได้ 1 ไม้"
        risk = "🟡 กลาง"
    else:
        action = "🚫 รอจังหวะก่อน"
        risk = "🔴 สูง"

    st.markdown("## 📌 MY ACTION")
    st.write("Action:", action)
    st.write("Risk:", risk)

    with st.expander("ดูหุ้นที่ผ่านเงื่อนไขทั้งหมด"):
        st.dataframe(safe_df, use_container_width=True)
else:
    st.warning("วันนี้ยังไม่มีหุ้นที่เข้าเงื่อนไขปลอดภัยพอ — ไม่ต้องเทรด")
    st.caption("เกณฑ์ตอนนี้: Hybrid Return > 0 และ Drawdown > -25%")

    if not hybrid_df.empty:
        with st.expander("ดู HYBRID ทั้งหมดที่ยังไม่ผ่าน safe filter"):
            st.dataframe(hybrid_df, use_container_width=True)
