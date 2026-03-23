import yfinance as yf
import pandas as pd
import ta as ta_lib # เปลี่ยนชื่อให้ตรงกับ library ที่เราลง
import requests
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
from google import genai
import matplotlib.pyplot as plt

class Action(Enum):
    BUY = "🟢 ซื้อเพิ่ม (Oversold)"
    SELL = "🔴 ขายทำกำไร (Overbought)"
    HOLD = "🟡 ถือไว้ก่อน (Neutral)"

@dataclass
class AnalysisResult:
    ticker: str
    action: Action 
    current_price: float
    macd_hist: float
    rsi_14: float
    timestamp: str
    # --- Configuration ---
TICKER = os.getenv("TICKER_SYMBOL", "^GSPC")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK","https://discord.com/api/webhooks/1483398247937474671/qrHpD3-JtVzpxUFYDrpkzFkNN-qKoiEavvevcgiiUjMehTcGTgA4mlxlwiRS4DMuZ-Y5")
GEMINI_KEY = os.getenv("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY)

def ask_gemini(result: AnalysisResult):
   
    prompt = f"""
    คุณคือผู้เชี่ยวชาญด้านการลงทุนในตลาดหุ้น{result.ticker} จากข้อมูลชุดปัจจุบัน:
    - ราคาปัจจุบัน: {result.current_price}
    - RSI: {result.rsi_14}
    - MACD: {result.macd_hist}
    - การตัดสินใจ: {result.action.value}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}"

    

def notify_discord(result: AnalysisResult, ai_insight: str):
    """ฟังก์ชันส่งข้อมูลเข้า Discord"""

    color = 0x2ecc71 if result.action == Action.BUY else \
            0xe74c3c if result.action == Action.SELL else 0xf1c40f

    macd_icon =  "📈" if result.macd_hist > 0 else "📉"

    payload = {
        "embeds": [{
            "title": f"🤖 AI Analyst Report: {result.ticker}",
            "description": ai_insight,
            "color": color,
            "fields": [
                {"name": "💰Price", "value": f"**{result.current_price:,.2f}**", "inline": True},
                {"name": "📊RSI", "value": f"**{result.rsi_14}**", "inline": True},
                {"name": "📉MACD", "value": f"**{result.macd_hist}**", "inline": True},
                {"name": "🎯Decition", "value": f"**{result.action.value}**", "inline": True},
                {"name": "⏰Time", "value": f"**{result.timestamp}**", "inline": True}],
            "footer": {"text": f"Analysis at: {result.timestamp}"},
            "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/2422/2422796.png"}






        }]
    }
   # msg = {
    #    "content": f"📊 **{result.ticker} Report**\nPrice: {result.current_price:,.2f}\nRSI: {result.rsi_14}\nDecision: **{result.action.value}**\nMACD: {result.macd_hist} {macd_icon}\n"
    
    
    
    #}
    try:
        # ใช้ requests (มี s) ที่เป็นมาตรฐาน
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"ส่ง Discord ไม่สำเร็จ: {e}")

def analyze_market(ticker_symbol: str) -> AnalysisResult:
    """วิเคราะห์ตลาดหุ้น"""
    try:
        df = yf.download(ticker_symbol, period="6mo", progress=False)

        if df.empty or len(df) < 26:
            raise ValueError("ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [str(col).capitalize() for col in df.columns]
        df = df.copy()
        df.columns = df.columns.str.lower()
        # คำนวณ RSI
        df["RSI_14"] = ta_lib.momentum.RSIIndicator(df["close"], window=14).rsi()

        # คำนวณ MACD
        macd_obj = ta_lib.trend.MACD(df["close"], window_slow=26,window_fast=12,window_sign=9)
        df["MACD"] = macd_obj.macd()
        df["MACD_SIGN"] = macd_obj.macd_signal()
        df["MACD_HIST"] = macd_obj.macd_diff()
        

        rsi_col = [c for c in df.columns if 'RSI' in c.upper()]
        if not rsi_col:
            raise ValueError(f"คำนวณ RSI ไม่สำเร็จ:{df.columns.tolist()}")

        lasted_rsi = float(df[rsi_col[0]].iloc[-1])
        lasted_close = float(df['close'].iloc[-1])
        lasted_hist = float(df["MACD_HIST"].iloc[-1])
        prev_hist = float(df["MACD_HIST"].iloc[-2])
        rsi_buy = lasted_rsi< 35
        rsi_sell = lasted_rsi > 65
        macd_buy = lasted_hist > 0 and lasted_hist > prev_hist
        macd_sell = lasted_hist < 0 and lasted_hist < prev_hist

        # Logic การตัดสินใจ (แก้คำผิดตรงนี้)
        if rsi_buy and macd_buy:
            action = Action.BUY
        elif rsi_sell and macd_sell:
            action = Action.SELL
        else:
            action = Action.HOLD

        return AnalysisResult(
            ticker=ticker_symbol,
            current_price=round(lasted_close, 2),
            rsi_14=round(lasted_rsi, 2),
            macd_hist=round(lasted_hist, 4),
            action=action,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")
        raise
def create_chart(df, ticker):
        plt.figure(figsize=(10, 5))
        plt.plot(df.index. df['close'], label='Price',color='blue')
        plt.totle(f"{ticker} Price Action")
        plt.savefig( 'chart.png')
        plt.close()

if __name__ == "__main__":
    try:
        result = analyze_market(TICKER)
        
        print("🤖 กำลังให้ AI ช่วยวิเคราะห์...")
        ai_insight = ask_gemini(result)
        
        # อย่าลืมเรียกฟังก์ชันแจ้งเตือน!
        notify_discord(result, ai_insight)
        print("🤖 AI วิเคราะห์เสร็จสิ้น:")
        print(ai_insight)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")
        import sys
        sys.exit(1)