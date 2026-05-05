import os
import anthropic

from money_tracker import ensure_portfolio_file, summarize_money, format_money_summary

SYSTEM_PROMPT = """
คุณคือ Soul Money Advisor ผู้ช่วยการเงินส่วนตัวของคุณ Soul
หน้าที่คืออ่านข้อมูลพอร์ตส่วนตัว แล้วสรุปเป็นคำแนะนำแบบระวังความเสี่ยง

กติกา:
- ตอบภาษาไทย
- กระชับ เข้าใจง่าย
- ห้ามฟันธงกำไร
- ห้ามบอกให้ all-in
- เน้นถือยาวสำหรับกองทุน
- เน้นเตือนความเสี่ยงสำหรับหุ้น/ทอง
- ถ้าข้อมูลไม่พอ ให้บอกตรง ๆ
"""


def ask_money_ai(user_question: str = "ช่วยวิเคราะห์พอร์ตของเราหน่อย") -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    portfolio = ensure_portfolio_file()
    summary = summarize_money(portfolio)
    summary_text = format_money_summary(summary)

    if not api_key:
        return summary_text + "\n\n⚠️ ยังไม่ได้ตั้ง ANTHROPIC_API_KEY เลยแสดงแค่สรุปพื้นฐานก่อน"

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
คำถามจากคุณ Soul:
{user_question}

ข้อมูลพอร์ตส่วนตัว:
{summary_text}

ช่วยวิเคราะห์ว่า:
1. ตอนนี้พอร์ตเสี่ยงไหม
2. กองทุนควรทำอะไร
3. หุ้น/ทองใน Dime ควรถือ รอ หรือระวังอะไร
4. วันนี้ควรซื้อเพิ่มไหม
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f"เรียก AI ไม่สำเร็จ: {str(e)}\n\n{summary_text}"


if __name__ == "__main__":
    print(ask_money_ai())
