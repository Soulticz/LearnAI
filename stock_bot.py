import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta  # เปลี่ยนชื่อให้ตรงกับ library ที่เราลง
import requests
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os

# --- Configuration ---
TICKER = os.getenv("TICKER_SYMBOL", "^GSPC")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/...")

class Action(Enum):
    BUY = "🟢 ซื้อเพิ่ม (Oversold)"
    SELL = "🔴 ขายทำกำไร (Overbought)"
    HOLD = "🟡 ถือไว้ก่อน (Neutral)"
    
@dataclass
class AnalysisResult:
    ticker: str
    action: Action 
    current_price: float
    rsi_14: float
    timestamp: str

def notify_discord(result: AnalysisResult):
    """ฟังก์ชันส่งข้อมูลเข้า Discord"""
    msg = {
        "content": f"📊 **{result.ticker} Report**\nPrice: {result.current_price:,.2f}\nRSI: {result.rsi_14}\nDecision: **{result.action.value}**"
    }
    try:
        # ใช้ requests (มี s) ที่เป็นมาตรฐาน
        response = requests.post(WEBHOOK_URL, json=msg)
        response.raise_for_status()
    except Exception as e:
        print(f"ส่ง Discord ไม่สำเร็จ: {e}")

def analyze_market(ticker_symbol: str) -> AnalysisResult:
    """วิเคราะห์ตลาดหุ้น"""
    try:
        df = yf.download(ticker_symbol, period="6mo", progress=False)

        if df.empty or len(df) < 14:
            raise ValueError("ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์")

        df = df.copy()
        df.ta.rsi(length=14, append=True)

        # ดึงค่าแถวสุดท้ายและแปลงเป็น float ให้ชัวร์
        lasted_rsi = float(df['RSI_14'].iloc[-1])
        lasted_close = float(df['Close'].iloc[-1])
        
        if pd.isna(lasted_rsi):
            raise ValueError("คำนวณ RSI ไม่สำเร็จ")
        
        # Logic การตัดสินใจ (แก้คำผิดตรงนี้)
        if lasted_rsi < 30:
            action = Action.BUY
        elif lasted_rsi > 70:
            action = Action.SELL
        else:
            action = Action.HOLD

        return AnalysisResult(
            ticker=ticker_symbol,
            current_price=round(lasted_close, 2),
            rsi_14=round(lasted_rsi, 2),
            action=action,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        result = analyze_market(TICKER)
        print(f"\n--- {result.ticker} Analysis ---")
        print(f"Price: {result.current_price} | RSI: {result.rsi_14}")
        print(f"Decision: {result.action.value}")
        
        # อย่าลืมเรียกฟังก์ชันแจ้งเตือน!
        notify_discord(result)
        
    except Exception:
        import sys
        sys.exit(1)