import os
import json
from pathlib import Path

import anthropic
import pandas as pd

ROOT = Path(__file__).resolve().parent
BACKTEST_FILE = ROOT / "backtest_summary.csv"
STRATEGY_FILE = ROOT / "strategy_modes.csv"
PORTFOLIO_FILE = ROOT / "paper_portfolio.json"

SYSTEM_PROMPT = """
คุณคือ SoulQuant AI Assistant เลขาผู้หญิงสุภาพ เรียบร้อย น่ารัก และเป็นผู้ช่วยส่วนตัวของคุณ Soul
หน้าที่หลักคือช่วยวิเคราะห์หุ้น พอร์ตจำลอง และกลยุทธ์จากข้อมูลในระบบ SoulQuant

สไตล์การตอบ:
- พูดภาษาไทยเป็นหลัก
- สุภาพ อบอุ่น เป็นกันเอง เหมือนเลขาส่วนตัว
- เรียกผู้ใช้ว่า "คุณ Soul"
- ตอบกระชับ เข้าใจง่าย ไม่ยาวเกินไป
- ใช้ emoji นิดหน่อย เช่น 💕 📊 ⚠️ ✅
- ไม่โอ้อวด ไม่ฟันธงเกินจริง

กติกาสำคัญ:
- ห้ามบอกว่าเป็นคำแนะนำการลงทุนแบบรับประกันกำไร
- ต้องเตือนความเสี่ยงเสมอเมื่อพูดเรื่องซื้อขาย
- ถ้าข้อมูลไม่พอ ให้บอกตรง ๆ
- ถ้า Strategy Mode เป็น HOLD ให้เน้นถือยาว ไม่ควรขายหมดเพราะสัญญาณสั้น ๆ
- ถ้า Strategy Mode เป็น HYBRID ให้แนะนำถือบางส่วน + ให้ AI ช่วยจับจังหวะบางส่วน
- ถ้า Strategy Mode เป็น WATCH ให้บอกให้เฝ้าดู รอสัญญาณชัด
- ถ้า Strategy Mode เป็น AVOID ให้เน้นหลีกเลี่ยงหรือลดความเสี่ยง
"""


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_ticker_context(ticker: str | None = None) -> str:
    strategy_df = load_csv(STRATEGY_FILE)
    backtest_df = load_csv(BACKTEST_FILE)
    portfolio = load_json(PORTFOLIO_FILE)

    lines = []

    if ticker:
        ticker = ticker.upper().strip()
        lines.append(f"ผู้ใช้ถามเกี่ยวกับ ticker: {ticker}")

        if strategy_df is not None and "ticker" in strategy_df.columns:
            row = strategy_df[strategy_df["ticker"].str.upper() == ticker]
            if not row.empty:
                r = row.iloc[0]
                lines.append("\nข้อมูล Strategy Selector:")
                lines.append(f"- Mode: {r.get('mode')}")
                lines.append(f"- Reason: {r.get('reason')}")
                lines.append(f"- Hybrid Return: {float(r.get('hybrid_return_pct', 0)):+.2f}%")
                lines.append(f"- Buy & Hold: {float(r.get('buy_hold_pct', 0)):+.2f}%")
                lines.append(f"- Hybrid Alpha: {float(r.get('hybrid_alpha_vs_hold_pct', 0)):+.2f}%")
                lines.append(f"- Hybrid Drawdown: {float(r.get('hybrid_max_drawdown_pct', 0)):.2f}%")

        if backtest_df is not None and "ticker" in backtest_df.columns:
            row = backtest_df[backtest_df["ticker"].str.upper() == ticker]
            if not row.empty:
                r = row.iloc[0]
                lines.append("\nข้อมูล Backtest:")
                lines.append(f"- AI Return: {float(r.get('ai_return_pct', 0)):+.2f}%")
                lines.append(f"- Hybrid Return: {float(r.get('hybrid_return_pct', 0)):+.2f}%")
                lines.append(f"- Buy & Hold: {float(r.get('buy_hold_pct', 0)):+.2f}%")
                lines.append(f"- Closed Trades: {int(r.get('closed_trades', 0))}")
                lines.append(f"- Win Rate: {float(r.get('win_rate_pct', 0)):.2f}%")
                lines.append(f"- Max Drawdown: {float(r.get('max_drawdown_pct', 0)):.2f}%")

        if portfolio is not None:
            pos = portfolio.get("positions", {}).get(ticker)
            if pos:
                lines.append("\nข้อมูล Paper Portfolio:")
                lines.append(f"- Shares: {float(pos.get('shares', 0)):.4f}")
                lines.append(f"- Avg Price: {float(pos.get('avg_price', 0)):.2f}")
                lines.append(f"- Last Price: {float(pos.get('last_price', 0)):.2f}")
    else:
        if strategy_df is not None:
            lines.append("ภาพรวม Strategy Modes:")
            for mode, group in strategy_df.groupby("mode"):
                tickers = ", ".join(group["ticker"].head(8).tolist())
                lines.append(f"- {mode}: {tickers}")

        if portfolio is not None:
            lines.append("\nภาพรวม Paper Portfolio:")
            lines.append(f"- Cash: {float(portfolio.get('cash', 0)):,.2f}")
            positions = portfolio.get("positions", {})
            lines.append(f"- Positions: {len(positions)}")
            for t, pos in positions.items():
                lines.append(f"  - {t}: {float(pos.get('shares', 0)):.4f} shares")

    if not lines:
        return "ยังไม่มีข้อมูล backtest/strategy/portfolio ในระบบ"

    return "\n".join(lines)


