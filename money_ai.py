import os
import anthropic

from money_tracker import ensure_portfolio_file, summarize_money, format_money_summary
from buy_advisor import build_buy_advice, format_buy_advice

SYSTEM_PROMPT = """
คุณคือ Soul Money Advisor ผู้ช่วยการเงินส่วนตัวของคุณ Soul
หน้าที่คืออ่านข้อมูลพอร์ตส่วนตัว + Buy Advisor แล้วสรุปเป็นคำแนะนำแบบระวังความเสี่ยง

กติกา:
- ตอบภาษาไทย
- กระชับ เข้าใจง่าย
- ห้ามฟันธงกำไร
- ห้ามบอกให้ all-in
- ห้ามแนะนำให้ซื้อเพิ่มถ้า Buy Readiness ต่ำกว่า 40
- ถ้า Buy Readiness 40-69 ให้เน้นรอ/แบ่งไม้เล็ก
- ถ้า Buy Readiness 70+ ให้บอกว่าซื้อได้เฉพาะไม้เล็กและต้องมีแผน
- เน้นถือยาวสำหรับกองทุน
- เน้นเตือนความเสี่ยงสำหรับหุ้น/ทอง
- ถ้าข้อมูลไม่พอ ให้บอกตรง ๆ
- ให้ตอบเป็นแผนปฏิบัติ 3 ข้อท้ายคำตอบเสมอ
"""


def ask_money_ai(user_question: str = "ช่วยวิเคราะห์พอร์ตของเราหน่อย") -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    portfolio = ensure_portfolio_file()
    summary = summarize_money(portfolio)
    summary_text = format_money_summary(summary)
    buy_advice = build_buy_advice(summary)
    buy_text = format_buy_advice(buy_advice)

    if not api_key:
        return (
            summary_text
            + "\n\n"
            + buy_text
            + "\n\n⚠️ ยังไม่ได้ตั้ง ANTHROPIC_API_KEY เลยแสดงแค่สรุปพื้นฐานก่อน"
        )

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
คำถามจากคุณ Soul:
{user_question}

ข้อมูลพอร์ตส่วนตัว:
{summary_text}

ข้อมูล Buy Advisor:
{buy_text}

ช่วยวิเคราะห์แบบผู้ช่วยการเงินส่วนตัวว่า:
1. พอร์ตตอนนี้เสี่ยงระดับไหน และเพราะอะไร
2. กองทุนควรถือ/เพิ่ม/รออย่างไร
3. หุ้น/ทองใน Dime ควรถือ รอ หรือระวังอะไร
4. วันนี้ควรซื้อเพิ่มไหม โดยอิง Buy Readiness Score
5. ถ้าจะซื้อ ให้ซื้อแบบไม้เล็กเท่าไรโดยประมาณเมื่อเทียบกับพอร์ต ไม่ใช่ all-in

รูปแบบคำตอบที่ต้องการ:
- สรุปสั้น 1 บรรทัด
- วิเคราะห์พอร์ต
- สิ่งที่ควรระวัง
- แผนวันนี้ 3 ข้อ
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f"เรียก AI ไม่สำเร็จ: {str(e)}\n\n{summary_text}\n\n{buy_text}"


if __name__ == "__main__":
    print(ask_money_ai())
