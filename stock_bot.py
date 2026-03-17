from curl_cffi import request
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
#import logging
import os

TICKER = os.getenv("TICKER_SYMBOL","^GSPC")


#logging.basicConfig(Level=logging.INFO, format= '$(asctime)s - %(levelname)s - %(message)s')
#logging = logging.getLogger(__name__)
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK","https://discord.com/api/webhooks/1483398247937474671/qrHpD3-JtVzpxUFYDrpkzFkNN-qKoiEavvevcgiiUjMehTcGTgA4mlxlwiRS4DMuZ-Y5")

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
    """ฟังชั่นส่งข้อมูลเข้า Discord """
    msg = {
        "content": f"📊 **{result.ticker} Report**\nPrice: {result.current_price}\nDecision: **{result.action.value}**"
    
    }
    request.post(WEBHOOK_URL, json=msg)   



def analyze_market(ticker_symbol: str) -> AnalysisResult:
    """วิเคราะห์ตลาดหุ้น"""
    try:
        # ดึงข้อมูลหุ้น
       df = yf.download(ticker_symbol, period="6mo", progress=False)

       if df.empty or len(df) < 14:
           raise ValueError("ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์")
# ใช้ .copy() เพื่อป้องกัน SettingWithCopyWarning
       df = df.copy()

       # คำนวณ RSI
       df.ta.rsi(length=14, append=True)

       lasted_rsi = df['RSI_14'].iloc[-1]
       lasted_close = df['Close'].iloc[-1]
       
       if pd.isna(lasted_rsi):
        raise ValueError("คำนวณ RSI ไม่สำเร็จ")
        
        if lasted_rsi < 30:
            action = Action.BUY
        elif lasted_rsi >70:
            action = Aciton.SELL
        else:
            action = Actionn.HOLD

        return AnalysisResult(
            ticker=ticker_symbol,
            current_price=round(folat(lastest_close),2),
            rsi_14=round(float(lasted_rsi),2),
            action=action,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")
        raise
if __name__ == "__main__":
    try:
        result = analyze_market(TICKER)
        print(f"\n---{result.ticker} Analysis ---")
        print(f"Price: {result.current_price} | RSI: {result.rsi_14}")
        print(f"Decision: {result.action.value}")
    except Exception:
        exit(1)