def extract_ticker_from_text(text: str, known_tickers: list[str] | None = None) -> str | None:
    text_upper = text.upper()
    if known_tickers:
        for ticker in known_tickers:
            if ticker.upper() in text_upper:
                return ticker.upper()

    # fallback แบบง่าย: หา token ตัวใหญ่ 2-5 ตัว
    for raw in text_upper.replace(",", " ").replace("?", " ").replace("/", " ").split():
        token = raw.strip()
        if token.isalpha() and 2 <= len(token) <= 5:
            return token
    return None


def get_known_tickers() -> list[str]:
    tickers = set()
    for path in [STRATEGY_FILE, BACKTEST_FILE]:
        df = load_csv(path)
        if df is not None and "ticker" in df.columns:
            tickers.update(df["ticker"].astype(str).str.upper().tolist())
    return sorted(tickers)


def ask_soul_assistant(user_message: str, chat_history: list[dict] | None = None) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "คุณ Soul คะ ตอนนี้ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY เลยค่ะ เลขาเลยยังตอบด้วย AI ไม่ได้นะคะ 💕"

    known_tickers = get_known_tickers()
    ticker = extract_ticker_from_text(user_message, known_tickers)
    context = get_ticker_context(ticker)

    client = anthropic.Anthropic(api_key=api_key)

    messages = []
    if chat_history:
        messages.extend(chat_history[-8:])

    messages.append({
        "role": "user",
        "content": f"""
คำถามจากคุณ Soul:
{user_message}

ข้อมูลจากระบบ SoulQuant:
{context}

ช่วยตอบเป็นเลขาส่วนตัวของคุณ Soul โดยใช้ข้อมูลนี้ประกอบค่ะ
"""
    })

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"ขออภัยค่ะคุณ Soul เลขาเรียก AI ไม่สำเร็จ: {str(e)}"


if __name__ == "__main__":
    print("SoulQuant AI Assistant พร้อมแล้วค่ะ 💕")
    while True:
        msg = input("คุณ Soul: ")
        if msg.lower() in ["exit", "quit", "q"]:
            break
        print("เลขา:", ask_soul_assistant(msg))
