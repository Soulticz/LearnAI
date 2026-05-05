import streamlit as st
import pandas as pd

from decision_tracker import load_decision_log, summarize_decisions, update_decision_result
from ai_adaptive import get_ai_adaptive_profile

st.set_page_config(page_title="AI Performance", page_icon="🧠", layout="wide")

st.title("🧠 AI Performance Dashboard")
st.caption("วัดความแม่นของ AI และดูพฤติกรรมย้อนหลัง")

logs = load_decision_log()
summary = summarize_decisions(logs)
profile = get_ai_adaptive_profile()

# ===== KPI =====
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", summary["total"])
c2.metric("Evaluated", summary["evaluated"])
c3.metric("Win Rate", f"{summary['win_rate']:.1f}%")
c4.metric("Pending", summary["pending"])

st.divider()

# ===== Adaptive Profile =====
st.subheader("🧠 AI Behavior Mode")
st.info(f"Mode: {profile['mode']}\n\n{profile['adjustment']}")

# ===== Table =====
st.subheader("📊 Decision Log")
if logs:
    df = pd.DataFrame(logs)
    st.dataframe(df, use_container_width=True)
else:
    st.warning("ยังไม่มีข้อมูล decision log")

# ===== Update Result =====
st.subheader("✏️ ประเมินผล AI")
if logs:
    idx = st.number_input("เลือก index", min_value=0, max_value=len(logs)-1, step=1)
    result = st.selectbox("ผลลัพธ์", ["GOOD", "BAD", "NEUTRAL"])
    note = st.text_input("หมายเหตุ", "")

    if st.button("บันทึกผล"):
        ok = update_decision_result(int(idx), result, note)
        if ok:
            st.success("อัปเดตเรียบร้อย")
            st.rerun()
        else:
            st.error("index ไม่ถูกต้อง")
